from flask import Flask, request, jsonify, render_template, send_from_directory, url_for
import os
import json
import inspect
import re
from typing import Dict, Any, Optional, List, Union
from Credit_Card_Selector.Database.general_utils import get_logger, load_csv_data, create_collection_if_not_exists, \
    create_snapshot
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.credit_card_profiles_handler import (
    handle_survey_response
)
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.database_operations import (
    fetch_all_cards, fetch_cards_by_ids
)
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.credit_card_profiles_handler_config import (
    CARDS_COLLECTION, SURVEY_COLLECTION, CARD_FETCH_LIMIT, FILTER_CONFIG
)
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.card_filtering import (
    apply_manual_filters
)
from Credit_Card_Selector.Database.Credit_Card_Handler.credit_card_handler import (
    update_or_add_credit_card, CREDIT_CARDS_COLLECTION, CSV_PATH, find_existing_credit_card
)
from Data_Handler.PreProcessor.PreProcessing import find_csv_files, merge_dataframes, load_dataframes, \
    categorize_columns, save_dataframe

# Create Flask app
app = Flask(__name__,
            static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'),
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))
logger = get_logger(__file__)

# Helper functions for parameter handling and response formatting
def extract_filter_params(allowed_params: List[str] = None) -> Dict[str, Any]:
    """
    Extract filter parameters from request (either query string or request body)

    Args:
        allowed_params: List of parameter names to extract. If None, uses default filter parameters.

    Returns:
        Dictionary of filter parameters
    """
    if allowed_params is None:
        allowed_params = ['search_term', 'Credit_Score', 'Monthly_Income', 'Card_Type', 
                         'Rewards', 'Card_Network', 'Islamic', 'Interest_Rate', 'Minimum_Income']

    filter_params = {}

    # Handle GET request parameters from query string
    if request.method == 'GET' and request.args:
        # Extract parameters from query string
        for param in allowed_params:
            if param in request.args:
                filter_params[param] = request.args.get(param)
                # Convert numeric values
                if param in ['Credit_Score', 'Islamic'] and filter_params[param].isdigit():
                    filter_params[param] = int(filter_params[param])
        logger.info(f"Received query parameters: {filter_params}")

    # Handle POST request parameters from body
    elif request.method == 'POST':
        if request.is_json:
            # Get all parameters from JSON
            json_data = request.get_json()
            for param in allowed_params:
                if param in json_data:
                    filter_params[param] = json_data[param]
            logger.info(f"Received JSON filter parameters: {filter_params}")
        elif request.data:
            # Try to parse text as JSON
            try:
                json_data = json.loads(request.data.decode('utf-8'))
                for param in allowed_params:
                    if param in json_data:
                        filter_params[param] = json_data[param]
                logger.info(f"Parsed text data as JSON: {filter_params}")
            except json.JSONDecodeError:
                # If not valid JSON, use the text as a search term
                search_term = request.data.decode('utf-8').strip()
                logger.info(f"Received text search term: {search_term}")
                if search_term:
                    # Create a simple filter that searches for the term in all fields
                    filter_params = {"search_term": search_term}

    return filter_params

def format_response(data: Any, message_key: str = "message", status_code: int = 200) -> tuple:
    """
    Format response with consistent structure

    Args:
        data: Data to include in response
        message_key: Key to use for the data in the response
        status_code: HTTP status code

    Returns:
        Tuple of (response_json, status_code)
    """
    return jsonify({message_key: data}), status_code

def format_error(error_message: str, status_code: int = 400) -> tuple:
    """
    Format error response with consistent structure

    Args:
        error_message: Error message
        status_code: HTTP status code

    Returns:
        Tuple of (response_json, status_code)
    """
    logger.warning(f"Error: {error_message}")
    return jsonify({"error": error_message}), status_code

# Create static and templates directories if they don't exist
os.makedirs(app.static_folder, exist_ok=True)
os.makedirs(app.template_folder, exist_ok=True)

