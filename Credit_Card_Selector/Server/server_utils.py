from flask import jsonify
from typing import Any, Dict, List, Optional
from Credit_Card_Selector.Database.general_utils import get_logger

# Configure module logger
logger = get_logger(__file__)

def extract_filter_params(allowed_params: List[str] = None) -> Dict[str, Any]:
    """
    Extract filter parameters from request (either query string or request body)

    Args:
        allowed_params: List of parameter names to extract. If None, uses default filter parameters.

    Returns:
        Dictionary of filter parameters
    """
    from flask import request
    import json
    
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