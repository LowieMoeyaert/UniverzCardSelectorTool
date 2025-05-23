from flask import Flask, request, jsonify, render_template, send_from_directory
import os

# Import utility functions
from Credit_Card_Selector.Server.server_utils import (
    extract_filter_params, format_response, format_error
)
from Credit_Card_Selector.Server.swagger_utils import (
    setup_swagger, SWAGGER_JSON
)

# Import API functions
from Credit_Card_Selector.Database.Credit_Card_Handler.credit_card_api import (
    get_all_credit_cards, get_credit_card_by_id, filter_credit_cards
)
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.survey_api import (
    process_survey, get_all_survey_responses, get_survey_response_by_id
)
from Data_Handler.PreProcessor.data_processing_api import (
    merge_and_categorize
)

# Import database utilities
from Credit_Card_Selector.Database.general_utils import get_logger
from Credit_Card_Selector.Database.Credit_Card_Handler.credit_card_handler import (
    update_credit_cards_from_csv
)

# Create Flask app
app = Flask(__name__,
            static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'),
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))
logger = get_logger(__file__)

# Set up Swagger documentation
setup_swagger(app)

# Root route to serve Swagger UI
@app.route('/')
def index():
    """Serve the Swagger UI documentation."""
    return render_template('swagger.html')

# Serve swagger.json
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory(app.static_folder, path)


# API v1 routes
@app.route('/api/v1/process_survey', methods=['POST'])
def api_process_survey():
    """
    Process a survey response and return recommended credit cards.
    ---
    tags:
      - Credit Cards
    parameters:
      - in: body
        name: body
        description: Survey response data
        required: true
        schema:
          type: object
    responses:
      200:
        description: Successful operation
      400:
        description: Bad request
      500:
        description: Internal server error
    """
    try:
        data = request.get_json()
        if not data:
            logger.warning("❗ No JSON data received.")
            return format_error("No JSON data received.", 400)

        recommended_cards, error = process_survey(data)

        if error:
            return format_error(error, 400 if "No JSON data received" in error else 500)

        if not recommended_cards:
            return format_response("No suitable cards found.", "message")

        return format_response(recommended_cards, "recommended_cards")

    except Exception as e:
        logger.error(f"❌ Error processing survey: {str(e)}")
        return format_error(str(e), 500)


@app.route('/api/v1/credit_cards', methods=['POST'])
def api_update_database():
    """
    Update the credit card database with the latest CSV data.
    ---
    tags:
      - Credit Cards
    responses:
      200:
        description: Database successfully updated
      500:
        description: Internal server error
    """
    try:
        logger.info("🔹 Manual database update started...")

        # Call the function from credit_card_handler.py
        success, message, stats = update_credit_cards_from_csv()

        if not success:
            return format_error(message, 500)

        # Include stats in the response
        response_data = {
            "message": message,
            "stats": stats
        }

        logger.info("🔹 Database update completed!")
        return format_response(response_data, "result")
    except Exception as e:
        logger.error(f"❌ Error updating database: {str(e)}")
        return format_error(str(e), 500)


@app.route('/api/v1/credit_cards', methods=['GET'])
def api_get_all_credit_cards():
    """
    Get all credit cards from the database.
    ---
    tags:
      - Credit Cards
    responses:
      200:
        description: List of all credit cards
      500:
        description: Internal server error
    """
    try:
        cards, error = get_all_credit_cards()

        if error:
            return format_error(error, 500)

        if not cards:
            return format_response("No credit cards found.", "message")

        return format_response(cards, "credit_cards")

    except Exception as e:
        logger.error(f"❌ Error retrieving credit cards: {str(e)}")
        return format_error(str(e), 500)


@app.route('/api/v1/credit_cards/<card_id>', methods=['GET'])
def api_get_credit_card_by_id(card_id):
    """
    Get a specific credit card by ID.
    ---
    tags:
      - Credit Cards
    parameters:
      - name: card_id
        in: path
        description: ID of the credit card to retrieve
        required: true
        type: string
        example: "Etihad Guest Platinum Card"
    responses:
      200:
        description: Credit card details
        schema:
          type: object
          properties:
            credit_card:
              type: object
              description: Credit card details
      404:
        description: Credit card not found
      500:
        description: Internal server error
    """
    try:
        card, error = get_credit_card_by_id(card_id)

        if error:
            return format_error(error, 404 if "not found" in error else 500)

        return format_response(card, "credit_card")

    except Exception as e:
        logger.error(f"❌ Error retrieving credit card with ID '{card_id}': {str(e)}")
        return format_error(str(e), 500)


