import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from Data_Handler.Scrape_Data.ScraperClasses.determine_islamic_status import determine_islamic_status

class CreditCardScraper:
    def __init__(self, driver):
        self.driver = driver

    def fetch_page_source(self, url):
        """Load page and return HTML source."""
        self.driver.get(url)
        time.sleep(3)
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

        # ✅ Handle normal cards
        card_elements = soup.select(".cards-list-grid-card")

        # ✅ Handle promotions page cards (if different structure)
        promo_card_elements = soup.select(".promo-card-wrapper")

        all_cards = card_elements + promo_card_elements  # ✅ Combine both types of cards

        print(f"🔍 Found {len(all_cards)} total credit cards on page.")

        extracted_cards = []
        seen_card_links = set()  # ✅ Prevent duplicates at extraction level

        for card in all_cards:
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
            name_element = card.select_one(".cl-card-desc-title")
            name = name_element.text.strip() if name_element else "Unknown Card"

            # ✅ Extract More Info Link
            info_element = card.select_one(".cl-card-desc-link a")
            detail_url = f"https://www.bankfab.com{info_element['href']}" if info_element else "No Link"

            # ✅ Extract Minimum Salary
            salary_element = card.select_one(".cl-card-desc-feature-value")
            min_salary = salary_element.text.replace("AED", "").strip() if salary_element else "N/A"

            # ✅ Extract Image URL
            img_url = self.extract_image_url(card, detail_url)

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

    def extract_image_url(self, card_element, detail_url):
        """Extracts the credit card image URL, handling missing cases."""
        try:
            image_element = card_element.select_one(".cl-card-header-image-wrapper img")
            if image_element:
                return image_element.get("src") or image_element.get("data-src") or "No Image"
            return self.extract_image_from_detail_page(detail_url)
        except Exception:
            return self.extract_image_from_detail_page(detail_url)

    def extract_image_from_detail_page(self, detail_url):
        """Fallback image extraction from detail page."""
        try:
            self.driver.get(detail_url)
            time.sleep(2)
            img_element = self.driver.find_element(By.CSS_SELECTOR, ".cl-card-header-image-wrapper img")
            return img_element.get_attribute("src") if img_element else "No Image"
        except Exception:
            return "No Image"
