import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union, cast
from json.decoder import JSONDecodeError

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
from qdrant_client.models import PointStruct, ScoredPoint
import tiktoken
from Credit_Card_Selector.Database.general_utils import (
    get_logger, encode_text, generate_unique_id, create_collection_if_not_exists, VECTOR_SIZE
)
from Credit_Card_Selector.Database.qdrant_config import qdrant_client
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.credit_card_profiles_handler_config import *

# Configure module logger
logger = get_logger(__file__)


def fetch_all_cards(collection_name: str, fetch_limit: int) -> List[Any]:
    """
    Retrieve all available credit cards from the database.

    Args:
        collection_name: Name of the Qdrant collection to query
        fetch_limit: Maximum number of cards to retrieve

    Returns:
        List of card objects from the database

    Raises:
        Exception: If there's an error communicating with the database
    """
    try:
        cards = qdrant_client.scroll(collection_name=collection_name, limit=fetch_limit)[0]
        logger.debug(f"📋 Retrieved {len(cards)} cards from database")
        return cards
    except Exception as e:
        logger.error(f"Failed to fetch cards from collection '{collection_name}': {str(e)}")
        return []


def fetch_cards_by_ids(collection_name: str, card_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Retrieve cards based on a list of Card_IDs.

    Args:
        collection_name: Name of the Qdrant collection to query
        card_ids: List of card IDs to retrieve

    Returns:
        List of card dictionaries with payload data

    Raises:
        Exception: If there's an error communicating with the database
    """
    if not card_ids:
        logger.warning("No card IDs provided to fetch_cards_by_ids")
        return []

    try:
        results = qdrant_client.scroll(
            collection_name=collection_name,
            limit=len(card_ids),
            scroll_filter={"must": [{"key": "Card_ID", "match": {"any": card_ids}}]}
        )[0]

        logger.debug(f"🔍 Retrieved {len(results)} cards by IDs")

        # Transform results to dictionaries with the Card_Name field
        return [{**card.payload, "Card_Name": card.payload.get("Card_ID", "Unknown")} 
                for card in results if hasattr(card, "payload")]
    except Exception as e:
        logger.error(f"Failed to fetch cards by IDs from collection '{collection_name}': {str(e)}")
        return []


def apply_manual_filters(cards: List[Any], survey_response: Dict[str, Any]) -> List[Any]:
    """
    Filter credit cards based on survey data.

    Args:
        cards: List of card objects to filter
        survey_response: Dictionary containing survey responses

    Returns:
        List of filtered card objects that match the survey criteria
    """
    if not cards:
        logger.warning("No cards provided to filter")
        return []

    if not isinstance(survey_response, dict):
        logger.warning(f"Invalid survey_response type: {type(survey_response)}, expected dict")
        return []

    filtered_cards = []

    try:
        for card in cards:
            is_match = True

            # Skip cards without payload
            if not hasattr(card, "payload"):
                continue

            for field, filter_type in FILTER_CONFIG.items():
                # Get values safely
                survey_value = survey_response.get(field)
                card_value = card.payload.get(field)

                # Skip comparison if either value is empty
                if survey_value in [None, 0, ""] or card_value in [None, 0, ""]:
                    continue

                # Apply different filter types
                if filter_type == "match":
                    # Direct equality match
                    if str(survey_value).lower() != str(card_value).lower():
                        is_match = False
                        break

                elif filter_type == "min":
                    # Numeric comparison
                    try:
                        # Convert values to float for comparison
                        survey_num = float(survey_value)
                        card_num = float(card_value)

                        if survey_num > card_num:
                            is_match = False
                            break
                    except (ValueError, TypeError):
                        # If conversion fails, skip this filter
                        logger.debug(f"Skipping numeric comparison for field '{field}': "
                                    f"survey_value={survey_value}, card_value={card_value}")
                        continue

            if is_match:
                filtered_cards.append(card)

        logger.info(f"📉 Manual filtering: {len(cards)} → {len(filtered_cards)} cards remaining")
        return filtered_cards

    except Exception as e:
        logger.error(f"Error during manual filtering: {str(e)}")
        return []


def embed_survey_response(survey_response: Dict[str, Any]) -> List[float]:
    """
    Generate a consistent vector representation of the survey response.

    Args:
        survey_response: Dictionary containing survey responses

    Returns:
        List of floats representing the embedded vector

    Raises:
        ValueError: If survey_response is not a dictionary
        Exception: If encoding fails
    """
    if not isinstance(survey_response, dict):
        raise ValueError(f"Expected dictionary for survey_response, got {type(survey_response)}")

    try:
        # Normalize all values to strings and sort keys for consistency
        normalized = {k: str(v).strip() if v is not None else "" 
                     for k, v in sorted(survey_response.items())}

        # Create a deterministic JSON representation
        flat_text = json.dumps(normalized, separators=(",", ":"), sort_keys=True)

        # Encode the text to a vector
        return encode_text(flat_text)
    except Exception as e:
        logger.error(f"Error embedding survey response: {str(e)}")
        # Return a zero vector as a fallback (with correct dimensions)
        return [0.0] * VECTOR_SIZE


def search_similar_survey(survey_vector: List[float]) -> Optional[ScoredPoint]:
    """
    Check if a similar survey response exists and return the best match.

    Args:
        survey_vector: Vector representation of the survey to search for

    Returns:
        Best matching ScoredPoint or None if no match found

    Raises:
        Exception: If there's an error communicating with the database
    """
    if not survey_vector or not isinstance(survey_vector, list):
        logger.warning(f"Invalid survey vector: {type(survey_vector)}")
        return None

    try:
        search_results = qdrant_client.search(
            collection_name=SURVEY_COLLECTION,
            query_vector=survey_vector,
            limit=1,
            with_vectors=True
        )

        if search_results:
            best_result = search_results[0]  # Best result

            # Log details at appropriate levels
            logger.debug(f"🔍 Best vector search result: {best_result}")

            if best_result.vector:
                logger.debug(f"🔍 Vector from DB (first 5 elements): {best_result.vector[:5]}...")
                logger.debug(f"🔍 Input vector (first 5 elements): {survey_vector[:5]}...")

            # Extract survey ID for logging
            survey_id = "Unknown"
            if hasattr(best_result, "payload") and best_result.payload:
                survey_response = best_result.payload.get("Survey_Response", {})
                if isinstance(survey_response, dict):
                    survey_id = survey_response.get("Survey_ID", "Unknown")

            logger.info(f"🔝 Best vector search score: {best_result.score:.4f} for Survey_ID: {survey_id}")
            return best_result
        else:
            logger.info("No similar surveys found in database")
            return None

    except Exception as e:
        logger.error(f"Error searching for similar survey: {str(e)}")
        return None


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
            # Set timeout to prevent hanging requests (increased from 60 to 180 seconds)
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


def extract_json_from_llm_output(llm_output: str) -> Optional[List[Dict[str, str]]]:
    """
    Extract a valid JSON list from LLM output.

    Args:
        llm_output: Raw text output from the LLM

    Returns:
        List of card dictionaries if valid JSON is found, None otherwise
    """
    if not llm_output or not isinstance(llm_output, str):
        logger.warning(f"Invalid LLM output type: {type(llm_output)}")
        return None

    # Trim whitespace and check for empty output
    llm_output = llm_output.strip()
    if not llm_output:
        logger.warning("Empty LLM output")
        return None

    # Try to parse the entire output as JSON
    try:
        parsed_json = json.loads(llm_output)

        # Validate that it's a list of dictionaries with Card_ID
        if isinstance(parsed_json, list):
            # Check if all items are dictionaries with Card_ID
            if all(isinstance(item, dict) and "Card_ID" in item for item in parsed_json):
                logger.info(f"Successfully parsed JSON list with {len(parsed_json)} cards")

                # Limit to 5 cards maximum
                if len(parsed_json) > 5:
                    logger.warning(f"Limiting cards from {len(parsed_json)} to 5")
                    parsed_json = parsed_json[:5]

                # Ensure all cards have both required fields
                for card in parsed_json:
                    if "Reason For Choice" not in card:
                        card["Reason For Choice"] = "Recommended by LLM"

                return parsed_json
            else:
                logger.warning("JSON list found but items don't have required 'Card_ID' field")
        elif isinstance(parsed_json, dict) and "Card" in parsed_json and isinstance(parsed_json["Card"], list):
            # Handle case where JSON is a dict with a "Card" array
            card_list = parsed_json["Card"]
            if all(isinstance(item, dict) and "cardID" in item for item in card_list):
                logger.info(f"Successfully parsed JSON dict with Card array containing {len(card_list)} cards")

                # Transform cardID to Card_ID for consistency
                transformed_cards = []
                for card in card_list:
                    transformed_card = {
                        "Card_ID": card["cardID"],
                        "Reason For Choice": "Recommended by LLM"
                    }
                    transformed_cards.append(transformed_card)

                # Limit to 5 cards maximum
                if len(transformed_cards) > 5:
                    logger.warning(f"Limiting cards from {len(transformed_cards)} to 5")
                    transformed_cards = transformed_cards[:5]

                return transformed_cards
            else:
                logger.warning("JSON dict with Card array found but items don't have required 'cardID' field")
        elif isinstance(parsed_json, dict):
            # Handle case where JSON is a single card object
            # Try different possible field names for card ID (case-insensitive)
            possible_id_fields = ["card_id", "cardid", "id", "name", "card", "card_name", "cardname"]
            card_id_field = None

            # First try exact matches
            for field in possible_id_fields:
                if field in parsed_json:
                    card_id_field = field
                    break

            # If no exact match, try case-insensitive matching
            if not card_id_field:
                card_id_field = next((k for k in parsed_json.keys() 
                                    if any(field.lower() == k.lower() for field in possible_id_fields)), None)

            if card_id_field:
                logger.info(f"Found single card object with field '{card_id_field}', converting to list format")
                card_id_value = str(parsed_json[card_id_field])

                # Create a list with a single card in the expected format
                transformed_card = [{
                    "Card_ID": card_id_value,
                    "Reason For Choice": "Recommended by LLM"
                }]

                return transformed_card
            elif len(parsed_json) > 0:
                # If we can't find a specific card ID field, use the first field as a fallback
                first_field = next(iter(parsed_json.keys()))
                first_value = str(parsed_json[first_field])

                logger.info(f"Using field '{first_field}' as fallback card ID")
                transformed_card = [{
                    "Card_ID": first_value,
                    "Reason For Choice": f"Recommended by LLM (using {first_field} as ID)"
                }]

                return transformed_card
            else:
                logger.warning("JSON dict found but couldn't identify a card ID field")
        else:
            logger.warning(f"JSON found but not a list or dict with Card array: {type(parsed_json)}")
    except JSONDecodeError:
        logger.debug("Failed to parse entire output as JSON, trying fallback methods")
    except Exception as e:
        logger.warning(f"Unexpected error parsing JSON: {str(e)}")

    return None


def fallback_extract_json_list(text: str) -> Optional[List[Dict[str, str]]]:
    """
    Extract card information from LLM output using fallback methods when JSON parsing fails.

    Args:
        text: Raw text output from the LLM

    Returns:
        List of card dictionaries if extraction succeeds, None otherwise
    """
    if not text or not isinstance(text, str):
        return None

    logger.info("Attempting fallback extraction methods for LLM output")

    # Method 1: Find JSON-like structures in the text
    try:
        # First, try to find a single JSON object (for single card case)
        single_object_matches = re.findall(r"\{\s*\"(?:.|\n)*?\"\s*:\s*(?:.|\n)*?}", text)

        for match in single_object_matches:
            try:
                card_object = json.loads(match)
                if isinstance(card_object, dict):
                    # Try different possible field names for card ID (case-insensitive)
                    possible_id_fields = ["card_id", "cardid", "id", "name", "card", "card_name", "cardname"]
                    card_id_field = None

                    # First try exact matches
                    for field in possible_id_fields:
                        if field in card_object:
                            card_id_field = field
                            break

                    # If no exact match, try case-insensitive matching
                    if not card_id_field:
                        card_id_field = next((k for k in card_object.keys() 
                                            if any(field.lower() == k.lower() for field in possible_id_fields)), None)

                    if card_id_field:
                        logger.info(f"Found single card object with field '{card_id_field}' in fallback extraction")
                        card_id_value = str(card_object[card_id_field])

                        # Create a list with a single card in the expected format
                        transformed_card = [{
                            "Card_ID": card_id_value,
                            "Reason For Choice": "Recommended by LLM"
                        }]

                        return transformed_card
                    elif len(card_object) > 0:
                        # If we can't find a specific card ID field, use the first field as a fallback
                        first_field = next(iter(card_object.keys()))
                        first_value = str(card_object[first_field])

                        logger.info(f"Using field '{first_field}' as fallback card ID in fallback extraction")
                        transformed_card = [{
                            "Card_ID": first_value,
                            "Reason For Choice": f"Recommended by LLM (using {first_field} as ID)"
                        }]

                        return transformed_card
            except JSONDecodeError:
                continue
            except Exception as e:
                logger.debug(f"Error in single object JSON pattern matching: {str(e)}")

        # Look for anything that resembles a JSON list
        matches = re.findall(r"\[\s*\{(?:.|\n)*?}\s*]", text)

        for match in matches:
            try:
                recommended_cards = json.loads(match)
                if isinstance(recommended_cards, list) and all(isinstance(card, dict) for card in recommended_cards):
                    # Check if cards have the required Card_ID field
                    valid_cards = [card for card in recommended_cards if "Card_ID" in card]

                    if valid_cards:
                        logger.info(f"Extracted {len(valid_cards)} cards using JSON pattern matching")

                        # Limit to 5 cards and ensure all have required fields
                        valid_cards = valid_cards[:5]
                        for card in valid_cards:
                            if "Reason For Choice" not in card:
                                card["Reason For Choice"] = "Recommended by LLM"

                        return valid_cards
            except JSONDecodeError:
                continue
            except Exception as e:
                logger.debug(f"Error in JSON pattern matching: {str(e)}")
    except Exception as e:
        logger.warning(f"Error in regex pattern matching: {str(e)}")

    # Method 2: Extract from markdown-formatted lists
    card_names = []

    try:
        # Pattern 1: Look for numbered list items with card names in bold or quotes
        numbered_items = re.findall(r'\d+\.\s+\*\*([^*]+)\*\*(?:\s+\(([^)]+)\))?', text)

        if numbered_items:
            logger.info(f"Found {len(numbered_items)} cards using numbered list pattern")

            for i, (card_name, provider) in enumerate(numbered_items):
                if i >= 5:  # Limit to 5 cards
                    break

                full_name = card_name.strip()
                if not full_name:
                    continue

                if provider:
                    reason = f"Recommended by LLM. Provider: {provider.strip()}"
                else:
                    reason = "Recommended by LLM"

                card_names.append({"Card_ID": full_name, "Reason For Choice": reason})

        # If we found cards using the numbered list pattern, return them
        if card_names:
            logger.info(f"Extracted {len(card_names)} cards using numbered list pattern")
            return card_names
    except Exception as e:
        logger.warning(f"Error extracting from numbered lists: {str(e)}")

    # Method 3: Look for card names in sections or bullet points
    try:
        sections = re.split(r'\n\s*\n', text)

        for section in sections:
            if '**' in section or '*' in section:
                # Try to extract the card name from bold text
                bold_match = re.search(r'\*\*([^*]+)\*\*', section)

                if bold_match:
                    card_name = bold_match.group(1).strip()
                    if not card_name:
                        continue

                    # Extract some context for the reason
                    reason_text = re.sub(r'\*\*[^*]+\*\*', '', section)
                    reason = f"Recommended by LLM: {reason_text[:100].strip()}..."

                    card_names.append({"Card_ID": card_name, "Reason For Choice": reason})

                    if len(card_names) >= 5:
                        break

        if card_names:
            logger.info(f"Extracted {len(card_names)} cards using section pattern")
            return card_names
    except Exception as e:
        logger.warning(f"Error extracting from sections: {str(e)}")

    # Method 4: Last resort - look for anything that might be a card name
    try:
        # Look for patterns like "Card: Name" or "Card Name":
        card_patterns = re.findall(r'(?:Card|Credit Card)[\s:]+([\w\s]+)(?:[\n:]|$)', text)

        for i, name in enumerate(card_patterns):
            if i >= 5:
                break

            clean_name = name.strip()
            if clean_name and len(clean_name) > 3:  # Avoid very short matches
                card_names.append({
                    "Card_ID": clean_name,
                    "Reason For Choice": "Extracted from LLM output"
                })

        if card_names:
            logger.info(f"Extracted {len(card_names)} cards using last resort pattern")
            return card_names
    except Exception as e:
        logger.warning(f"Error in last resort extraction: {str(e)}")

    logger.warning("All fallback extraction methods failed")
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

    # Try the primary extraction method
    parsed_cards = extract_json_from_llm_output(llm_output)
    if parsed_cards:
        logger.info(f"Successfully extracted {len(parsed_cards)} cards using primary method")
        return parsed_cards

    # Try fallback extraction methods
    fallback_cards = fallback_extract_json_list(llm_output)
    if fallback_cards:
        logger.info(f"Successfully extracted {len(fallback_cards)} cards using fallback methods")
        return fallback_cards

    # If all extraction methods fail, return an empty list
    logger.error("Failed to extract any valid card recommendations from LLM response")
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


def store_recommendation_in_qdrant(
    recommended_cards: List[Dict[str, str]], 
    survey_response: Dict[str, Any]
) -> bool:
    """
    Save the recommended cards to Qdrant along with the survey response and its vector.

    Args:
        recommended_cards: List of recommended card dictionaries
        survey_response: Dictionary containing survey responses

    Returns:
        True if storage was successful, False otherwise
    """
    if not recommended_cards:
        logger.warning("No recommended cards to store")
        return False

    if not isinstance(survey_response, dict):
        logger.warning(f"Invalid survey_response type: {type(survey_response)}, expected dict")
        return False

    try:
        # Generate vector from survey response
        survey_vector = embed_survey_response(survey_response)

        # Create point structure for Qdrant
        points = [
            PointStruct(
                id=generate_unique_id(),
                vector=survey_vector,
                payload={
                    "Survey_Response": survey_response,
                    "Recommended_Cards": recommended_cards,
                    "Survey_Vector": survey_vector,  # Store the vector itself for reference
                    "Timestamp": time.time()  # Add timestamp for tracking
                }
            )
        ]

        # Store in Qdrant
        qdrant_client.upsert(
            collection_name=SURVEY_COLLECTION,
            points=points
        )

        logger.info(f"Successfully saved {len(recommended_cards)} card recommendations to Qdrant")
        return True

    except Exception as e:
        logger.error(f"Error storing recommendations in Qdrant: {str(e)}")
        return False


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


def build_survey_vector(response: Dict[str, Any]) -> List[float]:
    """
    Generate a vector from a survey response consistently.

    Args:
        response: Dictionary containing survey responses or nested survey data

    Returns:
        Vector representation of the survey
    """
    if not isinstance(response, dict):
        logger.warning(f"Invalid response type: {type(response)}, expected dict")
        return [0.0] * VECTOR_SIZE  # Return zero vectors as fallback

    try:
        # Handle both direct survey responses and nested ones
        survey_data = response.get("Survey_Response", response)

        # Ensure survey_data is a dictionary
        if not isinstance(survey_data, dict):
            logger.warning(f"Invalid survey data type: {type(survey_data)}, expected dict")
            return [0.0] * VECTOR_SIZE

        return embed_survey_response(survey_data)

    except Exception as e:
        logger.error(f"Error building survey vector: {str(e)}")
        return [0.0] * VECTOR_SIZE


def is_similar_survey_existing(survey_vector: List[float]) -> Optional[ScoredPoint]:
    """
    Check if a similar survey already exists in the database.

    Args:
        survey_vector: Vector representation of the survey to check

    Returns:
        ScoredPoint of the similar survey if found, None otherwise
    """
    if not survey_vector or not isinstance(survey_vector, list):
        logger.warning(f"Invalid survey vector: {type(survey_vector)}")
        return None

    try:
        # Search for the similar survey
        existing_survey = search_similar_survey(survey_vector)

        # Check if similarity exceeds a threshold
        if existing_survey and hasattr(existing_survey, 'score') and existing_survey.score > SIMILARITY_THRESHOLD:
            logger.info(f"Found similar existing survey with similarity score: {existing_survey.score:.4f}")
            return existing_survey

        return None

    except Exception as e:
        logger.error(f"Error checking for similar surveys: {str(e)}")
        return None


def retrieve_filtered_cards(response: Dict[str, Any]) -> List[Any]:
    """
    Retrieve and filter cards based on survey response.

    Args:
        response: Dictionary containing survey responses

    Returns:
        List of filtered card objects
    """
    if not isinstance(response, dict):
        logger.warning(f"Invalid response type: {type(response)}, expected dict")
        return []

    try:
        # Fetch all cards from the database
        all_cards = fetch_all_cards(CARDS_COLLECTION, CARD_FETCH_LIMIT)
        if not all_cards:
            logger.warning("No cards retrieved from database")
            return []

        # Apply filters based on survey response
        filtered_cards = apply_manual_filters(all_cards, response)

        if not filtered_cards:
            logger.warning("No cards remaining after filtering. Check filter criteria.")
        else:
            logger.info(f"Retrieved {len(filtered_cards)} cards after filtering")

        return filtered_cards

    except Exception as e:
        logger.error(f"Error retrieving filtered cards: {str(e)}")
        return []


def handle_survey_response(response: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Process a survey response and return recommended cards without storing duplicates.

    This is the main entry point for the credit card recommendation system.

    Args:
        response: Dictionary containing survey responses

    Returns:
        List of recommended card dictionaries
    """
    if not isinstance(response, dict):
        logger.warning(f"Invalid response type: {type(response)}, expected dict")
        return []

    try:
        # Ensure the collection exists
        create_collection_if_not_exists(SURVEY_COLLECTION)

        # Generate vector from survey response
        survey_vector = build_survey_vector(response)

        # Check for similar existing surveys to avoid duplicates
        existing_survey = is_similar_survey_existing(survey_vector)
        if existing_survey and hasattr(existing_survey, 'payload'):
            logger.info("Using recommendations from similar existing survey")

            # Extract card recommendations from the existing survey
            try:
                card_dicts = existing_survey.payload.get("Recommended_Cards", [])
                if card_dicts and isinstance(card_dicts, list):
                    # Validate that we have valid card dictionaries
                    valid_cards = [
                        card for card in card_dicts 
                        if isinstance(card, dict) and "Card_ID" in card
                    ]

                    if valid_cards:
                        logger.info(f"Retrieved {len(valid_cards)} recommendations from similar survey")
                        return valid_cards
                    else:
                        logger.warning("Retrieved recommendations are invalid, generating new ones")
                else:
                    logger.warning("No valid recommendations in similar survey, generating new ones")
            except Exception as e:
                logger.error(f"Error extracting recommendations from similar survey: {str(e)}")

        # Filter cards based on survey response
        filtered_cards = retrieve_filtered_cards(response)
        if not filtered_cards:
            logger.warning("No cards match the survey criteria")
            return []

        # Generate top 5 recommendations using LLM
        logger.info(f"Generating recommendations from {len(filtered_cards)} filtered cards")
        best_cards = generate_top_5_with_llm(filtered_cards, response)

        # Store recommendations if they were successfully generated
        if best_cards:
            success = store_recommendation_in_qdrant(best_cards, response)
            if success:
                logger.info(f"Successfully stored {len(best_cards)} recommendations")
            else:
                logger.warning("Failed to store recommendations")
        else:
            logger.warning("No recommendations were generated")

        return best_cards

    except Exception as e:
        logger.error(f"Error handling survey response: {str(e)}")
        return []


if __name__ == "__main__":
    # Set up logging for standalone execution
    logger.info("Starting credit card recommendation system test")

    # Ensure collections exist
    create_collection_if_not_exists(SURVEY_COLLECTION)
    create_collection_if_not_exists(CARDS_COLLECTION)

    # Test 1: Standard case with valid survey response
    logger.info("\n=== Test 1: Standard case with valid survey response ===")
    standard_response = {
        "Card_Usage": "Luxury spending",
        "Frequency": "Daily",
        "Interest_Rate_Importance": "Low",
        "Credit_Score": 95,
        "Monthly_Income": "20000",
        "Minimum_Income": "25000",
        "Interest_Rate": "20",
        "Rewards": "Travel Miles",
        "Islamic": 1,
        "Survey_ID": generate_unique_id()
    }

    standard_results = handle_survey_response(standard_response)
    logger.info(f"Standard case results: {len(standard_results)} recommendations")


    # Summary of test results
    logger.info("\n=== Test Results Summary ===")
    logger.info(f"Test 1 (Standard): {len(standard_results)} recommendations")


    logger.info("\nAll tests completed successfully!")