@app.route('/api/v1/survey_responses', methods=['GET'])
def api_get_all_survey_responses():
    """
    Get all survey responses from the database with optional filtering.
    ---
    tags:
      - Survey Responses
    parameters:
      - name: search_term
        in: query
        description: Text to search for in all fields of survey responses and recommended cards (GET method)
        required: false
        type: string
        example: "travel"
      - name: Credit_Score
        in: query
        description: Credit score to filter by (GET method)
        required: false
        type: integer
        example: 85
      - name: Monthly_Income
        in: query
        description: Monthly income to filter by (GET method)
        required: false
        type: string
        example: "15000"
      - name: Card_Type
        in: query
        description: Card type to filter by (GET method)
        required: false
        type: string
        example: "Platinum"
      - name: Rewards
        in: query
        description: Rewards type to filter by (GET method)
        required: false
        type: string
        example: "Travel Miles"
      - name: Card_Network
        in: query
        description: Card network to filter by (GET method)
        required: false
        type: string
        example: "Visa"
      - name: Islamic
        in: query
        description: Whether the card is Islamic (1) or not (0) (GET method)
        required: false
        type: integer
        example: 1
      - name: Interest_Rate
        in: query
        description: Interest rate to filter by (GET method)
        required: false
        type: string
        example: "15.5"
      - name: Minimum_Income
        in: query
        description: Minimum income requirement to filter by (GET method)
        required: false
        type: string
        example: "8000"
    responses:
      200:
        description: List of all survey responses
      500:
        description: Internal server error
    """
    try:
        # Get filter parameters using helper function
        filter_params = extract_filter_params()

        responses, error = get_all_survey_responses(filter_params)

        if error:
            return format_error(error, 500)

        if not responses:
            return format_response("No survey responses found.", "message")

        return format_response(responses, "survey_responses")

    except Exception as e:
        logger.error(f"❌ Error retrieving survey responses: {str(e)}")
        return format_error(str(e), 500)


@app.route('/api/v1/credit_cards/filter', methods=['GET', 'POST'])
def api_filter_credit_cards():
    """
    Filter credit cards based on parameters. If no parameters are provided, a default filter will be applied 
    showing credit cards with Credit_Score >= 80, Rewards = "Cashback", and Card_Type = "Gold".
    ---
    tags:
      - Credit Cards
    parameters:
      - name: search_term
        in: query
        description: Text to search for in all fields of credit cards (GET method)
        required: false
        type: string
        example: "cashback"
      - name: Credit_Score
        in: query
        description: Credit score to filter by (GET method)
        required: false
        type: integer
        example: 80
      - name: Monthly_Income
        in: query
        description: Monthly income to filter by (GET method)
        required: false
        type: string
        example: "12000"
      - name: Card_Type
        in: query
        description: Card type to filter by (GET method)
        required: false
        type: string
        example: "Gold"
      - name: Rewards
        in: query
        description: Rewards type to filter by (GET method)
        required: false
        type: string
        example: "Cashback"
      - name: Card_Network
        in: query
        description: Card network to filter by (GET method)
        required: false
        type: string
        example: "Mastercard"
      - name: Islamic
        in: query
        description: Whether the card is Islamic (1) or not (0) (GET method)
        required: false
        type: integer
        example: 0
      - name: Interest_Rate
        in: query
        description: Interest rate to filter by (GET method)
        required: false
        type: string
        example: "18.99"
      - name: Minimum_Income
        in: query
        description: Minimum income requirement to filter by (GET method)
        required: false
        type: string
        example: "5000"
    responses:
      200:
        description: List of filtered credit cards
      500:
        description: Internal server error
    """
    try:
        # Get filter parameters using helper function
        filter_params = extract_filter_params()

        cards, error = filter_credit_cards(filter_params)

        if error:
            return format_error(error, 500)

        if not cards:
            return format_response("No credit cards match the filter criteria.", "message")

        return format_response(cards, "credit_cards")

    except Exception as e:
        logger.error(f"❌ Error filtering credit cards: {str(e)}")
        return format_error(str(e), 500)


@app.route('/api/v1/survey_responses/<survey_id>', methods=['GET'])
def api_get_survey_response_by_id(survey_id):
    """
    Get a specific survey response by ID.
    ---
    tags:
      - Survey Responses
    parameters:
      - name: survey_id
        in: path
        description: ID of the survey response to retrieve
        required: true
        type: string
        example: "survey_123456"
    responses:
      200:
        description: Survey response details
        schema:
          type: object
          properties:
            survey_response:
              type: object
              properties:
                survey_id:
                  type: string
                  description: ID of the survey
                survey_data:
                  type: object
                  description: Survey response data
                recommended_cards:
                  type: array
                  description: List of recommended cards
                  items:
                    type: object
                timestamp:
                  type: string
                  description: Timestamp when the survey was submitted
      404:
        description: Survey response not found
      500:
        description: Internal server error
    """
    try:
        response, error = get_survey_response_by_id(survey_id)

        if error:
            return format_error(error, 404 if "not found" in error else 500)

        return format_response(response, "survey_response")

    except Exception as e:
        logger.error(f"❌ Error retrieving survey response with ID '{survey_id}': {str(e)}")
        return format_error(str(e), 500)


@app.route('/api/v1/merge_and_categorize', methods=['POST'])
def api_merge_and_categorize():
    """
    Merge and categorize credit card data from multiple sources.
    ---
    tags:
      - Data Processing
    responses:
      200:
        description: Credit card data successfully merged and categorized
      404:
        description: No non-empty CSV files found
      500:
        description: Internal server error
    """
    try:
        success, message = merge_and_categorize()

        if not success:
            status_code = 404 if "No non-empty CSV files found" in message else 500
            return format_error(message, status_code)

        return format_response(message, "message")

    except Exception as e:
        logger.error(f"❌ Error merging and categorizing data: {str(e)}")
        return format_error(str(e), 500)



# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return format_error("Resource not found", 404)

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors."""
    return format_error("Method not allowed", 405)

@app.errorhandler(500)
def internal_server_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {str(error)}")
    return format_error("Internal server error", 500)


if __name__ == '__main__':
    logger.info("🚀 Starting Credit Card Selector API Server...")
    logger.info("📚 API Documentation available at http://localhost:5000/")
    app.run(host='0.0.0.0', port=5000, debug=True)
