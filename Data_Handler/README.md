# Data Handler Component Documentation

## Overview
The Data Handler component is responsible for collecting, processing, and preparing credit card data for use in the Credit Card Selector Tool. It consists of two main subcomponents: the PreProcessor and the Scrape_Data modules. Together, they form the data pipeline that feeds the recommendation system with up-to-date credit card information.

## Structure
The Data Handler component is organized into the following submodules:

### 1. PreProcessor
Processes and transforms raw credit card data into a standardized format suitable for the recommendation system.

#### Key Files:
- **PreProcessing.py**: Contains functions for merging and categorizing credit card data
- **data_processing_api.py**: Provides API functions for data processing operations

#### Main Functions:
- `find_csv_files`: Locates CSV files containing credit card data
- `load_dataframes`: Loads CSV files into pandas DataFrames
- `merge_dataframes`: Combines multiple DataFrames into a single DataFrame
- `categorize_columns`: Adds category flags to credit cards based on their benefits
- `merge_and_categorize`: Main function that orchestrates the entire processing pipeline

#### Output Files:
- **merged_credit_cards.csv**: Contains the merged data from all bank scrapers
- **categorized_credit_cards.csv**: Contains the merged data with additional category columns

### 2. Scrape_Data
Collects credit card data from various bank websites.

#### Key Directories:
- **CSV**: Contains utility functions for handling CSV files
- **ScraperClasses**: Contains base classes and utilities for scrapers
- **Scrapers**: Contains bank-specific scrapers

#### Bank-Specific Scrapers:
Each bank has its own scraper implementation with the following components:
- **BenefitExtractor.py**: Extracts benefit information from card pages
- **CreditCardScraper.py**: Scrapes basic card information
- **RequirementsExtractor.py**: Extracts eligibility requirements
- **Scraper_[BankName].py**: Main scraper file that orchestrates the scraping process

#### Supported Banks:
- ADIB (Abu Dhabi Islamic Bank)
- ADCB (Abu Dhabi Commercial Bank)
- BankFab (First Abu Dhabi Bank)
- DIB (Dubai Islamic Bank)
- EmiratesNBD
- HSBC
- Mashreq
- Rakbank

## Data Flow

1. **Data Collection**:
   - Bank-specific scrapers collect credit card information from bank websites
   - Each scraper extracts card details, benefits, and requirements
   - Data is saved to bank-specific CSV files

2. **Data Processing**:
   - The PreProcessor finds all CSV files from the scrapers
   - It merges the data into a single DataFrame
   - It categorizes the cards based on their benefits
   - The processed data is saved to CSV files

3. **Data Integration**:
   - The processed data is used to update the credit card database
   - The Credit_Card_Selector component uses this data for recommendations

## Usage Examples

### Running the Data Processing Pipeline
```python
from Data_Handler.PreProcessor.data_processing_api import merge_and_categorize

# Run the data processing pipeline
success, message = merge_and_categorize()
if success:
    print(f"Data processing successful: {message}")
else:
    print(f"Data processing failed: {message}")
```

### Running a Specific Bank Scraper
```python
# Example for ADIB scraper
from Data_Handler.Scrape_Data.Scrapers.ADIB.Scraper_ADIB import main as scrape_adib

# Run the ADIB scraper
scrape_adib()
```

## Data Categorization
The system categorizes credit cards based on their benefits into the following categories:

1. **Dining Benefits**: Cards that offer benefits for dining, such as cashback on restaurant purchases
2. **Travel Benefits**: Cards that offer travel-related benefits, such as airline miles or lounge access
3. **Shopping Benefits**: Cards that offer benefits for shopping, such as discounts or cashback
4. **Financial Benefits**: Cards that offer financial benefits, such as low interest rates or balance transfers

The categorization is done by checking if any of the predefined keywords for each category appear in the card's benefits.

## Extending the System

### Adding a New Bank Scraper
To add a new bank scraper:

1. Create a new directory under `Scrape_Data/Scrapers` with the bank name
2. Implement the following files:
   - BenefitExtractor.py
   - CreditCardScraper.py
   - RequirementsExtractor.py
   - Scraper_[BankName].py
3. Ensure the scraper saves data to a `credit_cards.csv` file in the bank's directory

### Modifying the Categorization Logic
To modify how cards are categorized:

1. Edit the `categorize_columns` function in `PreProcessing.py`
2. Update the `category_mapping` dictionary with new categories and keywords
3. Run the data processing pipeline to apply the changes

## Dependencies
The Data Handler component relies on the following external libraries:

- **pandas**: For data manipulation and analysis
- **selenium**: For web scraping (used by the bank scrapers)
- **beautifulsoup4**: For HTML parsing (used by some scrapers)

These dependencies should be installed as part of the project setup.