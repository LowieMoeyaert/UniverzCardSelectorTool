import time
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class CreditCardScraper:
    def __init__(self, driver):
        self.driver = driver

    def fetch_and_extract_cards(self, url, is_islamic_source):
        """Load the page, wait for cards to load, and extract card details."""
        self.driver.get(url)

        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.M-CNT-ITEM-ART-DEV"))
            )
        except Exception as e:
            print(f"❌ Timeout waiting for cards to load: {e}")
            return []

        card_elements = self.driver.find_elements(By.CSS_SELECTOR, "li.M-CNT-ITEM-ART-DEV")
        print(f"🔍 Found {len(card_elements)} total credit cards on page.")

        extracted_cards = []
        seen_card_links = set()

        for card in card_elements:
            card_data = self.extract_card_data(card, is_islamic_source)
            if card_data:
                card_link = card_data["Card_Link"]
                if card_link in seen_card_links:
                    print(f"⚠️ Skipping duplicate: {card_data['Card_ID']}")
                    continue
                seen_card_links.add(card_link)
                print(f"✅ Extracted: {card_data['Card_ID']} | Link: {card_link}")
                extracted_cards.append(card_data)

        return extracted_cards

    def extract_card_data(self, card_element, is_islamic_source):
        """Extract credit card details from a Selenium WebElement."""
        try:
            # ✅ Extract Name
            try:
                name_element = card_element.find_element(By.CSS_SELECTOR, "h3.link-header a span.link.text")
                name = name_element.text.strip()
            except NoSuchElementException:
                name = "Unknown Card"

            # ✅ Extract More Info Link
            try:
                info_element = card_element.find_element(By.CSS_SELECTOR, "h3.link-header a")
                detail_url = info_element.get_attribute("href")
            except NoSuchElementException:
                detail_url = "No Link"

            # ✅ Extract Image URL
            try:
                img_element = card_element.find_element(By.CSS_SELECTOR, "div.smart-image img")
                img_url = img_element.get_attribute("src")
            except NoSuchElementException:
                img_url = "No Image"

            # ✅ Extract Description
            try:
                desc_element = card_element.find_element(By.CSS_SELECTOR, "div.text-container.text")
                description = desc_element.text.strip()
            except NoSuchElementException:
                description = "No Description"

            # ✅ Debug Prints
            print(f"🟡 Extracting: {name} - {detail_url} - {img_url} - {description}")

            if name == "Unknown Card" or detail_url == "No Link":
                print(f"⚠️ Skipping card: {name} (missing details)")
                return None

            is_islamic = is_islamic_source

            return {
                "Bank_ID": 8,
                "Card_Link": detail_url,
                "Card_Image": img_url,
                "Card_ID": name,
                "Islamic": is_islamic,
                "Description": description
            }

        except Exception as e:
            print(f"❌ Error extracting card data: {e}")
            return None
