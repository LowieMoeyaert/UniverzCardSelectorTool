import re
import time
import unicodedata
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from CSVHandler import CSVHandler


def normalize_text(text):
    """Removes invisible characters and normalizes Unicode."""
    return unicodedata.normalize("NFKC", text).replace("\xa0", " ").strip()


def scrape_benefits(card_url, driver, max_retries=3):
    """Extracts benefits from the card details page, including new website structures."""
    max_retries = int(max_retries)
    for attempt in range(max_retries):
        try:
            print(f"🟡 Attempt {attempt + 1}: Scraping benefits for {card_url}")
            driver.get(card_url)

            WebDriverWait(driver, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
            time.sleep(3)

            benefits = set()  # Avoid duplicates

            # ✅ Nieuwe HTML secties verwerken

            # ✅ `feature-card` sectie (Swiper-slide benefits)
            feature_cards = driver.find_elements(By.CLASS_NAME, "feature-card")
            for card in feature_cards:
                try:
                    title = card.find_element(By.CLASS_NAME, "feature-card__heading").text.strip()
                    description = card.find_element(By.TAG_NAME, "p").text.strip()
                    benefits.add(normalize_text(f"{title}: {description}"))
                except Exception:
                    continue

            # ✅ `benefit-card` sectie (Nieuwe tab-panel voordelen)
            benefit_cards = driver.find_elements(By.CLASS_NAME, "benefit-card__content")
            for card in benefit_cards:
                try:
                    title = card.find_element(By.CLASS_NAME, "h4").text.strip()
                    benefits.add(normalize_text(title))
                except Exception:
                    continue

            # ✅ `c-product-feature__list` sectie (Main benefits)
            feature_items = driver.find_elements(By.CLASS_NAME, "c-product-feature__item")
            for item in feature_items:
                try:
                    title = item.find_element(By.CLASS_NAME, "c-feature-card__title").text.strip()
                    description = item.find_element(By.CLASS_NAME, "c-feature-card__summary").text.strip()
                    benefits.add(normalize_text(f"{title}: {description}"))
                except Exception:
                    continue

            # ✅ `c-card-features__features` sectie (Andere voordelen)
            other_benefits = driver.find_elements(By.CLASS_NAME, "c-card-features__item")
            for item in other_benefits:
                try:
                    title = item.find_element(By.CLASS_NAME, "c-card-features__feature").text.strip()
                    benefits.add(normalize_text(title))
                except Exception:
                    continue

            # ✅ `js-acc-item` sectie (Accordion)
            accordions = driver.find_elements(By.CLASS_NAME, "js-acc-item")
            for accordion in accordions:
                try:
                    title_element = accordion.find_element(By.CLASS_NAME, "accordion-item__title")
                    driver.execute_script("arguments[0].scrollIntoView();", title_element)
                    title_element.click()
                    time.sleep(1)  # Content laten laden

                    expanded_content = accordion.find_elements(By.CLASS_NAME, "expand-content")
                    for content in expanded_content:
                        benefits.add(normalize_text(content.text))
                except Exception:
                    continue

            # ✅ Bullet points
            bullet_benefits = driver.find_elements(By.CSS_SELECTOR, ".o-bullet-points li")
            for item in bullet_benefits:
                benefits.add(normalize_text(item.text))

            # ✅ Image alt text (afbeeldingsbeschrijvingen)
            image_benefits = driver.find_elements(By.CLASS_NAME, "custom-img")
            for item in image_benefits:
                alt_text = item.get_attribute("alt")
                if alt_text:
                    benefits.add(normalize_text(alt_text))

            benefits = list(benefits)  # Zet set om naar lijst

            if benefits:
                print(f"✅ Successfully extracted {len(benefits)} benefits for {card_url}")
                for idx, benefit in enumerate(benefits, start=1):
                    print(f"  {idx}. {benefit}")

                return benefits

        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1}: Error scraping benefits ({str(e)}), retrying...")

        time.sleep(5)

    print(f"❌ Failed to scrape benefits after {max_retries} attempts.")
    return []


def map_benefits_to_csv(benefits, valid_columns=None):
    """Match benefits to CSV columns using regex patterns and dynamically add new categories."""
    COLUMN_PATTERNS = {
        "Cashback": r"cashback",
        "Dining Discounts": r"dining|restaurant",
        "Shopping Discounts": r"shopping|retail",
        "Entertainment Offers": r"entertainment|movies|shows",
        "Travel Perks": r"travel|airport|lounge",
    }

    row_data = {col: "0" for col in COLUMN_PATTERNS.keys()}  # Init alles op "0"
    unmapped_benefits = []  # Opslaan van niet-gematchte voordelen

    for benefit in benefits:
        mapped = False
        for column, pattern in COLUMN_PATTERNS.items():
            if re.search(pattern, benefit, re.IGNORECASE):  # ✅ Check op match
                row_data[column] = "1"
                mapped = True
        if not mapped:
            unmapped_benefits.append(benefit)  # Onbekende voordelen opslaan

    # ✅ Voeg onbekende voordelen als nieuwe kolommen toe
    for new_category in unmapped_benefits:
        formatted_category = f"Uncategorized - {new_category[:30]}"  # Max 30 tekens
        CSVHandler.add_missing_category(formatted_category)
        valid_columns.add(formatted_category)
        row_data[formatted_category] = "1"

    return row_data
