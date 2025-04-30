import time
from selenium.common import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class CreditCardScraper:
    def __init__(self, driver):
        self.driver = driver

    def fetch_and_extract_cards(self, url, is_islamic_source):
        """Load the page, wait for cards to load, and extract card details."""
        self.driver.get(url)

        if self.is_validation_page():
            print("⚠️ Validation page detected. Please resolve the captcha manually.")
            input("Press Enter to continue after resolving the captcha...")

        try:
            # Increase the timeout duration to 30 seconds
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.Card_card__28wfw.ProductCard_card__jZzpv"))
            )
        except TimeoutException:
            print("❌ Timeout waiting for cards to load.")
            self.save_page_source("timeout_page.html")
            return []
        except Exception as e:
            print(f"❌ Error waiting for cards to load: {e}")
            self.save_page_source("error_page.html")
            return []

        # Extract card elements
        card_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.Card_card__28wfw.ProductCard_card__jZzpv")
        print(f"🔍 Found {len(card_elements)} total credit cards on page.")

        if card_elements:
            print("HTML of the first found card:")
            print(card_elements[0].get_attribute('outerHTML'))

        extracted_cards = []
        seen_card_links = set()  # Prevent duplicates

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

    def is_validation_page(self):
        """Check if the current page is a validation page."""
        try:
            return "validate.perfdrive.com" in self.driver.current_url
        except Exception as e:
            print(f"❌ Error checking validation page: {e}")
            return False

    def extract_card_data(self, card_element, is_islamic_source):
        """Extract credit card details from a Selenium WebElement."""
        try:
            # Extract Name
            try:
                name_element = card_element.find_element(By.CSS_SELECTOR, "h5.Typography_h5__2CnIC")
                name = name_element.text.strip()
            except NoSuchElementException:
                name = "Unknown Card"

            # Extract More Info Link
            try:
                info_element = card_element.find_element(By.CSS_SELECTOR, "a.ProductCardTop_imageContainer__xrlQX")
                detail_url = info_element.get_attribute('href')

                # Ensure the URL is absolute
                if not detail_url.startswith("http"):  # Checks if it is a relative URL
                    detail_url = f"https://www.mashreqbank.com{detail_url}"
            except NoSuchElementException:
                detail_url = "No Link"

            # Extract Image URL
            try:
                img_element = card_element.find_element(By.CSS_SELECTOR, "img.ProductCardTop_image__11cdv")
                img_url = img_element.get_attribute('src')
                if not img_url.startswith("https://www.mashreqbank.com"):
                    img_url = f"https://www.mashreqbank.com{img_url}"
            except NoSuchElementException:
                img_url = "No Image"

            # Extract Description
            try:
                desc_element = card_element.find_element(By.CSS_SELECTOR, "p.Typography_body4__3fXWt")
                description = desc_element.text.strip()
            except NoSuchElementException:
                description = "No Description"

            # Debug Prints
            print(f"🟡 Extracting: {name} - {detail_url} - {img_url} - {description}")

            # Handle missing details
            if name == "Unknown Card" or detail_url == "No Link":
                print(f"⚠️ Skipping card: {name} (missing details)")
                return None

            # Determine Islamic status
            is_islamic = is_islamic_source  # Based on the page

            return {
                "Bank_ID": 2,
                "Card_Link": detail_url,
                "Card_Image": img_url,
                "Card_ID": name,
                "Islamic": is_islamic,
                "Description": description,
                "Minimum_Income": "N/A"
            }

        except Exception as e:
            print(f"❌ Error extracting card data: {e}")
            return None

    def save_page_source(self, filename):
        """Save the current page source to a file."""
        with open(filename, "w", encoding="utf-8") as file:
            file.write(self.driver.page_source)