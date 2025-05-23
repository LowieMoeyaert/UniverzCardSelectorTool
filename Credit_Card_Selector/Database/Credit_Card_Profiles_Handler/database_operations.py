import json
import time
from typing import Any, Dict, List, Optional

from qdrant_client.models import PointStruct, ScoredPoint
from Credit_Card_Selector.Database.general_utils import (
    get_logger, generate_unique_id, create_collection_if_not_exists, VECTOR_SIZE
)
from Credit_Card_Selector.Database.qdrant_config import qdrant_client
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.credit_card_profiles_handler_config import (
    CARDS_COLLECTION, SURVEY_COLLECTION, CARD_FETCH_LIMIT
)

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


def store_recommendation_in_qdrant(
    recommended_cards: List[Dict[str, str]],
    survey_response: Dict[str, Any],
    survey_vector: List[float]
) -> bool:
    """
    Save the recommended cards to Qdrant along with the survey response and its vector.

    Args:
        recommended_cards: List of recommended card dictionaries
        survey_response: Dictionary containing survey responses
        survey_vector: Vector representation of the survey

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
        # Extract survey_id from survey_response
        survey_id = survey_response.get("Survey_ID", generate_unique_id())

        # Prepare the Survey_Response object for the payload
        if "Survey_Response" in survey_response and isinstance(survey_response["Survey_Response"], dict):
            # Case 1: survey_response has a nested Survey_Response field
            # Create a copy of the nested Survey_Response
            survey_response_obj = survey_response["Survey_Response"].copy()

            # Remove Survey_ID from the Survey_Response object if it exists
            if "Survey_ID" in survey_response_obj:
                survey_response_obj.pop("Survey_ID")
                logger.info("Removed duplicate Survey_ID from nested Survey_Response object")
        else:
            # Case 2: survey_response itself should be the Survey_Response in the payload
            # Create a copy of survey_response
            survey_response_obj = survey_response.copy()

            # Remove Survey_ID from the copy if it exists
            if "Survey_ID" in survey_response_obj:
                survey_response_obj.pop("Survey_ID")
                logger.info("Removed Survey_ID from Survey_Response object")

        # Create point structure for Qdrant
        points = [
            PointStruct(
                id=generate_unique_id(),
                vector=survey_vector,
                payload={
                    "Survey_ID": survey_id,  # Store survey_id at the top level
                    "Survey_Response": survey_response_obj,  # Store the prepared Survey_Response object
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
