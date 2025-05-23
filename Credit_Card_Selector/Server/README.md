# Server Component Documentation

## Overview
The Server component provides a RESTful API for interacting with the Credit Card Selector Tool. It handles HTTP requests, processes them using the Database component, and returns appropriate responses. The server is built using Flask and includes Swagger documentation for easy API exploration.

## Structure
The Server component consists of the following files:

### Key Files
- **Server.py**: The main server file that defines all API endpoints and starts the Flask application
- **server_utils.py**: Contains utility functions for request handling and response formatting
- **swagger_utils.py**: Sets up Swagger documentation for the API

### Templates and Static Files
- **templates/swagger.html**: HTML template for the Swagger UI
- **static/swagger.json**: Swagger specification for the API

## API Endpoints

### Survey Processing
- **POST /api/v1/process_survey**: Process a survey response and return recommended credit cards
  - Accepts a JSON object containing survey responses
  - Returns a list of recommended credit cards based on the survey

### Credit Card Management
- **GET /api/v1/credit_cards**: Get all credit cards from the database
  - Returns a list of all credit cards in the database

- **GET /api/v1/credit_cards/{card_id}**: Get a specific credit card by ID
  - Returns details of a specific credit card

- **GET /api/v1/credit_cards/filter**: Filter credit cards based on parameters
  - Accepts query parameters for filtering
  - Returns a list of credit cards that match the filter criteria

- **POST /api/v1/credit_cards**: Update the credit card database with the latest CSV data
  - Triggers the database update process
  - Returns a status message and statistics about the update

### Survey Response Management
- **GET /api/v1/survey_responses**: Get all survey responses from the database
  - Returns a list of all survey responses in the database

- **GET /api/v1/survey_responses/{survey_id}**: Get a specific survey response by ID
  - Returns details of a specific survey response

### Data Processing
- **POST /api/v1/merge_and_categorize**: Merge and categorize credit card data from multiple sources
  - Triggers the data processing pipeline
  - Returns a status message about the operation

## Request and Response Handling

### Request Processing
The server extracts parameters from incoming requests using the `extract_filter_params` function in `server_utils.py`. This function handles both GET and POST requests, extracting parameters from query strings or JSON bodies.

### Response Formatting
Responses are formatted using the `format_response` and `format_error` functions in `server_utils.py`:

- `format_response`: Creates a standardized JSON response with the requested data
- `format_error`: Creates a standardized error response with an appropriate HTTP status code

## Swagger Documentation
The API is documented using Swagger, which provides an interactive UI for exploring and testing the API. The Swagger documentation is set up in `swagger_utils.py` and served at the root URL of the server.

### Accessing Swagger UI
When the server is running, you can access the Swagger UI at:
```
http://localhost:5000/
```

This provides a user-friendly interface to:
- View all available endpoints
- See request and response schemas
- Test endpoints directly from the browser

## Error Handling
The server includes comprehensive error handling to ensure robust operation:

- **404 Not Found**: Returned when a requested resource doesn't exist
- **405 Method Not Allowed**: Returned when an endpoint doesn't support the requested HTTP method
- **500 Internal Server Error**: Returned when an unexpected error occurs

All errors are logged for debugging purposes.

## Usage Example

### Starting the Server
```python
# Run the server
python -m Credit_Card_Selector.Server.Server
```

### Making API Requests
```python
import requests
import json

# Base URL for the API
base_url = "http://localhost:5000/api/v1"

# Get all credit cards
response = requests.get(f"{base_url}/credit_cards")
print(json.dumps(response.json(), indent=2))

# Filter credit cards
params = {
    "Card_Type": "Gold",
    "Rewards": "Cashback",
    "Credit_Score": 80
}
response = requests.get(f"{base_url}/credit_cards/filter", params=params)
print(json.dumps(response.json(), indent=2))

# Process a survey
survey_data = {
    "Monthly_Income": "15000",
    "Credit_Score": 85,
    "Card_Type": "Platinum",
    "Rewards": "Travel Miles",
    "Card_Network": "Visa",
    "Islamic": 0
}
response = requests.post(f"{base_url}/process_survey", json=survey_data)
print(json.dumps(response.json(), indent=2))
```

## Configuration
The server runs on port 5000 by default and listens on all interfaces (0.0.0.0). These settings can be modified in the `Server.py` file.

## Logging
The server uses the logging system defined in `general_utils.py` to log information about requests, responses, and errors. Logs are stored in the `Credit_Card_Selector/Logs` directory.