# Credit Card Selector Tool - Architecture

## System Architecture

The Credit Card Selector Tool follows a modular architecture with clear separation of concerns. The diagram below illustrates the main components and their interactions:

```
+---------------------------------+
|                                 |
|     Web Scraping Layer          |
|     (Data_Handler/Scrape_Data)  |
|                                 |
+---------------+-----------------+
                |
                | CSV Files
                v
+---------------+-----------------+
|                                 |
|     Data Processing Layer       |
|     (Data_Handler/PreProcessor) |
|                                 |
+---------------+-----------------+
                |
                | Processed CSV
                v
+---------------+-----------------+
|                                 |
|     Storage Layer               |
|     (Credit_Card_Selector/      |
|      Database)                  |
|                                 |
+---------------+-----------------+
                ^
                | Data Access
                v
+---------------+-----------------+
|                                 |
|     API Layer                   |
|     (Credit_Card_Selector/      |
|      Server)                    |
|                                 |
+---------------+-----------------+
                ^
                | HTTP Requests
                v
+---------------+-----------------+
|                                 |
|     Client Applications         |
|     (Web, Mobile, etc.)         |
|                                 |
+---------------------------------+
```

## Component Interactions

### Data Flow

1. **Web Scraping Layer**
   - Bank-specific scrapers collect credit card information from bank websites
   - Data is saved to bank-specific CSV files

2. **Data Processing Layer**
   - Finds all CSV files from the scrapers
   - Merges the data into a single DataFrame
   - Categorizes the cards based on their benefits
   - Saves the processed data to CSV files

3. **Storage Layer**
   - Loads processed data into the vector database (Qdrant)
   - Provides functions for storing and retrieving credit card data
   - Handles survey processing and card recommendations

4. **API Layer**
   - Exposes functionality through RESTful endpoints
   - Processes HTTP requests and returns appropriate responses
   - Provides Swagger documentation for API exploration

5. **Client Applications**
   - Interact with the system through the API
   - Can be web applications, mobile apps, or other systems

### Key Processes

#### Credit Card Data Update Process
```
Bank Websites → Scrapers → CSV Files → PreProcessor → 
Merged CSV → Database Update → Vector Database
```

#### Survey Processing and Recommendation
```
Client → API Request → Survey Processing → 
Vector Embedding → Similar Survey Search → 
Card Filtering → Recommendation → API Response → Client
```

## Database Collections

The system uses two main collections in the Qdrant vector database:

1. **credit_cards**: Stores credit card information
   - Each card is represented as a document with various attributes
   - Cards are also represented as vectors for semantic search

2. **survey_responses**: Stores user survey responses and recommended cards
   - Each survey is represented as a document with the survey data and recommendations
   - Surveys are also represented as vectors for finding similar profiles

## Technology Stack

- **Backend**: Python, Flask
- **Database**: Qdrant (vector database)
- **Machine Learning**: Sentence Transformers for text embeddings
- **Web Scraping**: Selenium, BeautifulSoup
- **Data Processing**: Pandas, NumPy

## Extensibility

The modular architecture allows for easy extension:

1. **Adding New Banks**: Create new scraper modules in the Scrape_Data component
2. **Adding New API Endpoints**: Add new routes to the Server component
3. **Enhancing Recommendations**: Modify the card filtering or survey processing logic
4. **Supporting New Client Types**: The RESTful API can be consumed by any client type