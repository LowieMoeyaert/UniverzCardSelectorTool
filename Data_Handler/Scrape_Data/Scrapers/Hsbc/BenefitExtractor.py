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
    """Extracts benefits from the card details page based on the provided HTML structure."""
    max_retries = int(max_retries)
    for attempt in range(max_retries):
        try:
            print(f"🟡 Attempt {attempt + 1}: Scraping benefits for {card_url}")
            driver.get(card_url)

            WebDriverWait(driver, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
            time.sleep(3)

            benefits = set()

            # ✅ Exceed Rewards sectie
            reward_sections = driver.find_elements(By.CLASS_NAME, "block-content-main-center")
            for section in reward_sections:
                try:
                    title = section.find_element(By.TAG_NAME, "h2").text.strip()
                    description = section.find_element(By.TAG_NAME, "p").text.strip()
                    benefits.add(normalize_text(f"{title}: {description}"))
                except Exception:
                    continue

            # ✅ Extra details zoals voetnoten
            footnotes = driver.find_elements(By.CLASS_NAME, "ExternalClass0E739782BD1B48FD9B985B31205DB6AC")
            for note in footnotes:
                try:
                    benefits.add(normalize_text(note.text))
                except Exception:
                    continue

            benefits = list(benefits)

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

    row_data = {col: "0" for col in COLUMN_PATTERNS.keys()}
    unmapped_benefits = []

    for benefit in benefits:
        mapped = False
        for column, pattern in COLUMN_PATTERNS.items():
            if re.search(pattern, benefit, re.IGNORECASE):
                row_data[column] = "1"
                mapped = True
        if not mapped:
            unmapped_benefits.append(benefit)

    for new_category in unmapped_benefits:
        formatted_category = f"Uncategorized - {new_category[:30]}"
        CSVHandler.add_missing_category(formatted_category)
        valid_columns.add(formatted_category)
        row_data[formatted_category] = "1"

    return row_data