# Create swagger.json file in static folder
SWAGGER_JSON = {
    "swagger": "2.0",
    "info": {
        "title": "Credit Card Selector API",
        "description": "API for selecting and managing credit cards",
        "version": "1.0.0"
    },
    "basePath": "/",
    "schemes": ["http"],
    "consumes": ["application/json"],
    "produces": ["application/json"],
    "paths": {
        "/api/v1/process_survey": {
            "post": {
                "summary": "Process survey response",
                "description": "Process a survey response and return recommended credit cards based on user preferences. The survey collects information about spending habits, income, credit score, and preferences for rewards, interest rates, and Islamic banking options. The system uses this information to filter and rank credit cards that best match the user's profile.",
                "parameters": [
                    {
                        "name": "body",
                        "in": "body",
                        "description": "Survey response data containing user preferences and financial information. Each field helps determine the most suitable credit cards.",
                        "required": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "Card_Usage": {
                                    "type": "string",
                                    "description": "Primary purpose for the credit card (e.g., 'Luxury spending', 'Daily expenses', 'Business', 'Travel')"
                                },
                                "Frequency": {
                                    "type": "string",
                                    "description": "How often the card will be used (e.g., 'Daily', 'Weekly', 'Monthly')"
                                },
                                "Interest_Rate_Importance": {
                                    "type": "string",
                                    "description": "How important interest rates are to the user (e.g., 'Low', 'Medium', 'High')"
                                },
                                "Credit_Score": {
                                    "type": "number",
                                    "description": "User's credit score (typically 0-100)"
                                },
                                "Monthly_Income": {
                                    "type": "string",
                                    "description": "User's monthly income in AED"
                                },
                                "Minimum_Income": {
                                    "type": "string",
                                    "description": "Minimum income requirement the user can meet in AED"
                                },
                                "Interest_Rate": {
                                    "type": "string",
                                    "description": "Preferred maximum interest rate as a percentage"
                                },
                                "Rewards": {
                                    "type": "string",
                                    "description": "Preferred reward type (e.g., 'Travel Miles', 'Cashback', 'Points')"
                                },
                                "Islamic": {
                                    "type": "number",
                                    "description": "Whether Islamic banking options are required (1 for yes, 0 for no)"
                                }
                            },
                            "examples": {
                                "luxury_traveler": {
                                    "summary": "Luxury Traveler Profile",
                                    "value": {
                                        "Card_Usage": "Luxury spending",
                                        "Frequency": "Daily",
                                        "Interest_Rate_Importance": "Low",
                                        "Credit_Score": 95,
                                        "Monthly_Income": "20000",
                                        "Minimum_Income": "25000",
                                        "Interest_Rate": "20",
                                        "Rewards": "Travel Miles",
                                        "Islamic": 1
                                    }
                                },
                                "everyday_user": {
                                    "summary": "Everyday User Profile",
                                    "value": {
                                        "Card_Usage": "Daily expenses",
                                        "Frequency": "Weekly",
                                        "Interest_Rate_Importance": "High",
                                        "Credit_Score": 75,
                                        "Monthly_Income": "10000",
                                        "Minimum_Income": "8000",
                                        "Interest_Rate": "15",
                                        "Rewards": "Cashback",
                                        "Islamic": 0
                                    }
                                }
                            }
                        }
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Successful operation",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "recommended_cards": {
                                    "type": "array",
                                    "description": "List of credit cards recommended based on the survey responses",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "Card_ID": {
                                                "type": "string",
                                                "description": "Unique identifier for the credit card"
                                            },
                                            "Card_Type": {
                                                "type": "string",
                                                "description": "Type or category of the credit card"
                                            },
                                            "Card_Network": {
                                                "type": "string",
                                                "description": "Payment network (e.g., Visa, Mastercard)"
                                            },
                                            "Reason For Choice": {
                                                "type": "string",
                                                "description": "Explanation of why this card was recommended"
                                            }
                                        }
                                    }
                                }
                            },
                            "examples": {
                                "luxury_traveler_response": {
                                    "summary": "Luxury Traveler Recommendations",
                                    "value": {
                                        "recommended_cards": [
                                            {
                                                "Card_ID": "ADCB_Traveller_Credit_Card",
                                                "Card_Type": "Traveller Credit Card",
                                                "Card_Network": "Visa",
                                                "Reason For Choice": "Best for travel rewards and luxury spending"
                                            },
                                            {
                                                "Card_ID": "ADIB_Etihad_Guest_Visa_Platinum_Card",
                                                "Card_Type": "Platinum Card",
                                                "Card_Network": "Visa",
                                                "Reason For Choice": "Islamic option with excellent travel benefits"
                                            }
                                        ]
                                    }
                                },
                                "everyday_user_response": {
                                    "summary": "Everyday User Recommendations",
                                    "value": {
                                        "recommended_cards": [
                                            {
                                                "Card_ID": "RAKBANK_Cashback_Card",
                                                "Card_Type": "Cashback Card",
                                                "Card_Network": "Mastercard",
                                                "Reason For Choice": "Excellent cashback on daily expenses"
                                            },
                                            {
                                                "Card_ID": "Emirates_NBD_Go4it_Card",
                                                "Card_Type": "Rewards Card",
                                                "Card_Network": "Visa",
                                                "Reason For Choice": "Good rewards for everyday spending with low fees"
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Bad request",
                        "schema": {
                            "type": "object",
                            "example": {
                                "error": "No JSON data received."
                            }
                        }
                    },
                    "500": {
                        "description": "Internal server error",
                        "schema": {
                            "type": "object",
                            "example": {
                                "error": "Error processing survey: Invalid data format."
                            }
                        }
                    }
                }
            }
        },
        "/api/v1/credit_cards": {
            "post": {
                "summary": "Update credit card database",
                "description": "Update the database with the latest CSV data",
                "responses": {
                    "200": {
                        "description": "Successful operation"
                    },
                    "500": {
                        "description": "Internal server error"
                    }
                }
            }
        },
        "/api/v1/merge_and_categorize": {
            "post": {
                "summary": "Merge and categorize credit card data",
                "description": "Merge and categorize credit card data from multiple sources",
                "responses": {
                    "200": {
                        "description": "Successful operation"
                    },
                    "404": {
                        "description": "No CSV files found"
                    },
                    "500": {
                        "description": "Internal server error"
                    }
                }
            }
        }
    }
}


