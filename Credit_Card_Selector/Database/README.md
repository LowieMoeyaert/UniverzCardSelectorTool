# Database Component Documentation

## Overview
The Database component is responsible for storing, retrieving, and managing credit card data and user survey responses. It uses Qdrant, a vector database, to enable semantic search capabilities and efficient data management.

## Structure
The Database component is organized into the following submodules:

### 1. Credit_Card_Handler
Manages the storage and retrieval of credit card data.

#### Key Files:
- **credit_card_api.py**: Provides API functions for retrieving and filtering credit cards
- **credit_card_handler.py**: Contains core functions for managing credit card data in the database

#### Main Functions:
- `update_or_add_credit_card`: Adds a new credit card or updates an existing one
- `find_existing_credit_card`: Searches for an existing credit card by ID or link
- `delete_credit_card`: Removes a credit card from the database
- `update_credit_cards_from_csv`: Updates the database with data from a CSV file

### 2. Credit_Card_Profiles_Handler
Processes user surveys and recommends credit cards based on user preferences.

#### Key Files:
- **card_filtering.py**: Filters credit cards based on survey criteria
- **credit_card_profiles_handler.py**: Manages user profiles and card recommendations
- **survey_api.py**: Provides API functions for processing surveys
- **survey_processing.py**: Processes survey responses and finds similar profiles
- **database_operations.py**: Contains database operations for retrieving cards
- **llm_interaction.py**: Handles interactions with language models for enhanced recommendations

#### Main Functions:
- `process_survey`: Processes a survey response and returns recommended cards
- `apply_manual_filters`: Filters credit cards based on survey data
- `embed_survey_response`: Generates vector representations of survey responses
- `search_similar_survey`: Finds similar survey responses in the database

### 3. Utility Files
- **general_utils.py**: Contains utility functions used across the database component
- **qdrant_config.py**: Configures the Qdrant client and connection

## Vector Database
The system uses Qdrant, a vector database, to store and retrieve data. This enables:

1. **Semantic Search**: Finding similar credit cards or survey responses based on meaning, not just exact matches
2. **Efficient Filtering**: Quickly filtering large datasets based on multiple criteria
3. **Vector Embeddings**: Representing text data as numerical vectors for machine learning applications

## Collections
The database uses the following collections:

1. **credit_cards**: Stores credit card information
2. **survey_responses**: Stores user survey responses and recommended cards

## Data Flow

1. **Data Ingestion**:
   - Credit card data is scraped from bank websites
   - Data is processed and categorized
   - Processed data is stored in the credit_cards collection

2. **Survey Processing**:
   - User submits a survey through the API
   - Survey is processed and converted to a vector representation
   - System searches for similar surveys in the database
   - If a similar survey exists, its recommendations are used
   - Otherwise, cards are filtered based on survey criteria

3. **Card Recommendation**:
   - Filtered cards are ranked based on relevance
   - Top cards are returned as recommendations
   - Survey and recommendations are stored for future reference

## Usage Examples

### Updating the Credit Card Database
```python
from Credit_Card_Selector.Database.Credit_Card_Handler.credit_card_handler import update_credit_cards_from_csv

# Update database with latest CSV data
success, message, stats = update_credit_cards_from_csv()
if success:
    print(f"Database updated successfully: {message}")
else:
    print(f"Database update failed: {message}")
```

### Processing a Survey
```python
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.survey_api import process_survey

# Survey data
survey_data = {
    "Monthly_Income": "15000",
    "Credit_Score": 85,
    "Card_Type": "Platinum",
    "Rewards": "Travel Miles",
    "Card_Network": "Visa",
    "Islamic": 0
}

# Process survey
recommended_cards, error = process_survey(survey_data)
if error:
    print(f"Error: {error}")
else:
    print(f"Recommended cards: {recommended_cards}")
```

## Configuration
The database component uses environment variables for configuration:

- `VECTOR_SIZE`: Size of the vector embeddings (default: 1024)
- `SENTENCE_TRANSFORMER_MODEL`: Model used for text embeddings (default: "intfloat/multilingual-e5-large")

These can be set in a .env file at the project root.