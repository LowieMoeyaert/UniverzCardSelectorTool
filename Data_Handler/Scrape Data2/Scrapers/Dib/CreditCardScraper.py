import time
from bs4 import BeautifulSoup
from prompt_toolkit.contrib.telnet.protocol import EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from ScraperClasses.determine_islamic_status import determine_islamic_status


class CreditCardScraper:
    def __init__(self, driver):
        self.driver = driver

    def fetch_page_source(self, url):
        """Load page, click 'Load More' until all cards are loaded, and return HTML."""
        self.driver.get(url)
        time.sleep(3)
        self.click_load_more()  # 🔥 Click 'Load More' before scraping
        self.scroll_to_bottom()
        return self.driver.page_source


    def scroll_to_bottom(self):
        """Scroll to the bottom to load all cards."""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Wait for new content to load
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def extract_cards(self, page_source, is_islamic_source):
        """Extract all credit card elements and return a list of dictionaries."""
        soup = BeautifulSoup(page_source, "html.parser")

        # ✅ Zoek naar kaarten in de juiste class
        card_elements = soup.select(".card-list-item")

        print(f"🔍 Found {len(card_elements)} total credit cards on page.")

        extracted_cards = []
        seen_card_links = set()  # ✅ Prevent duplicates at extraction level

        for card in card_elements:
            card_data = self.extract_card_data(card, is_islamic_source)
            if card_data:
                card_link = card_data["Card_Link"]
                if card_link in seen_card_links:
                    print(f"⚠️ Skipping duplicate at extraction: {card_data['Card_ID']}")
                    continue
                seen_card_links.add(card_link)
                print(f"✅ Extracted: {card_data['Card_ID']} | Link: {card_link}")
                extracted_cards.append(card_data)

        return extracted_cards

    def extract_card_data(self, card, is_islamic_source):
        """Extract credit card details."""
        try:
            # ✅ Extract Name
            name_element = card.select_one(".card-title-info a meta[itemprop='name']")
            name = name_element["content"].strip() if name_element else "Unknown Card"

            # ✅ Extract More Info Link
            info_element = card.select_one(".card-title-info a")
            detail_url = f"https://www.dib.ae{info_element['href']}" if info_element else "No Link"

            # ✅ Extract Minimum Salary
            min_salary = card.get("data-minimum-salary", "N/A")

            # ✅ Extract Image URL
            img_element = card.select_one(".card-img-container img")
            img_url = img_element["src"] if img_element else "No Image"

            # ✅ Handle missing details
            if name == "Unknown Card" or detail_url == "No Link":
                return None

            # ✅ Determine Islamic status
            is_islamic = determine_islamic_status(name, detail_url, is_islamic_source)

            return {
                "Bank_ID": 1,
                "Card_Link": detail_url,
                "Card_Image": img_url,
                "Card_ID": name,
                "Islamic": is_islamic,
                "Minimum_Income": min_salary
            }

        except Exception as e:
            print(f"❌ Error extracting card data: {e}")
            return None

    def click_load_more(self):
        """Click 'Load More' until no more cards are loaded."""
        while True:
            try:
                load_more_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".show-more-cards .show-more"))
                )
                print("🔄 Clicking 'Load More' button...")
                load_more_button.click()
                time.sleep(2)  # Wait for new content to load
            except Exception:
                print("✅ No more 'Load More' button found.")
                break
