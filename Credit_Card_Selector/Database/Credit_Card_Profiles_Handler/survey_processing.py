import json
from typing import Any, Dict, List, Optional

from qdrant_client.models import ScoredPoint
from Credit_Card_Selector.Database.general_utils import (
    get_logger, encode_text, VECTOR_SIZE
)
from Credit_Card_Selector.Database.qdrant_config import qdrant_client
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.credit_card_profiles_handler_config import (
    SURVEY_COLLECTION, SIMILARITY_THRESHOLD
)

# Configure module logger
logger = get_logger(__file__)


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
        # checks if survey_vector is filled in en type is list

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