# Initial Swagger JSON will be updated with all routes before the first request

# Create Swagger UI HTML file
SWAGGER_UI_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Credit Card Selector API</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@3/swagger-ui.css">
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: 'Arial', sans-serif;
        }
        .swagger-ui .topbar {
            background-color: #2C3E50;
        }
        .swagger-ui .info .title {
            color: #2C3E50;
        }
        .swagger-ui .opblock.opblock-post {
            background: rgba(73, 204, 144, 0.1);
            border-color: #49cc90;
        }
        .swagger-ui .btn.execute {
            background-color: #2C3E50;
        }
        .swagger-ui .btn.execute:hover {
            background-color: #1a242f;
        }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@3/swagger-ui-bundle.js"></script>
    <script>
        window.onload = function() {
            const ui = SwaggerUIBundle({
                url: "/static/swagger.json",
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
                layout: "BaseLayout",
                supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch'],
            });
            window.ui = ui;
        };
    </script>
</body>
</html>
"""

with open(os.path.join(app.template_folder, 'swagger.html'), 'w') as f:
    f.write(SWAGGER_UI_HTML)


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
def process_survey():
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

        logger.info(f"📥 Received survey data: {data}")
        recommended_cards = handle_survey_response(data)

        if not recommended_cards:
            logger.info("📭 No suitable cards found.")
            return format_response("No suitable cards found.", "message")

        logger.info(f"📤 Recommended cards: {[card.get('Card_ID', 'unknown') for card in recommended_cards]}")
        return format_response(recommended_cards, "recommended_cards")

    except Exception as e:
        logger.error(f"❌ Error processing survey: {str(e)}")
        return format_error(str(e), 500)


@app.route('/api/v1/credit_cards', methods=['POST'])
def update_database():
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
        create_snapshot(CREDIT_CARDS_COLLECTION)
        create_collection_if_not_exists(CREDIT_CARDS_COLLECTION)

        data = load_csv_data(CSV_PATH)
        if data is None:
            return format_error("Cannot load CSV or it is empty.", 500)

        for _, row in data.iterrows():
            credit_card = row.to_dict()
            update_or_add_credit_card(credit_card)

        logger.info("🔹 Database update completed!")
        return format_response("Database successfully updated!", "message")
    except Exception as e:
        logger.error(f"❌ Error updating database: {str(e)}")
        return format_error(str(e), 500)


@app.route('/api/v1/credit_cards', methods=['GET'])
def get_all_credit_cards():
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
        cards = fetch_all_cards(CREDIT_CARDS_COLLECTION, CARD_FETCH_LIMIT)

        if not cards:
            logger.info("No credit cards found in the database.")
            return format_response("No credit cards found.", "message")

        # Convert Qdrant points to dictionaries
        card_dicts = [card.payload for card in cards if hasattr(card, "payload")]

        logger.info(f"Retrieved {len(card_dicts)} credit cards.")
        return format_response(card_dicts, "credit_cards")

    except Exception as e:
        logger.error(f"❌ Error retrieving credit cards: {str(e)}")
        return format_error(str(e), 500)


@app.route('/api/v1/credit_cards/<card_id>', methods=['GET'])
def get_credit_card_by_id(card_id):
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
        # Find the credit card by ID
        card = find_existing_credit_card(card_id, None)

        if not card:
            logger.warning(f"Credit card with ID '{card_id}' not found.")
            return format_error(f"Credit card with ID '{card_id}' not found.", 404)

        logger.info(f"Retrieved credit card with ID '{card_id}'.")
        return format_response(card.payload, "credit_card")

    except Exception as e:
        logger.error(f"❌ Error retrieving credit card with ID '{card_id}': {str(e)}")
        return format_error(str(e), 500)


@app.route('/api/v1/survey_responses', methods=['GET'])
def get_all_survey_responses():
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
      - name: Credit_Score
        in: query
        description: Credit score to filter by (GET method)
        required: false
        type: integer
      - name: Monthly_Income
        in: query
        description: Monthly income to filter by (GET method)
        required: false
        type: string
      - name: Card_Type
        in: query
        description: Card type to filter by (GET method)
        required: false
        type: string
      - name: Rewards
        in: query
        description: Rewards type to filter by (GET method)
        required: false
        type: string
      - name: Card_Network
        in: query
        description: Card network to filter by (GET method)
        required: false
        type: string
      - name: Islamic
        in: query
        description: Whether the card is Islamic (1) or not (0) (GET method)
        required: false
        type: integer
      - name: Interest_Rate
        in: query
        description: Interest rate to filter by (GET method)
        required: false
        type: string
      - name: Minimum_Income
        in: query
        description: Minimum income requirement to filter by (GET method)
        required: false
        type: string
      - name: body
        in: body
        description: Filter criteria in JSON format or plain text search term (POST method)
        required: false
        schema:
          type: object
          properties:
            search_term:
              type: string
              description: Text to search for in all fields of survey responses and recommended cards
            Credit_Score:
              type: integer
              description: Credit score to filter by
            Monthly_Income:
              type: string
              description: Monthly income to filter by
            Card_Type:
              type: string
              description: Card type to filter by
            Rewards:
              type: string
              description: Rewards type to filter by
            Card_Network:
              type: string
              description: Card network to filter by
            Islamic:
              type: integer
              description: Whether the card is Islamic (1) or not (0)
            Interest_Rate:
              type: string
              description: Interest rate to filter by
            Minimum_Income:
              type: string
              description: Minimum income requirement to filter by
    responses:
      200:
        description: List of all survey responses
      500:
        description: Internal server error
    """
    try:
        responses = fetch_all_cards(SURVEY_COLLECTION, CARD_FETCH_LIMIT)

        if not responses:
            logger.info("No survey responses found in the database.")
            return format_response("No survey responses found.", "message")

        # Get filter parameters using helper function
        filter_params = extract_filter_params()

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
                if "search_term" in filter_params and filter_params["search_term"]:
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
                    from qdrant_client.models import PointStruct
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
        return format_response(response_dicts, "survey_responses")

    except Exception as e:
        logger.error(f"❌ Error retrieving survey responses: {str(e)}")
        return format_error(str(e), 500)


