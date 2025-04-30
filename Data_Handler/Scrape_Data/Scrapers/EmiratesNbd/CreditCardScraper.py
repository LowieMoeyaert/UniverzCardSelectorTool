import time
from selenium.webdriver.common.by import By
from Data_Handler.Scrape_Data.ScraperClasses.determine_islamic_status import determine_islamic_status

class CreditCardScraper:
    def __init__(self, driver, main_url):
        self.driver = driver
        self.main_url = main_url  # Store the main URL

    def fetch_cards(self):
        """Fetch all credit card elements."""
        self.driver.get(self.main_url)  # Use stored main URL
        time.sleep(3)

        # Scroll to load all cards
        self.scroll_to_bottom()
        cards = self.driver.find_elements(By.CSS_SELECTOR, ".cc-block")
        print(f"Found {len(cards)} credit cards.")  # Debugging
        return cards

    def scroll_to_bottom(self):
        """Scroll to ensure all cards are loaded."""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Wait for new content to load
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def extract_card_data(self, card):
        """Extract credit card details."""
        try:
            name = card.find_element(By.CSS_SELECTOR, ".cc-block__title").text.strip()
            detail_url = card.find_element(By.CSS_SELECTOR, "a[data-ctatext='know more']").get_attribute("href")
            img_url = self.extract_image_url(card)

            print(f"Scraping: {name} - {detail_url}")  # Debugging

            # ✅ Determine Islamic status
            is_islamic = determine_islamic_status(name, detail_url, is_islamic_source=False)

            return [detail_url, img_url, name, is_islamic]

        except Exception as e:
            print(f"Error extracting card data: {e}")  # Debugging
            return None

    def extract_image_url(self, card_element):
        """Extracts the credit card image URL from the main listing page and converts it to an absolute URL."""
        try:
            # Look inside the card block for the main image
            image_element = card_element.find_element(By.CSS_SELECTOR, "picture.cc-block__card img")

            # Extract the image URL (either from src or data-src)
            image_url = image_element.get_attribute("src") or image_element.get_attribute("data-src")

            # Convert to absolute URL if necessary
            if image_url and image_url.startswith("/-/media/"):
                image_url = f"https://www.emiratesnbd.com{image_url}"

            return image_url
        except Exception as e:
            print(f"⚠️ Failed to extract image URL: {e}")
            return None
