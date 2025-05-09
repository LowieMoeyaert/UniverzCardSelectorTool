from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.credit_card_profiles_handler import \
    handle_survey_response
from Credit_Card_Selector.Database.general_utils import (
    get_logger, create_collection_if_not_exists
)

from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.credit_card_profiles_handler_config import *

logger = get_logger(__file__)
if __name__ == "__main__":
    logger.info("🧪 Start test van credit_card_profiles_handler module")

    # Zorg dat de collecties bestaan
    create_collection_if_not_exists(SURVEY_COLLECTION)
    create_collection_if_not_exists(CARDS_COLLECTION)

    # Test 1: Standaard scenario met geldige survey response
    logger.info("\n\n🧪 TEST 1: Standaard scenario met geldige survey response")
    example_response = {
        "Card_Usage": "Luxe uitgaven",
        "Frequency": "Dagelijks",
        "Interest_Rate_Importance": "Laag",
        "Credit_Score": 95,
        "Monthly_Income": "20000",
        "Minimum_Income": "25000",
        "Interest_Rate": "20",
        "Rewards": "Travel Miles",
        "Islamic": 1
    }

    logger.info("📝 Verwerk standaard survey response...")
    results = handle_survey_response(example_response)
    logger.info(f"✅ Resultaat: {len(results)} aanbevelingen ontvangen")

    # Test 2: Edge case - Lege survey response
    logger.info("\n\n🧪 TEST 2: Edge case - Lege survey response")
    logger.info("📝 Verwerk lege survey response...")
    empty_results = handle_survey_response({})
    logger.info(f"✅ Resultaat: {len(empty_results)} aanbevelingen ontvangen (verwacht: 0)")

    # Test 3: Edge case - Ongeldige survey response type
    logger.info("\n\n🧪 TEST 3: Edge case - Ongeldige survey response type")
    logger.info("📝 Verwerk ongeldige survey response (string in plaats van dict)...")
    invalid_results = handle_survey_response("Dit is geen dict")
    logger.info(f"✅ Resultaat: {len(invalid_results)} aanbevelingen ontvangen (verwacht: 0)")

    # Test 4: Edge case - Survey response met ontbrekende velden
    logger.info("\n\n🧪 TEST 4: Edge case - Survey response met ontbrekende velden")
    partial_response = {
        "Card_Usage": "Luxe uitgaven",
        # Veel velden ontbreken
        "Monthly_Income": "20000"
    }
    logger.info("📝 Verwerk survey response met ontbrekende velden...")
    partial_results = handle_survey_response(partial_response)
    logger.info(f"✅ Resultaat: {len(partial_results)} aanbevelingen ontvangen")

    # Test 5: Edge case - Survey response met ongeldige waarden
    logger.info("\n\n🧪 TEST 5: Edge case - Survey response met ongeldige waarden")
    invalid_values_response = {
        "Card_Usage": "Luxe uitgaven",
        "Frequency": "Dagelijks",
        "Interest_Rate_Importance": "Laag",
        "Credit_Score": "niet-numeriek",  # Ongeldige waarde
        "Monthly_Income": None,  # Ongeldige waarde
        "Minimum_Income": "25000",
        "Interest_Rate": "twintig",  # Ongeldige waarde
        "Rewards": "Travel Miles",
        "Islamic": "ja"  # Ongeldige waarde
    }
    logger.info("📝 Verwerk survey response met ongeldige waarden...")
    invalid_values_results = handle_survey_response(invalid_values_response)
    logger.info(f"✅ Resultaat: {len(invalid_values_results)} aanbevelingen ontvangen")

    # Test 6: Gelijkaardige survey response (zou bestaande resultaten moeten hergebruiken)
    logger.info("\n\n🧪 TEST 6: Gelijkaardige survey response")
    similar_response = {
        "Card_Usage": "Luxe uitgaven",
        "Frequency": "Dagelijks",
        "Interest_Rate_Importance": "Laag",
        "Credit_Score": 94,  # Licht verschillend
        "Monthly_Income": "20100",  # Licht verschillend
        "Minimum_Income": "25000",
        "Interest_Rate": "20",
        "Rewards": "Travel Miles",
        "Islamic": 1
    }
    logger.info("📝 Verwerk gelijkaardige survey response...")
    similar_results = handle_survey_response(similar_response)
    logger.info(f"✅ Resultaat: {len(similar_results)} aanbevelingen ontvangen")

    logger.info("\n\n✅ Alle tests zijn voltooid!")

    # Toon een samenvatting van de resultaten
    logger.info("\n📊 Test resultaten samenvatting:")
    logger.info(f"Test 1 (Standaard): {len(results)} aanbevelingen")
    logger.info(f"Test 2 (Lege response): {len(empty_results)} aanbevelingen")
    logger.info(f"Test 3 (Ongeldig type): {len(invalid_results)} aanbevelingen")
    logger.info(f"Test 4 (Ontbrekende velden): {len(partial_results)} aanbevelingen")
    logger.info(f"Test 5 (Ongeldige waarden): {len(invalid_values_results)} aanbevelingen")
    logger.info(f"Test 6 (Gelijkaardige response): {len(similar_results)} aanbevelingen")

import sys
import os
import logging
from pathlib import Path