@app.route('/api/v1/credit_cards/filter', methods=['GET', 'POST'])
def filter_credit_cards():
    """
    Filter credit cards based on parameters.
    ---
    tags:
      - Credit Cards
    parameters:
      - name: search_term
        in: query
        description: Text to search for in all fields of credit cards (GET method)
        required: false
        type: string
      - name: Credit_Score
        in: query
        description: Credit score to filter by (GET method)
        required: false
        type: integer
      - name: Monthly_Income
        in: query
        description: Monthly income to filter by (GET method)
        required: false
        type: string
      - name: Card_Type
        in: query
        description: Card type to filter by (GET method)
        required: false
        type: string
      - name: Rewards
        in: query
        description: Rewards type to filter by (GET method)
        required: false
        type: string
      - name: Card_Network
        in: query
        description: Card network to filter by (GET method)
        required: false
        type: string
      - name: Islamic
        in: query
        description: Whether the card is Islamic (1) or not (0) (GET method)
        required: false
        type: integer
      - name: Interest_Rate
        in: query
        description: Interest rate to filter by (GET method)
        required: false
        type: string
      - name: Minimum_Income
        in: query
        description: Minimum income requirement to filter by (GET method)
        required: false
        type: string
      - name: body
        in: body
        description: Filter criteria in JSON format or plain text search term (POST method)
        required: false
        schema:
          type: object
          properties:
            search_term:
              type: string
              description: Text to search for in all fields of credit cards
            Credit_Score:
              type: integer
              description: Credit score to filter by
            Monthly_Income:
              type: string
              description: Monthly income to filter by
            Card_Type:
              type: string
              description: Card type to filter by
            Rewards:
              type: string
              description: Rewards type to filter by
            Card_Network:
              type: string
              description: Card network to filter by
            Islamic:
              type: integer
              description: Whether the card is Islamic (1) or not (0)
            Interest_Rate:
              type: string
              description: Interest rate to filter by
            Minimum_Income:
              type: string
              description: Minimum income requirement to filter by
    responses:
      200:
        description: List of filtered credit cards
      400:
        description: No filter parameters provided
      500:
        description: Internal server error
    """
    try:
        # Get filter parameters using helper function
        filter_params = extract_filter_params()

        if not filter_params:
            return format_error("No filter parameters provided. Please specify at least one filter.", 400)

        # Fetch all cards
        cards = fetch_all_cards(CREDIT_CARDS_COLLECTION, CARD_FETCH_LIMIT)

        if not cards:
            logger.info("No credit cards found in the database.")
            return format_response("No credit cards found.", "message")

        # Apply filters
        filtered_cards = apply_manual_filters(cards, filter_params)

        if not filtered_cards:
            logger.info("No credit cards match the filter criteria.")
            return format_response("No credit cards match the filter criteria.", "message")

        # Convert Qdrant points to dictionaries
        card_dicts = [card.payload for card in filtered_cards if hasattr(card, "payload")]

        logger.info(f"Retrieved {len(card_dicts)} credit cards after filtering.")
        return format_response(card_dicts, "credit_cards")

    except Exception as e:
        logger.error(f"❌ Error filtering credit cards: {str(e)}")
        return format_error(str(e), 500)


