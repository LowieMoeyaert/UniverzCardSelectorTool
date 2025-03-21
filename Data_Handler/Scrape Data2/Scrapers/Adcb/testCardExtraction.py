import time
import unicodedata
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# List of failed URLs (populate this with your failed links)
FAILED_CARD_URLS = [
    "https://www.adcb.com/en/personal/cards/credit-cards/talabat-credit-card.aspx",
    "https://www.adcb.com/en/personal/cards/credit-cards/etihad-guest-infinite-credit-card.aspx",
    "https://www.adcb.com/en/personal/cards/credit-cards/etihad-signature-credit-card.aspx",
    "https://www.adcb.com/en/personal/cards/credit-cards/etihad-platinum-credit-card.aspx",
    "https://www.adcb.com/en/personal/cards/credit-cards/betaqti-credit-card.aspx",
    "https://www.adcb.com/en/personal/cards/credit-cards/adcb-lulu-credit-card.aspx",
    "https://www.adcb.com/en/personal/cards/credit-cards/adcb-lulu-titanium-gold-credit-card.aspx",
    "https://www.adcb.com/en/personal/cards/credit-cards/touchpoint-ic.aspx",
    "https://www.adcb.com/en/personal/cards/credit-cards/touchpoint-platinum-cc.aspx",
    "https://www.adcb.com/en/personal/cards/credit-cards/touchpoint-tg-cc.aspx",
]

def normalize_text(text):
    """Removes invisible characters and normalizes Unicode."""
    return unicodedata.normalize("NFKC", text).replace("\xa0", " ").strip()

def retry_failed_cards(driver, max_retries=3):
    """Attempts to scrape benefits only for previously failed cards."""
    successful_extractions = {}

    for card_url in FAILED_CARD_URLS:
        for attempt in range(max_retries):
            try:
                print(f"🔄 Retrying ({attempt + 1}/{max_retries}): {card_url}")
                driver.get(card_url)

                WebDriverWait(driver, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
                time.sleep(3)

                benefits = set()

                # ✅ Extract from `c-product-feature__list`
                feature_items = driver.find_elements(By.CLASS_NAME, "c-product-feature__item")
                for item in feature_items:
                    try:
                        title = item.find_element(By.CLASS_NAME, "c-feature-card__title").text.strip()
                        description = item.find_element(By.CLASS_NAME, "c-feature-card__summary").text.strip()
                        benefits.add(normalize_text(f"{title}: {description}"))
                    except Exception:
                        continue

                # ✅ Extract from `c-card-features__features`
                other_benefits = driver.find_elements(By.CLASS_NAME, "c-card-features__item")
                for item in other_benefits:
                    try:
                        title = item.find_element(By.CLASS_NAME, "c-card-features__feature").text.strip()
                        benefits.add(normalize_text(title))
                    except Exception:
                        continue

                # ✅ Extract from `js-acc-item` (Accordion-based sections)
                accordions = driver.find_elements(By.CLASS_NAME, "js-acc-item")
                for accordion in accordions:
                    try:
                        title_element = accordion.find_element(By.CLASS_NAME, "accordion-item__title")
                        driver.execute_script("arguments[0].scrollIntoView();", title_element)
                        title_element.click()
                        time.sleep(1)

                        expanded_content = accordion.find_elements(By.CLASS_NAME, "expand-content")
                        for content in expanded_content:
                            benefits.add(normalize_text(content.text))
                    except Exception:
                        continue

                # ✅ Extract from bullet points
                bullet_benefits = driver.find_elements(By.CSS_SELECTOR, ".o-bullet-points li")
                for item in bullet_benefits:
                    benefits.add(normalize_text(item.text))

                # ✅ Extract from image descriptions
                image_benefits = driver.find_elements(By.CLASS_NAME, "c-feature-card__img")
                for item in image_benefits:
                    alt_text = item.get_attribute("alt")
                    if alt_text:
                        benefits.add(normalize_text(alt_text))

                benefits = list(benefits)  # Convert set to list

                if benefits:
                    print(f"✅ Successfully extracted {len(benefits)} benefits for {card_url}")
                    for idx, benefit in enumerate(benefits, start=1):
                        print(f"  {idx}. {benefit}")

                    successful_extractions[card_url] = benefits
                    break  # If successful, stop retrying this card

            except Exception as e:
                print(f"⚠️ Attempt {attempt + 1}: Error scraping benefits ({str(e)}), retrying...")

            time.sleep(5)

        if card_url not in successful_extractions:
            print(f"❌ Still failed after {max_retries} attempts: {card_url}")

    return successful_extractions

def main():
    print("✅ main() started")

    try:
        # Start de web driver
        driver = webdriver.Chrome()
        print("🌍 WebDriver started")

        # Ga naar de pagina
        url = "https://www.adcb.com/en/personal/cards/credit-cards/talabat-credit-card.aspx"
        driver.get(url)
        print("🔗 Navigated to URL:", url)

        # Zoek naar elementen
        features = driver.find_elements(By.CLASS_NAME, "c-product-feature__item")
        print(f"🔍 Found {len(features)} features")

        if not features:
            print("⚠️ No features found!")

        driver.quit()
        print("✅ WebDriver closed")

    except Exception as e:
        print(f"❌ Error in main(): {e}")
