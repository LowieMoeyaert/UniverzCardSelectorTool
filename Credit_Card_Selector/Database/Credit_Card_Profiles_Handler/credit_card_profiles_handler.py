"""
Credit Card Profiles Handler

This module serves as the main entry point for the credit card recommendation system.
It coordinates the different components of the system to provide credit card recommendations
based on user survey responses.
"""

import json
from typing import Any, Dict, List, Optional

from Credit_Card_Selector.Database.general_utils import (
    get_logger, generate_unique_id, create_collection_if_not_exists
)
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.credit_card_profiles_handler_config import (
    SURVEY_COLLECTION, CARDS_COLLECTION
)
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.database_operations import (
    store_recommendation_in_qdrant
)
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.survey_processing import (
    build_survey_vector, is_similar_survey_existing
)
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.card_filtering import (
    retrieve_filtered_cards
)
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.llm_interaction import (
    generate_top_5_with_llm
)

# Configure module logger
logger = get_logger(__file__)


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

        # Add a Survey_ID if it doesn't exist
        if "Survey_ID" not in response:
            response["Survey_ID"] = generate_unique_id()
            logger.info(f"Generated Survey_ID: {response['Survey_ID']}")

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
            success = store_recommendation_in_qdrant(best_cards, response, survey_vector)
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

    # Test 1: Standard case with valid survey response
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