@app.route('/api/v1/survey_responses/<survey_id>', methods=['GET'])
def get_survey_response_by_id(survey_id):
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
        responses = fetch_all_cards(SURVEY_COLLECTION, CARD_FETCH_LIMIT)

        if not responses:
            logger.warning(f"Survey response with ID '{survey_id}' not found.")
            return format_error(f"Survey response with ID '{survey_id}' not found.", 404)

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
                    return format_response(response_dict, "survey_response")

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
                    return format_response(response_dict, "survey_response")

        logger.warning(f"Survey response with ID '{survey_id}' not found.")
        return format_error(f"Survey response with ID '{survey_id}' not found.", 404)

    except Exception as e:
        logger.error(f"❌ Error retrieving survey response with ID '{survey_id}': {str(e)}")
        return format_error(str(e), 500)


@app.route('/api/v1/merge_and_categorize', methods=['POST'])
def merge_and_categorize():
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
        scrapers_folder = 'Credit_Card_Selector/Data_Handler/Scrape_Data/Scrapers'
        merged_output_file = 'Credit_Card_Selector/Data_Handler/PreProcessor/merged_credit_cards.csv'
        categorized_output_file = 'Credit_Card_Selector/Data_Handler/PreProcessor/categorized_credit_cards.csv'

        csv_files = find_csv_files(scrapers_folder)
        dataframes = load_dataframes(csv_files)

        if not dataframes:
            return format_error("No non-empty CSV files found.", 404)

        merged_df = merge_dataframes(dataframes)
        save_dataframe(merged_df, merged_output_file)

        categorized_df = categorize_columns(merged_df)
        save_dataframe(categorized_df, categorized_output_file)

        return format_response("Credit card data successfully merged and categorized.", "message")
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

