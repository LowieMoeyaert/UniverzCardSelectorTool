from Data_Handler.Scrape_Data.CSV.CSVHandler import CSVHandler, CSV_FILE
from Data_Handler.Scrape_Data.ScraperClasses.extractCardNetwork import extract_card_network
from Data_Handler.Scrape_Data.Scrapers.EmiratesNbd.BenefitExtractor import *

from Data_Handler.Scrape_Data.Scrapers.EmiratesNbd.CreditCardScraper import *
from Data_Handler.Scrape_Data.Scrapers.EmiratesNbd.RequirementExtractor import *
from Data_Handler.Scrape_Data.ScraperClasses.WebDriverSetup import *
# ✅ Constants
MAIN_URL = "https://www.emiratesnbd.com/en/cards/credit-cards"
BASE_URL = "https://www.emiratesnbd.com"


def set_card_type():
    """Returns the default card type."""
    return {"Card_Type": "1"}

# ✅ Main Execution
if __name__ == "__main__":
    CSVHandler.initialize_csv()
    web_driver_setup = WebDriverSetup()
    driver = web_driver_setup.get_driver()
    scraper = CreditCardScraper(driver, MAIN_URL)

    cards = scraper.fetch_cards()

    for index in range(len(cards)):
        try:
            fresh_cards = scraper.fetch_cards()
            card = fresh_cards[index]

            # ✅ Extract card details (including image)
            card_data = scraper.extract_card_data(card)

            if card_data:
                card_url = card_data[0]

                # ✅ Extract image (ensuring it's captured correctly)
                card_image = scraper.extract_image_url(card)

                # ✅ Extract benefits
                benefits = scrape_benefit_titles(card_url, driver)
                benefit_data = map_benefits_to_csv(benefits)

                # ✅ Extract Requirements (Minimum Salary, Interest Rate, Annual Fee)
                requirements = extract_requirements(card_url, driver)

                # ✅ Compile Data
                card_dict = {
                    "Bank_ID": 2,
                    "Card_Link": card_url,
                    "Card_Image": card_image,
                    "Card_ID": card_data[2],
                    "Card_Type": "1",
                    "Card_Network": extract_card_network(card_data[2]),
                    "Islamic": card_data[3],  # ✅ Add Islamic status
                }

                card_dict.update(benefit_data)  # ✅ Add benefits
                card_dict.update(requirements)  # ✅ Add requirements

                # ✅ Save to CSV
                CSVHandler.save_to_csv(card_dict)

            print(f"✅ Processed {index + 1}/{len(cards)} cards.\n")

        except Exception as e:
            print(f"❌ Error processing card {index + 1}: {e}")

    web_driver_setup.close()
    print(f"Data has been scraped and saved to {CSV_FILE}!")
