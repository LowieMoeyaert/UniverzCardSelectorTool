from CSVHandler import CSVHandler
from ScraperClasses.WebDriverSetup import WebDriverSetup
from Scrapers.Adcb.CreditCardScraper import CreditCardScraper
from Scrapers.Adcb.RequirementsExtractor import extract_requirements
from Scrapers.Adcb.BenefitExtractor import scrape_benefits, map_benefits_to_csv  # ✅ Mappingfunctie toegevoegd

MAIN_URL = "https://www.adcb.com/en/personal/cards/credit-cards/#credit-card"
MAIN_URL_ISLAMIC = "https://www.adcb.com/en/islamic/personal/cards/#covered-card"

if __name__ == "__main__":
    # ✅ Initialize CSV file
    CSVHandler.initialize_csv()

    # ✅ Start Selenium WebDriver
    web_driver_setup = WebDriverSetup()
    driver = web_driver_setup.get_driver()
    scraper = CreditCardScraper(driver)

    saved_card_names = set()
    valid_columns = set(CSVHandler.COLUMNS)  # ✅ Bepaal de geldige kolommen in de CSV

    for url, is_islamic in [(MAIN_URL, False), (MAIN_URL_ISLAMIC, True)]:
        # ✅ Fetch and extract card details
        credit_cards = scraper.fetch_and_extract_cards(url, is_islamic)
        print(f"🔍 Extracted {len(credit_cards)} cards to process for saving.")

        for card in credit_cards:
            if card["Card_ID"] in saved_card_names:
                print(f"⚠️ Skipping duplicate: {card['Card_ID']}")
                continue
            saved_card_names.add(card["Card_ID"])

            # ✅ Extract eligibility requirements dynamically
            try:
                card_requirements = extract_requirements(card["Card_Link"], driver)
            except Exception as e:
                print(f"❌ Error extracting requirements for {card['Card_ID']}: {e}")
                card_requirements = {}

            # ✅ Extract benefits dynamically
            try:
                benefits = scrape_benefits(card["Card_Link"], driver, max_retries=3)
                benefit_data = map_benefits_to_csv(benefits, valid_columns)                # ✅ Map de benefits naar CSV-structuur
                filtered_benefit_data = {k: v for k, v in benefit_data.items() if k in valid_columns}  # ✅ Filter geldige kolommen
                card.update(filtered_benefit_data)
            except Exception as e:
                print(f"❌ Error extracting benefits for {card['Card_ID']}: {e}")

            print(f"✅ Saving card: {card['Card_ID']} to CSV")

            # ✅ Als er meerdere resultaten zijn, opsplitsen
            if isinstance(card_requirements, list):
                for req in card_requirements:
                    merged_card = card.copy()
                    merged_card.update(req)
                    print(f"✅ Saving card: {merged_card['Card_ID']} to CSV")
                    CSVHandler.save_to_csv(merged_card)
            else:
                card.update(card_requirements)
                print(f"✅ Saving card: {card['Card_ID']} to CSV")
                CSVHandler.save_to_csv(card)

    # ✅ Close the WebDriver session
    web_driver_setup.close()
    print(f"✅ Scraping completed. Data saved to {CSVHandler.CSV_FILE}!")