# Function to automatically generate Swagger paths from Flask routes
def generate_swagger_paths():
    """Generate Swagger paths from Flask routes and their docstrings."""
    paths = {}

    # Iterate through all routes in the Flask app
    for rule in app.url_map.iter_rules():
        # Skip static files and the root route
        if 'static' in rule.endpoint or rule.rule == '/':
            continue

        # Get the HTTP methods for this route
        methods = [method for method in rule.methods if method not in ['HEAD', 'OPTIONS']]

        # Skip if no methods
        if not methods:
            continue

        # Get the function for this route
        function = app.view_functions[rule.endpoint]

        # Get the docstring for this function
        docstring = inspect.getdoc(function) or ""

        # Extract summary and description from docstring
        summary = docstring.split('\n')[0] if docstring else rule.endpoint
        description = docstring if docstring else f"Endpoint for {rule.rule}"

        # Initialize parameters list
        parameters = []

        # Default parameters for routes with path parameters
        for arg in re.findall('<([^>]+)>', rule.rule):
            arg_name = arg.split(':')[-1]
            parameters.append({
                'name': arg_name,
                'in': 'path',
                'required': True,
                'type': 'string'
            })

        # Default responses
        responses = {
            '200': {'description': 'Successful operation'},
            '400': {'description': 'Bad request'},
            '500': {'description': 'Internal server error'}
        }

        # Add route to Swagger paths
        # Convert Flask path parameters (<param>) to Swagger path parameters ({param})
        path = re.sub(r'<([^>]+)>', r'{\1}', rule.rule)
        # If the parameter has a type prefix (e.g., <string:param>), remove it
        path = re.sub(r'{[^:]+:([^}]+)}', r'{\1}', path)

        for method in methods:
            method = method.lower()

            # Skip HEAD and OPTIONS methods
            if method in ['head', 'options']:
                continue

            # Initialize path if it doesn't exist
            if path not in paths:
                paths[path] = {}

            # Add method to path
            paths[path][method] = {
                'summary': summary,
                'description': description,
                'parameters': parameters,
                'responses': responses
            }

    return paths

# Update SWAGGER_JSON with automatically generated paths before starting the server
def update_swagger_json():
    auto_paths = generate_swagger_paths()
    for path, methods in auto_paths.items():
        if path not in SWAGGER_JSON["paths"]:
            SWAGGER_JSON["paths"][path] = methods
        else:
            for method, details in methods.items():
                if method not in SWAGGER_JSON["paths"][path]:
                    SWAGGER_JSON["paths"][path][method] = details

    # Write the updated Swagger JSON to file
    with open(os.path.join(app.static_folder, 'swagger.json'), 'w') as f:
        json.dump(SWAGGER_JSON, f)

    logger.info("✅ Swagger documentation updated with all routes!")

# Register a function to run before the first request
@app.before_request
def before_first_request():
    # Use a global variable to track if this is the first request
    if not hasattr(app, 'swagger_updated'):
        update_swagger_json()
        app.swagger_updated = True

if __name__ == '__main__':
    logger.info("🚀 Starting Credit Card Selector API Server...")
    logger.info("📚 API Documentation available at http://localhost:5000/")
    app.run(host='0.0.0.0', port=5000, debug=True)
