import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from json.decoder import JSONDecodeError

import requests
import tiktoken
from requests.exceptions import RequestException, Timeout, ConnectionError
from Credit_Card_Selector.Database.general_utils import get_logger
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.credit_card_profiles_handler_config import (
    OLLAMA_API_URL, OLLAMA_MODEL, MAX_TOKENS, LLM_API_TIMEOUT, RELEVANT_FIELDS
)

# Configure module logger
logger = get_logger(__file__)


def count_prompt_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    Count the number of tokens in a text string for a specific model.

    Args:
        text: The text to count tokens for
        model: The model to use for token counting

    Returns:
        Number of tokens in the text

    Raises:
        Exception: If token counting fails
    """
    if not text:
        return 0

    try:
        # Try to get the encoding for the specified model
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fall back to a base encoding if a model-specific one isn't available
        encoding = tiktoken.get_encoding("cl100k_base")
        logger.debug(f"Using fallback encoding 'cl100k_base' for model '{model}'")
    except Exception as e:
        logger.error(f"Error getting token encoding: {str(e)}")
        # Return a conservative estimate as fallback
        return len(text) // 3

    try:
        return len(encoding.encode(text))
    except Exception as e:
        logger.error(f"Error counting tokens: {str(e)}")
        # Return a conservative estimate as fallback
        return len(text) // 3


def build_llm_prompt_prefix(survey_response: Dict[str, Any]) -> Tuple[str, str]:
    """
    Build the prefix part of the LLM prompt with instructions and survey data.

    Args:
        survey_response: Dictionary containing survey responses

    Returns:
        Tuple containing (prompt_prefix, survey_json_string)

    Raises:
        ValueError: If survey_response is not a dictionary
    """
    if not isinstance(survey_response, dict):
        logger.warning(f"Invalid survey_response type: {type(survey_response)}, expected dict")
        # Create an empty dict as a fallback
        survey_response = {}

    try:
        # Convert survey to format JSON
        survey_json = json.dumps(survey_response, indent=2)

        # Build the prompt with clear instructions
        prompt_prefix = f"""
            You are an API that selects the best credit cards. 
            Your output **must only be a JSON list** with exactly 5 recommended credit cards with their values shown in "Expected Output", without any extra text or explanations. I want only JSON in the response, nothing else.

            IMPORTANT: The response MUST be a JSON ARRAY/LIST with square brackets [], not a single object with curly braces {{}}.
            IMPORTANT: You must return EXACTLY 5 credit cards, not more, not less.

            **Expected Output:**  
            [
                {{"Card_ID": "ValueOfCardID","Reason For Choice": "ReasonExplainedHere"}},
                {{"Card_ID": "ValueOfCardID","Reason For Choice": "ReasonExplainedHere"}},
                {{"Card_ID": "ValueOfCardID","Reason For Choice": "ReasonExplainedHere"}},
                {{"Card_ID": "ValueOfCardID","Reason For Choice": "ReasonExplainedHere"}},
                {{"Card_ID": "ValueOfCardID","Reason For Choice": "ReasonExplainedHere"}}
            ]

            **Survey Response:**
            {survey_json}

            **Available Credit Cards (only relevant fields):**
        """

        return prompt_prefix, survey_json
    except Exception as e:
        logger.error(f"Error building LLM prompt: {str(e)}")
        # Return a minimal working prompt as fallback
        empty_json = "{}"
        fallback_prompt = f"""
            Return a JSON list of 5 recommended credit cards.
            **Survey Response:**
            {empty_json}
            **Available Credit Cards:**
        """
        return fallback_prompt, empty_json


def truncate_cards_to_token_limit(
    cards: List[Any],
    base_prompt_prefix: str,
    survey_json: str
) -> List[Dict[str, Any]]:
    """
    Truncate the list of cards to fit within the token limit for the LLM.

    Args:
        cards: List of card objects to filter
        base_prompt_prefix: The prefix part of the prompt
        survey_json: JSON string of the survey response

    Returns:
        List of filtered card dictionaries that fit within the token limit
    """
    if not cards:
        logger.warning("No cards provided to truncate")
        return []

    filtered_cards = []

    try:
        # Calculate the initial token count from the base prompt and survey
        current_token_count = count_prompt_tokens(base_prompt_prefix + survey_json, model=OLLAMA_MODEL)
        logger.debug(f"Initial token count: {current_token_count}")

        # Reserve some tokens for the JSON structure overhead
        reserved_tokens = 100
        effective_max_tokens = MAX_TOKENS - reserved_tokens

        for i, card in enumerate(cards):
            # Skip cards without payload
            if not hasattr(card, "payload"):
                continue

            # Extract only relevant fields from the card
            try:
                temp_card = {
                    key: card.payload.get(key, "")
                    for key in RELEVANT_FIELDS
                    if key in card.payload and card.payload.get(key) is not None
                }

                # Add the card to our filtered list
                filtered_cards.append(temp_card)

                # Check if we've reached our card limit (safety check)
                if len(filtered_cards) >= 50:  # Arbitrary limit to prevent excessive processing
                    logger.info("Reached maximum card limit (50) for LLM prompt")
                    break

                # Recalculate the token count with the updated list
                test_prompt = base_prompt_prefix + json.dumps(filtered_cards, indent=2)
                test_token_count = count_prompt_tokens(test_prompt, model=OLLAMA_MODEL)

                # If the new token count exceeds the max, remove the last card and stop
                if test_token_count >= effective_max_tokens:
                    filtered_cards.pop()  # Remove the last added card
                    logger.info(f"Token limit reached after adding {len(filtered_cards)} cards. "
                               f"Token count: {test_token_count}/{effective_max_tokens}")
                    break

                # Log progress periodically
                if i % 10 == 0 and i > 0:
                    logger.debug(f"Added {len(filtered_cards)} cards so far. Current token count: {test_token_count}")

            except Exception as e:
                logger.warning(f"Error processing card {i}: {str(e)}")
                continue

        logger.info(f"Final card count for LLM: {len(filtered_cards)} cards")
        return filtered_cards

    except Exception as e:
        logger.error(f"Error truncating cards to token limit: {str(e)}")
        # Return a small subset as fallback
        if cards and len(cards) > 0 and hasattr(cards[0], "payload"):
            return [{key: cards[0].payload.get(key, "") for key in RELEVANT_FIELDS
                    if key in cards[0].payload and cards[0].payload.get(key) is not None}]
        return []


def call_llm_api(prompt: str, max_retries: int = 3, retry_delay: float = 2.0, timeout: int = LLM_API_TIMEOUT) -> Optional[requests.Response]:
    """
    Call the LLM API with the given prompt.

    Args:
        prompt: The prompt to send to the LLM
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        timeout: Timeout in seconds for the API call (default from LLM_API_TIMEOUT config)

    Returns:
        Response object from the API or None if the request failed
    """
    if not prompt:
        logger.error("Empty prompt provided to LLM API")
        return None

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }

    # Log token count and truncated prompt for debugging
    token_count = count_prompt_tokens(prompt)
    truncated_prompt = prompt[:200] + "..." if len(prompt) > 200 else prompt
    logger.debug(f"Sending prompt to LLM (tokens: {token_count}):\n{truncated_prompt}")

    # Implement retry logic
    for attempt in range(max_retries):
        try:
            # Set timeout to prevent hanging requests
            logger.debug(f"Making LLM API call with timeout of {timeout} seconds")
            response = requests.post(OLLAMA_API_URL, json=payload, timeout=timeout)

            # Log response status
            logger.debug(f"Received response from LLM: status={response.status_code}")

            # If successful, return the response
            if response.status_code == 200:
                return response

            # If server error, retry
            if response.status_code >= 500:
                logger.warning(f"Server error from LLM API (attempt {attempt+1}/{max_retries}): "
                              f"status={response.status_code}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue

            # For other errors, log and return the response anyway
            logger.error(f"Error response from LLM API: status={response.status_code}, "
                        f"response={response.text[:200]}...")
            return response

        except Timeout:
            logger.warning(f"Timeout calling LLM API after {timeout} seconds (attempt {attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                # Increase retry delay for timeout errors to give the server more time to recover
                adjusted_delay = retry_delay * (attempt + 1)
                logger.info(f"Waiting {adjusted_delay} seconds before retry...")
                time.sleep(adjusted_delay)
                continue
        except ConnectionError:
            logger.warning(f"Connection error calling LLM API (attempt {attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
        except RequestException as e:
            logger.error(f"Request error calling LLM API: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling LLM API: {str(e)}")
            return None

    logger.error(f"Failed to call LLM API after {max_retries} attempts")
    return None


def ensure_ollama_running(max_retries: int = 2, retry_delay: float = 3.0) -> bool:
    """
    Check if the Ollama model is running and start it if needed.

    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        True if Ollama is running, False otherwise
    """
    # Check if Ollama is already running
    for attempt in range(max_retries + 1):
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=10)

            if response.status_code == 200:
                models = response.json().get("models", [])

                if OLLAMA_MODEL in models:
                    logger.info(f"Ollama model '{OLLAMA_MODEL}' is already running")
                    return True
                else:
                    logger.info(f"Ollama is running but model '{OLLAMA_MODEL}' is not loaded")
                    break  # Continue to loading the model
            else:
                logger.warning(f"Unexpected response from Ollama server: {response.status_code}")

        except Timeout:
            logger.warning(f"Timeout checking Ollama status (attempt {attempt+1}/{max_retries+1})")
        except ConnectionError:
            logger.warning("Ollama server appears to be offline")
        except RequestException as e:
            logger.warning(f"Error checking Ollama status: {str(e)}")

        if attempt < max_retries:
            logger.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)

    # Try to start/pull the model
    try:
        logger.info(f"Pulling Ollama model '{OLLAMA_MODEL}'...")
        start_response = requests.post(
            "http://localhost:11434/api/pull",
            json={"name": OLLAMA_MODEL},
            timeout=60  # Longer timeout for model pulling
        )

        if start_response.status_code == 200:
            logger.info(f"Successfully pulled Ollama model '{OLLAMA_MODEL}'")
            return True
        else:
            logger.error(f"Failed to pull Ollama model: status={start_response.status_code}, "
                        f"response={start_response.text[:200]}...")
            return False

    except Exception as e:
        logger.error(f"Error pulling Ollama model: {str(e)}")
        return False


def check_response_ok(response: Optional[requests.Response]) -> bool:
    """
    Check if the response from the LLM API is valid.

    Args:
        response: Response object from the API

    Returns:
        True if the response is valid, False otherwise
    """
    if response is None:
        return False

    try:
        return response.status_code == 200 and len(response.text.strip()) > 0
    except Exception as e:
        logger.error(f"Error checking response: {str(e)}")
        return False


def safe_json_parse(response: requests.Response) -> Optional[Dict[str, Any]]:
    """
    Safely parse JSON from the response.

    Args:
        response: Response object from the API

    Returns:
        Parsed JSON as a dictionary or None if parsing failed
    """
    if response is None:
        return None

    try:
        return response.json()
    except JSONDecodeError:
        logger.error(f"Invalid JSON received from LLM: {response.text[:200]}...")
        return None
    except Exception as e:
        logger.error(f"Error parsing JSON from LLM response: {str(e)}")
        return None


def parse_recommendations_from_llm(response: Optional[requests.Response]) -> List[Dict[str, str]]:
    """
    Parse recommendations from the LLM response.

    Args:
        response: Response object from the LLM API

    Returns:
        List of recommended card dictionaries
    """
    # Check if the response is valid
    if not check_response_ok(response):
        status = getattr(response, 'status_code', 'No response') if response else 'No response'
        logger.error(f"Invalid or failed response from LLM API: {status}")
        return []

    # Parse JSON from response
    response_json = safe_json_parse(response)
    if not response_json:
        logger.error("Failed to parse JSON from LLM response")
        return []

    # Extract the text output from the response
    llm_output = response_json.get("response", "").strip()
    if not llm_output:
        logger.error("Empty response text from LLM")
        return []

    # Log a truncated version of the output for debugging
    truncated_output = llm_output[:200] + "..." if len(llm_output) > 200 else llm_output
    logger.debug(f"Processing LLM output: {truncated_output}")

    # Try to parse the JSON output
    try:
        # Try to parse the entire output as JSON
        parsed_json = json.loads(llm_output)

        # Validate that it's a list of dictionaries with Card_ID
        if isinstance(parsed_json, list) and all(isinstance(item, dict) and "Card_ID" in item for item in parsed_json):
            # Limit to 5 cards maximum
            if len(parsed_json) > 5:
                logger.warning(f"Limiting cards from {len(parsed_json)} to 5")
                parsed_json = parsed_json[:5]

            logger.info(f"Successfully extracted {len(parsed_json)} cards")
            return parsed_json
        else:
            logger.warning("JSON found but not in expected format")
            return []
    except JSONDecodeError:
        logger.error("Failed to parse JSON from LLM output")
        return []
    except Exception as e:
        logger.error(f"Error parsing recommendations: {str(e)}")
        return []


def generate_top_5_with_llm(
    cards: List[Any],
    survey_response: Dict[str, Any]
) -> List[Dict[str, str]]:
    """
    Generate the top 5 card recommendations using the LLM.

    Args:
        cards: List of card objects to choose from
        survey_response: Dictionary containing survey responses

    Returns:
        List of recommended card dictionaries
    """
    if not cards:
        logger.warning("No cards provided for LLM recommendation")
        return []

    if not isinstance(survey_response, dict):
        logger.warning(f"Invalid survey_response type: {type(survey_response)}, expected dict")
        return []

    try:
        # Ensure Ollama is running
        ensure_ollama_running()

        # Build the prompt
        base_prompt_prefix, survey_json = build_llm_prompt_prefix(survey_response)

        # Truncate cards to fit the token limit
        filtered_cards = truncate_cards_to_token_limit(cards, base_prompt_prefix, survey_json)
        if not filtered_cards:
            logger.warning("No cards left after token limit truncation")
            return []

        # Build the full prompt
        full_prompt = base_prompt_prefix + json.dumps(filtered_cards, indent=2)

        # Call the LLM API
        logger.info(f"Calling LLM API with {len(filtered_cards)} cards")
        response = call_llm_api(full_prompt)

        # Parse recommendations from the response
        recommendations = parse_recommendations_from_llm(response)

        logger.info(f"Generated {len(recommendations)} card recommendations")
        return recommendations

    except Exception as e:
        logger.error(f"Error generating recommendations with LLM: {str(e)}")
        return []
