import json
from typing import Any, Dict, List

from Credit_Card_Selector.Database.general_utils import get_logger
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.credit_card_profiles_handler_config import (
    FILTER_CONFIG, CARDS_COLLECTION, CARD_FETCH_LIMIT
)
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.database_operations import fetch_all_cards

# Configure module logger
logger = get_logger(__file__)


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
        # Check if we're doing a text search
        search_term = survey_response.get("search_term")
        if search_term:
            search_term = str(search_term).lower()
            logger.info(f"Performing text search for: {search_term}")

            for card in cards:
                # Skip cards without payload
                if not hasattr(card, "payload"):
                    continue

                # Search in all card fields
                found = False
                for key, value in card.payload.items():
                    if isinstance(value, (str, int, float)) and str(value).lower().find(search_term) != -1:
                        found = True
                        break

                if found:
                    filtered_cards.append(card)

            logger.info(f"Text search found {len(filtered_cards)} matching cards")
            return filtered_cards

        # Standard filtering
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
