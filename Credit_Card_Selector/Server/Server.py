from flask import Flask, request, jsonify
from Credit_Card_Selector.Database.general_utils import get_logger, load_csv_data, create_collection_if_not_exists, \
    create_snapshot
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.credit_card_profiles_handler import (
    handle_survey_response
)

from Credit_Card_Selector.Database.Credit_Card_Handler.credit_card_handler import (
    update_or_add_credit_card, CREDIT_CARDS_COLLECTION, CSV_PATH
)
from Data_Handler.PreProcessor.PreProcessing import find_csv_files, merge_dataframes, load_dataframes, \
    categorize_columns, save_dataframe

app = Flask(__name__)
logger = get_logger(__file__)


@app.route('/process_survey', methods=['POST'])
def process_survey():
    """API-endpoint om een survey response te verwerken en kaartinfo te retourneren."""
    try:
        data = request.get_json()
        if not data:
            logger.warning("❗ Geen JSON-gegevens ontvangen.")
            return jsonify({"error": "Geen JSON-gegevens ontvangen."}), 400

        logger.info(f"📥 Binnengekomen surveydata: {data}")
        recommended_cards = handle_survey_response(data)

        if not recommended_cards:
            logger.info("📭 Geen geschikte kaarten gevonden.")
            return jsonify({"message": "Geen geschikte kaarten gevonden."}), 200

        logger.info(f"📤 Aanbevolen kaarten: {[card.get('Card_ID', 'onbekend') for card in recommended_cards]}")
        return jsonify({"recommended_cards": recommended_cards}), 200

    except Exception as e:
        logger.error(f"❌ Fout bij verwerken survey: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/update_credit_card', methods=['POST'])
def update_database():
    """API-endpoint om de database bij te werken met de nieuwste CSV-gegevens."""
    try:
        logger.info("🔹 Handmatige database-update gestart...")
        create_snapshot(CREDIT_CARDS_COLLECTION)
        create_collection_if_not_exists(CREDIT_CARDS_COLLECTION)

        data = load_csv_data(CSV_PATH)
        print(CSV_PATH + " " + str(data))
        if data is None:
            return jsonify({"error": "Kan CSV niet laden of is leeg."}), 500

        for _, row in data.iterrows():
            credit_card = row.to_dict()
            update_or_add_credit_card(credit_card)

        logger.info("🔹 Database-update voltooid!")
        return jsonify({"message": "Database succesvol bijgewerkt!"}), 200
    except Exception as e:
        logger.error(f"❌ Fout bij bijwerken van database: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/merge_and_categorize', methods=['POST'])
def merge_and_categorize():
    """API-endpoint om creditcardgegevens samen te voegen en te categoriseren."""
    try:
        scrapers_folder = '../../Data_Handler/Scrape_Data/Scrapers'
        merged_output_file = '../../Data_Handler/PreProcessor/merged_credit_cards.csv'
        categorized_output_file = '../../Data_Handler/PreProcessor/categorized_credit_cards.csv'

        csv_files = find_csv_files(scrapers_folder)
        dataframes = load_dataframes(csv_files)

        if not dataframes:
            return jsonify({"error": "Geen niet-lege CSV-bestanden gevonden."}), 404

        merged_df = merge_dataframes(dataframes)
        save_dataframe(merged_df, merged_output_file)

        categorized_df = categorize_columns(merged_df)
        save_dataframe(categorized_df, categorized_output_file)

        return jsonify({"message": "Creditcardgegevens succesvol samengevoegd en gecategoriseerd."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
