import os
import json
import inspect
import re
from flask import Flask
from typing import Dict, Any

def generate_swagger_paths(app: Flask) -> Dict[str, Any]:
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

def update_swagger_json(app: Flask, swagger_json: Dict[str, Any]) -> None:
    """
    Update Swagger JSON with automatically generated paths and write to file.
    
    Args:
        app: Flask application instance
        swagger_json: Base Swagger JSON configuration
    """
    auto_paths = generate_swagger_paths(app)
    for path, methods in auto_paths.items():
        if path not in swagger_json["paths"]:
            swagger_json["paths"][path] = methods
        else:
            for method, details in methods.items():
                if method not in swagger_json["paths"][path]:
                    swagger_json["paths"][path][method] = details

    # Write the updated Swagger JSON to file
    with open(os.path.join(app.static_folder, 'swagger.json'), 'w') as f:
        json.dump(swagger_json, f)

    app.logger.info("✅ Swagger documentation updated with all routes!")

# Create Swagger UI HTML template
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

# Base Swagger JSON configuration
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
        }
    }
}

def setup_swagger(app: Flask) -> None:
    """
    Set up Swagger documentation for the Flask app.
    
    Args:
        app: Flask application instance
    """
    # Create static and templates directories if they don't exist
    os.makedirs(app.static_folder, exist_ok=True)
    os.makedirs(app.template_folder, exist_ok=True)
    
    # Write Swagger UI HTML to template file
    with open(os.path.join(app.template_folder, 'swagger.html'), 'w') as f:
        f.write(SWAGGER_UI_HTML)
    
    # Register a function to run before the first request to update Swagger JSON
    @app.before_request
    def before_first_request():
        # Use a global variable to track if this is the first request
        if not hasattr(app, 'swagger_updated'):
            update_swagger_json(app, SWAGGER_JSON)
            app.swagger_updated = True