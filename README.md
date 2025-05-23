# Credit Card Selector Tool

## Overview
The Credit Card Selector Tool is a comprehensive system designed to help users find the most suitable credit cards based on their preferences and financial profile. The tool scrapes credit card data from various banks, processes and categorizes this data, and provides personalized recommendations through a survey-based approach.

## Features
- **Credit Card Database**: Maintains an up-to-date database of credit cards from multiple banks
- **Personalized Recommendations**: Recommends credit cards based on user survey responses
- **Semantic Matching**: Uses vector embeddings to find similar user profiles and their successful card matches
- **RESTful API**: Provides a comprehensive API for integrating with other applications
- **Interactive Documentation**: Includes Swagger UI for easy API exploration and testing

## Project Structure
The project is organized into three main components:

### 1. Credit_Card_Selector
- **Database**: Handles storage and retrieval of credit card and survey data
  - Credit_Card_Handler: Manages credit card data
  - Credit_Card_Profiles_Handler: Processes user surveys and recommends cards
- **Server**: Provides the API endpoints and web interface
  - Flask-based RESTful API
  - Swagger documentation

### 2. Data_Handler
- **PreProcessor**: Merges and categorizes credit card data
- **Scrape_Data**: Contains scrapers for different banks
  - Each bank has its own scraper implementation
  - Extracts credit card details, benefits, and requirements

## Installation

### Prerequisites
- Python 3.8 or higher
- Qdrant vector database
- Required Python packages (see requirements below)

### Setup
1. Obtain the software from Univerz's internal repository or IT department.

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (create a .env file in the project root):
```
VECTOR_SIZE=1024
SENTENCE_TRANSFORMER_MODEL=intfloat/multilingual-e5-large
```

4. Run the server:
```bash
python -m Credit_Card_Selector.Server.Server
```

Note: This software is for internal Univerz use only. Please contact the IT department for access and installation assistance.

## Usage

### API Endpoints

#### Survey Processing
```
POST /api/v1/process_survey
```
Submit a survey to get personalized credit card recommendations.

#### Credit Card Management
```
GET /api/v1/credit_cards
```
Retrieve all credit cards from the database.

```
GET /api/v1/credit_cards/{card_id}
```
Get a specific credit card by ID.

```
GET /api/v1/credit_cards/filter
```
Filter credit cards based on various criteria.

```
POST /api/v1/credit_cards
```
Update the credit card database with the latest CSV data.

#### Data Processing
```
POST /api/v1/merge_and_categorize
```
Merge and categorize credit card data from multiple sources.

### Example: Processing a Survey

```python
import requests
import json

# Survey data
survey_data = {
    "Monthly_Income": "15000",
    "Credit_Score": 85,
    "Card_Type": "Platinum",
    "Rewards": "Travel Miles",
    "Card_Network": "Visa",
    "Islamic": 0
}

# Send request
response = requests.post(
    "http://localhost:5000/api/v1/process_survey",
    json=survey_data
)

# Print results
print(json.dumps(response.json(), indent=2))
```

## Architecture

The system follows a modular architecture with clear separation of concerns:

1. **Data Collection Layer**: Scrapers collect credit card data from various bank websites
2. **Data Processing Layer**: Processes, merges, and categorizes the raw data
3. **Storage Layer**: Stores processed data in a vector database (Qdrant)
4. **Application Layer**: Provides business logic for card recommendations
5. **API Layer**: Exposes functionality through RESTful endpoints

### Key Components Interaction

1. Scrapers collect credit card data from bank websites
2. Data is processed, merged, and categorized
3. Processed data is stored in the Qdrant database
4. Users submit surveys through the API
5. The system processes the survey, finds similar profiles, and recommends cards
6. Results are returned through the API

## Proprietary Notice

This software is proprietary to Univerz. It is not open source and is not available for public distribution or contribution. All rights are reserved by Univerz.

## License

This project is licensed under a proprietary license agreement - see the LICENSE file for details. This software may only be used by Univerz and its authorized licensees in accordance with the terms of the license agreement.