# Add the parent directory to the Python path
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent.parent.parent
sys.path.append(str(parent_dir.parent))

from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.credit_card_profiles_handler import handle_survey_response

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("credit_card_profile_test.log")
    ]
)

logger = logging.getLogger(__name__)

def run_tests():
    logger.info("🧪 Start test van credit_card_profiles_handler module")

    # Test 1: Standaard scenario met geldige survey response
    logger.info("\n🧪 TEST 1: Standaard scenario met geldige survey response")
    example_response = {
        "Card_Usage": "Luxe uitgaven",
        "Frequency": "Dagelijks",
        "Interest_Rate_Importance": "Laag",
        "Credit_Score": 95,
        "Monthly_Income": "20000",
        "Minimum_Income": "25000",
        "Interest_Rate": "20",
        "Rewards": "Travel Miles",
        "Islamic": 1,
        "Survey_ID": "58e947e1-18ed-4cce-b309-8b101b313342"
    }

    logger.info("📝 Verwerk standaard survey response...")
    results = handle_survey_response(example_response)
    logger.info(f"✅ Resultaat: {len(results)} aanbevelingen ontvangen")

    # Test 2: Edge case - Lege survey response
    logger.info("\n🧪 TEST 2: Edge case - Lege survey response")
    logger.info("📝 Verwerk lege survey response...")
    empty_results = handle_survey_response({})
    logger.info(f"✅ Resultaat: {len(empty_results)} aanbevelingen ontvangen (verwacht: 0)")

    # Test 3: Edge case - Ongeldige survey response type
    logger.info("\n🧪 TEST 3: Edge case - Ongeldige survey response type")
    logger.info("📝 Verwerk ongeldige survey response (string in plaats van dict)...")
    invalid_results = handle_survey_response("Dit is geen dict")
    logger.info(f"✅ Resultaat: {len(invalid_results)} aanbevelingen ontvangen (verwacht: 0)")

    # Test 4: Edge case - Survey response met ontbrekende velden
    logger.info("\n🧪 TEST 4: Edge case - Survey response met ontbrekende velden")
    partial_response = {
        "Card_Usage": "Luxe uitgaven",
        # Veel velden ontbreken
        "Monthly_Income": "20000",
        "Survey_ID": "8bb457da-fc89-45e9-935f-627d3471d413"
    }
    logger.info("📝 Verwerk survey response met ontbrekende velden...")
    partial_results = handle_survey_response(partial_response)
    logger.info(f"✅ Resultaat: {len(partial_results)} aanbevelingen ontvangen")

    # Test 5: Edge case - Survey response met ongeldige waarden
    logger.info("\n🧪 TEST 5: Edge case - Survey response met ongeldige waarden")
    invalid_values_response = {
        "Card_Usage": "Luxe uitgaven",
        "Frequency": "Dagelijks",
        "Interest_Rate_Importance": "Laag",
        "Credit_Score": "niet-numeriek",  # Ongeldige waarde
        "Monthly_Income": None,  # Ongeldige waarde
        "Minimum_Income": "25000",
        "Interest_Rate": "twintig",  # Ongeldige waarde
        "Rewards": "Travel Miles",
        "Islamic": "ja",  # Ongeldige waarde
        "Survey_ID": "d83867b0-ff66-4604-a7e4-8d44a4f2904f"
    }
    logger.info("📝 Verwerk survey response met ongeldige waarden...")
    invalid_values_results = handle_survey_response(invalid_values_response)
    logger.info(f"✅ Resultaat: {len(invalid_values_results)} aanbevelingen ontvangen")

    # Test 6: Gelijkaardige survey response (zou bestaande resultaten moeten hergebruiken)
    logger.info("\n🧪 TEST 6: Gelijkaardige survey response")
    similar_response = {
        "Card_Usage": "Luxe uitgaven",
        "Frequency": "Dagelijks",
        "Interest_Rate_Importance": "Laag",
        "Credit_Score": 94,  # Licht verschillend
        "Monthly_Income": "20100",  # Licht verschillend
        "Minimum_Income": "25000",
        "Interest_Rate": "20",
        "Rewards": "Travel Miles",
        "Islamic": 1,
        "Survey_ID": "b8229da6-ebff-4442-b8c9-88c4a02a3634"
    }
    logger.info("📝 Verwerk gelijkaardige survey response...")
    similar_results = handle_survey_response(similar_response)
    logger.info(f"✅ Resultaat: {len(similar_results)} aanbevelingen ontvangen")

    logger.info("\n\n✅ Alle tests zijn voltooid!")

    # Toon een samenvatting van de resultaten
    logger.info("\n📊 Test resultaten samenvatting:")
    logger.info(f"Test 1 (Standaard): {len(results)} aanbevelingen")
    logger.info(f"Test 2 (Lege response): {len(empty_results)} aanbevelingen")
    logger.info(f"Test 3 (Ongeldig type): {len(invalid_results)} aanbevelingen")
    logger.info(f"Test 4 (Ontbrekende velden): {len(partial_results)} aanbevelingen")
    logger.info(f"Test 5 (Ongeldige waarden): {len(invalid_values_results)} aanbevelingen")
    logger.info(f"Test 6 (Gelijkaardige response): {len(similar_results)} aanbevelingen")

if __name__ == "__main__":
    run_tests()
