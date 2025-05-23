from typing import Dict, Any, List, Tuple, Optional
from Credit_Card_Selector.Database.general_utils import get_logger
from Credit_Card_Selector.Database.Credit_Card_Handler.credit_card_handler import (
    find_existing_credit_card, CREDIT_CARDS_COLLECTION
)
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.database_operations import fetch_all_cards
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.card_filtering import apply_manual_filters
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.credit_card_profiles_handler_config import CARD_FETCH_LIMIT

# Configure module logger
logger = get_logger(__file__)

def get_all_credit_cards() -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Get all credit cards from the database.
    
    Returns:
        Tuple containing:
        - List of credit card dictionaries
        - Error message if an error occurred, None otherwise
    """
    try:
        cards = fetch_all_cards(CREDIT_CARDS_COLLECTION, CARD_FETCH_LIMIT)

        if not cards:
            logger.info("No credit cards found in the database.")
            return [], "No credit cards found."

        # Convert Qdrant points to dictionaries
        card_dicts = [card.payload for card in cards if hasattr(card, "payload")]

        logger.info(f"Retrieved {len(card_dicts)} credit cards.")
        return card_dicts, None

    except Exception as e:
        error_msg = f"Error retrieving credit cards: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return [], error_msg


def get_credit_card_by_id(card_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Get a specific credit card by ID.
    
    Args:
        card_id: ID of the credit card to retrieve
        
    Returns:
        Tuple containing:
        - Credit card dictionary if found, None otherwise
        - Error message if an error occurred, None otherwise
    """
    try:
        # Find the credit card by ID
        card = find_existing_credit_card(card_id, None)

        if not card:
            logger.warning(f"Credit card with ID '{card_id}' not found.")
            return None, f"Credit card with ID '{card_id}' not found."

        logger.info(f"Retrieved credit card with ID '{card_id}'.")
        return card.payload, None

    except Exception as e:
        error_msg = f"Error retrieving credit card with ID '{card_id}': {str(e)}"
        logger.error(f"❌ {error_msg}")
        return None, error_msg


def filter_credit_cards(filter_params: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Filter credit cards based on parameters.
    
    Args:
        filter_params: Dictionary of filter parameters
        
    Returns:
        Tuple containing:
        - List of filtered credit card dictionaries
        - Error message if an error occurred, None otherwise
    """
    try:
        if not filter_params:
            # Apply default filter example instead of returning an error
            filter_params = {
                "Credit_Score": 80,
                "Rewards": "Cashback",
                "Card_Type": "Gold"
            }
            logger.info("No filter parameters provided, applying default filter example")

        # Fetch all cards
        cards = fetch_all_cards(CREDIT_CARDS_COLLECTION, CARD_FETCH_LIMIT)

        if not cards:
            logger.info("No credit cards found in the database.")
            return [], "No credit cards found."

        # Apply filters
        filtered_cards = apply_manual_filters(cards, filter_params)

        if not filtered_cards:
            logger.info("No credit cards match the filter criteria.")
            return [], "No credit cards match the filter criteria."

        # Convert Qdrant points to dictionaries
        card_dicts = [card.payload for card in filtered_cards if hasattr(card, "payload")]

        logger.info(f"Retrieved {len(card_dicts)} credit cards after filtering.")
        return card_dicts, None

    except Exception as e:
        error_msg = f"Error filtering credit cards: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return [], error_msg