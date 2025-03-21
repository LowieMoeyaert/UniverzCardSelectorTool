import time
import re
from typing import List
from CSVHandler import CSVHandler
import unicodedata
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def normalize_text(text):
    """Removes invisible characters and normalizes Unicode."""
    return unicodedata.normalize("NFKC", text).replace("\xa0", " ").strip()


def scrape_benefits(card_url, driver, max_retries=3):
    """Extracts benefits from the card details page based on the new website structure."""
    max_retries = int(max_retries)
    for attempt in range(max_retries):
        try:
            print(f"🟡 Attempt {attempt + 1}: Scraping benefits for {card_url}")
            driver.get(card_url)

            WebDriverWait(driver, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
            time.sleep(3)

            benefits = set()  # Use a set to avoid duplicates

            # ✅ Extract benefits from `c-product-feature__list` (Main benefits section)
            feature_items = driver.find_elements(By.CLASS_NAME, "c-product-feature__item")
            for item in feature_items:
                try:
                    title = item.find_element(By.CLASS_NAME, "c-feature-card__title").text.strip()
                    description = item.find_element(By.CLASS_NAME, "c-feature-card__summary").text.strip()
                    benefits.add(normalize_text(f"{title}: {description}"))
                except Exception:
                    continue

            # ✅ Extract benefits from `c-card-features__features` (Other credit card benefits)
            other_benefits = driver.find_elements(By.CLASS_NAME, "c-card-features__item")
            for item in other_benefits:
                try:
                    title = item.find_element(By.CLASS_NAME, "c-card-features__feature").text.strip()
                    benefits.add(normalize_text(title))
                except Exception:
                    continue

            # ✅ Extract benefits from `js-acc-item` (Accordion-based benefits)
            accordions = driver.find_elements(By.CLASS_NAME, "js-acc-item")
            for accordion in accordions:
                try:
                    # Click to expand if collapsed
                    title_element = accordion.find_element(By.CLASS_NAME, "accordion-item__title")
                    driver.execute_script("arguments[0].scrollIntoView();", title_element)
                    title_element.click()
                    time.sleep(1)  # Allow content to load

                    expanded_content = accordion.find_elements(By.CLASS_NAME, "expand-content")
                    for content in expanded_content:
                        benefits.add(normalize_text(content.text))
                except Exception:
                    continue

            # ✅ Extract benefits from bullet points
            bullet_benefits = driver.find_elements(By.CSS_SELECTOR, ".o-bullet-points li")
            for item in bullet_benefits:
                benefits.add(normalize_text(item.text))

            # ✅ Extract benefits from image descriptions
            image_benefits = driver.find_elements(By.CLASS_NAME, "c-feature-card__img")
            for item in image_benefits:
                alt_text = item.get_attribute("alt")
                if alt_text:
                    benefits.add(normalize_text(alt_text))

            benefits = list(benefits)  # Convert back to list

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
    """Match benefits to CSV columns using regex patterns and provide debug output."""
    COLUMN_PATTERNS = {
    }
    """Match benefits met CSV-kolommen en voeg automatisch nieuwe categorieën toe als nodig."""
    row_data = {col: "0" for col in COLUMN_PATTERNS.keys()}  # Initieel alles op 0
    unmapped_benefits = []  # Opslaan van niet-gematchte voordelen

    for benefit in benefits:
        mapped = False
        for column, pattern in COLUMN_PATTERNS.items():
            if pattern.search(benefit):  # ✅ Controleer op match
                row_data[column] = "1"
                mapped = True
        if not mapped:
            unmapped_benefits.append(benefit)  # Onbekende voordelen opslaan

    # ✅ Voeg ontbrekende categorieën toe aan de CSV als ze niet bestaan
    # ✅ Voeg ontbrekende categorieën toe aan de CSV als ze niet bestaan
    for new_category in unmapped_benefits:
        formatted_category = f"Uncategorized - {new_category[:30]}"  # Max 30 tekens
        CSVHandler.add_missing_category(formatted_category)

        # ✅ Zorg dat de nieuwe categorie in valid_columns komt
        valid_columns.add(formatted_category)

        # ✅ Voeg de nieuwe categorie direct toe aan row_data met waarde "1"
        row_data[formatted_category] = "1"

    return row_data
