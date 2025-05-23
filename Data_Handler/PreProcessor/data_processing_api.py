import os
from typing import Dict, Any, Tuple, Optional
from Credit_Card_Selector.Database.general_utils import get_logger
from Data_Handler.PreProcessor.PreProcessing import (
    find_csv_files, merge_dataframes, load_dataframes, categorize_columns, save_dataframe
)

# Configure module logger
logger = get_logger(__file__)

def merge_and_categorize() -> Tuple[bool, str]:
    """
    Merge and categorize credit card data from multiple sources.
    
    Returns:
        Tuple containing:
        - Boolean indicating success or failure
        - Message describing the result
    """
    try:
        # Get the directory of the current script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Get the root directory (two levels up from current script)
        root_dir = os.path.dirname(os.path.dirname(current_dir))

        # Define paths relative to the root directory
        scrapers_folder = os.path.join(root_dir, 'Data_Handler', 'Scrape_Data', 'Scrapers')
        merged_output_file = os.path.join(current_dir, 'merged_credit_cards.csv')
        categorized_output_file = os.path.join(current_dir, 'categorized_credit_cards.csv')

        csv_files = find_csv_files(scrapers_folder)
        dataframes = load_dataframes(csv_files)

        if not dataframes:
            return False, "No non-empty CSV files found."

        merged_df = merge_dataframes(dataframes)
        save_dataframe(merged_df, merged_output_file)

        categorized_df = categorize_columns(merged_df)
        save_dataframe(categorized_df, categorized_output_file)

        return True, "Credit card data successfully merged and categorized."
    except Exception as e:
        error_msg = f"Error merging and categorizing data: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return False, error_msg