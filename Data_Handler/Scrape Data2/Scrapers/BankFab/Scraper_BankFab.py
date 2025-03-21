from CSVHandler import CSVHandler
from ScraperClasses.WebDriverSetup import WebDriverSetup
from Scrapers.BankFab.CreditCardScraper import CreditCardScraper
from ScraperClasses.extractCardNetwork import extract_card_network
from Scrapers.BankFab.RequirementsExtractor import extract_requirements
from Scrapers.BankFab.BenefitExtractor import scrape_benefit_titles, map_benefits_to_csv

MAIN_URL = "https://www.bankfab.com/en-ae/personal/credit-cards"
MAIN_URL_ISLAMIC = "https://www.bankfab.com/en-ae/islamic-banking/personal-islamic-banking/islamic-cards"

if __name__ == "__main__":
    # ✅ Initialiseer CSV-bestand
    CSVHandler.initialize_csv()

    # ✅ Start Selenium WebDriver
    web_driver_setup = WebDriverSetup()
    driver = web_driver_setup.get_driver()
    scraper = CreditCardScraper(driver)

    saved_card_names = set()
    valid_columns = set(CSVHandler.COLUMNS)

    for url, is_islamic in [(MAIN_URL, False), (MAIN_URL_ISLAMIC, True)]:
        # ✅ Haal de pagina-inhoud op
        page_source = scraper.fetch_page_source(url)
        credit_cards = scraper.extract_cards(page_source, is_islamic)

        for card in credit_cards:
            if card["Card_ID"] in saved_card_names:
                continue
            saved_card_names.add(card["Card_ID"])

            # ✅ Extraheer netwerk (Visa, Mastercard, etc.)
            card["Card_Network"] = extract_card_network(card["Card_ID"])
            card["Islamic"] = "1" if card["Islamic"] else "0"

            # ✅ Voordelen scrapen en matchen met CSV-kolommen
            benefits = scrape_benefit_titles(card["Card_Link"], driver, max_retries=3)
            benefit_data = map_benefits_to_csv(benefits)
            filtered_benefit_data = {k: v for k, v in benefit_data.items() if k in valid_columns}
            card.update(filtered_benefit_data)

            # ✅ Vereisten (zoals minimum inkomen, jaarlijkse kosten) scrapen
            card_requirements = extract_requirements(card["Card_Link"], driver)

            # ✅ Als er meerdere resultaten zijn (overzichtspagina's), verwerk elk apart
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

    # ✅ Sluit de WebDriver sessie af
    web_driver_setup.close()
    print(f"✅ Scraping completed. Data saved to {CSVHandler.CSV_FILE}!")
