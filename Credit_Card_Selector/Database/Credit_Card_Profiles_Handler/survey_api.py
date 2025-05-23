from typing import Dict, Any, List, Tuple, Optional
from qdrant_client.models import PointStruct
from Credit_Card_Selector.Database.general_utils import get_logger
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.credit_card_profiles_handler import (
    handle_survey_response
)
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.database_operations import fetch_all_cards
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.card_filtering import apply_manual_filters
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.credit_card_profiles_handler_config import (
    SURVEY_COLLECTION, CARD_FETCH_LIMIT
)

# Configure module logger
logger = get_logger(__file__)

def process_survey(data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Process a survey response and return recommended credit cards.
    
    Args:
        data: Dictionary containing survey responses
        
    Returns:
        Tuple containing:
        - List of recommended credit card dictionaries
        - Error message if an error occurred, None otherwise
    """
    try:
        if not data:
            logger.warning("❗ No JSON data received.")
            return [], "No JSON data received."

        logger.info(f"📥 Received survey data: {data}")
        recommended_cards = handle_survey_response(data)

        if not recommended_cards:
            logger.info("📭 No suitable cards found.")
            return [], "No suitable cards found."

        logger.info(f"📤 Recommended cards: {[card.get('Card_ID', 'unknown') for card in recommended_cards]}")
        return recommended_cards, None

    except Exception as e:
        error_msg = f"Error processing survey: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return [], error_msg


def get_all_survey_responses(filter_params: Dict[str, Any] = None) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Get all survey responses from the database with optional filtering.
    
    Args:
        filter_params: Dictionary of filter parameters
        
    Returns:
        Tuple containing:
        - List of survey response dictionaries
        - Error message if an error occurred, None otherwise
    """
    try:
        responses = fetch_all_cards(SURVEY_COLLECTION, CARD_FETCH_LIMIT)

        if not responses:
            logger.info("No survey responses found in the database.")
            return [], "No survey responses found."

        # Convert Qdrant points to dictionaries
        response_dicts = []
        for resp in responses:
            if hasattr(resp, "payload"):
                survey_data = resp.payload.get("Survey_Response", {})
                recommended_cards = resp.payload.get("Recommended_Cards", [])
                timestamp = resp.payload.get("Timestamp", "")

                # Get survey_id from top level first, fall back to survey_data for backward compatibility
                survey_id = resp.payload.get("Survey_ID", survey_data.get("Survey_ID", "unknown"))

                # Check if we need to filter based on search term
                include_response = True
                if filter_params and "search_term" in filter_params and filter_params["search_term"]:
                    search_term = filter_params["search_term"].lower()
                    # Search in survey data
                    survey_match = False
                    for key, value in survey_data.items():
                        if isinstance(value, (str, int, float)) and str(value).lower().find(search_term) != -1:
                            survey_match = True
                            break

                    # Search in recommended cards
                    card_match = False
                    for card in recommended_cards:
                        for key, value in card.items():
                            if isinstance(value, (str, int, float)) and str(value).lower().find(search_term) != -1:
                                card_match = True
                                break
                        if card_match:
                            break

                    # Only include if either survey data or cards match
                    include_response = survey_match or card_match
                    if include_response:
                        logger.info(f"Survey {survey_id} matches search term '{search_term}'")
                    else:
                        continue

                # If filter parameters are provided, filter the recommended cards
                if filter_params and recommended_cards and "search_term" not in filter_params:
                    # Convert recommended_cards to a format compatible with apply_manual_filters
                    card_objects = []
                    for card in recommended_cards:
                        # Create a PointStruct with the card data as payload
                        card_obj = PointStruct(id=card.get("Card_ID", ""), payload=card)
                        card_objects.append(card_obj)

                    # Apply filters
                    filtered_cards = apply_manual_filters(card_objects, filter_params)

                    # Extract the filtered cards' payloads
                    filtered_card_dicts = [card.payload for card in filtered_cards if hasattr(card, "payload")]

                    # Only include responses that have matching cards after filtering
                    if not filtered_card_dicts:
                        continue

                    # Update recommended_cards with filtered cards
                    recommended_cards = filtered_card_dicts
                    logger.info(f"Filtered recommended cards for survey {survey_id}")

                response_dicts.append({
                    "survey_id": survey_id,
                    "survey_data": survey_data,
                    "recommended_cards": recommended_cards,
                    "timestamp": timestamp
                })

        logger.info(f"Retrieved {len(response_dicts)} survey responses after filtering.")
        return response_dicts, None

    except Exception as e:
        error_msg = f"Error retrieving survey responses: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return [], error_msg


def get_survey_response_by_id(survey_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Get a specific survey response by ID.
    
    Args:
        survey_id: ID of the survey response to retrieve
        
    Returns:
        Tuple containing:
        - Survey response dictionary if found, None otherwise
        - Error message if an error occurred, None otherwise
    """
    try:
        responses = fetch_all_cards(SURVEY_COLLECTION, CARD_FETCH_LIMIT)

        if not responses:
            logger.warning(f"Survey response with ID '{survey_id}' not found.")
            return None, f"Survey response with ID '{survey_id}' not found."

        # Normalize the survey_id for comparison (trim whitespace and convert to lowercase)
        normalized_survey_id = survey_id.strip().lower() if isinstance(survey_id, str) else survey_id

        # Find the survey response with the matching ID
        for resp in responses:
            if hasattr(resp, "payload"):
                # Get the survey_id from the top level and normalize it
                top_level_id = resp.payload.get("Survey_ID")
                normalized_top_level_id = top_level_id.strip().lower() if isinstance(top_level_id, str) else top_level_id

                # Get the survey_id from the Survey_Response object and normalize it
                survey_response_id = resp.payload.get("Survey_Response", {}).get("Survey_ID")
                normalized_survey_response_id = survey_response_id.strip().lower() if isinstance(survey_response_id, str) else survey_response_id

                # Check if survey_id is at the top level (new format)
                if normalized_top_level_id == normalized_survey_id:
                    survey_data = resp.payload.get("Survey_Response", {})
                    recommended_cards = resp.payload.get("Recommended_Cards", [])
                    timestamp = resp.payload.get("Timestamp", "")

                    response_dict = {
                        "survey_id": top_level_id,  # Use the original survey_id, not the normalized one
                        "survey_data": survey_data,
                        "recommended_cards": recommended_cards,
                        "timestamp": timestamp
                    }

                    logger.info(f"Retrieved survey response with ID '{survey_id}' from top level.")
                    return response_dict, None

                # Fallback to check in survey_data for backward compatibility
                elif normalized_survey_response_id == normalized_survey_id:
                    survey_data = resp.payload.get("Survey_Response", {})
                    recommended_cards = resp.payload.get("Recommended_Cards", [])
                    timestamp = resp.payload.get("Timestamp", "")

                    response_dict = {
                        "survey_id": survey_response_id,  # Use the original survey_id from Survey_Response, not the normalized one
                        "survey_data": survey_data,
                        "recommended_cards": recommended_cards,
                        "timestamp": timestamp
                    }

                    logger.info(f"Retrieved survey response with ID '{survey_id}' from Survey_Response (legacy format).")
                    return response_dict, None

        logger.warning(f"Survey response with ID '{survey_id}' not found.")
        return None, f"Survey response with ID '{survey_id}' not found."

    except Exception as e:
        error_msg = f"Error retrieving survey response with ID '{survey_id}': {str(e)}"
        logger.error(f"❌ {error_msg}")
        return None, error_msg