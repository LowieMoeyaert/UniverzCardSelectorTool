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

            # ✅ Extract benefits from `KPIs_container__2M6GZ` (Main benefits section)
            kpi_items = driver.find_elements(By.CLASS_NAME, "KPIs_item__19coa")
            for item in kpi_items:
                benefits.add(normalize_text(item.text))

            # ✅ Extract benefits from `RequirementListSecondary_item__1mM-3` (Welcome bonus section)
            welcome_bonus_items = driver.find_elements(By.CLASS_NAME, "RequirementListSecondary_item__1mM-3")
            for item in welcome_bonus_items:
                benefits.add(normalize_text(item.text))

            # ✅ Extract benefits from `FeatureCard_content__cDd5P` (Feature card section)
            feature_card_items = driver.find_elements(By.CLASS_NAME, "FeatureCard_content__cDd5P")
            for item in feature_card_items:
                benefits.add(normalize_text(item.text))

            # ✅ Extract benefits from new section `Section_container__1p9AA`
            new_section_benefits = driver.find_elements(By.CSS_SELECTOR,
                                                        ".Section_container__1p9AA .ImageCard_content__2MXP4")
            for item in new_section_benefits:
                benefits.add(normalize_text(item.text))

            # ✅ Extract benefits from new section `Section_container__1p9AA FeatureCard_container__g4ILO`
            feature_card_benefits = driver.find_elements(By.CSS_SELECTOR,
                                                         ".Section_container__1p9AA.FeatureCard_container__g4ILO .FeatureCard_content__cDd5P")
            for item in feature_card_benefits:
                benefits.add(normalize_text(item.text))

            # ✅ Extract benefits from new section `Section_container__1p9AA FeatureCard_container__g4ILO FeatureCard_large__2yTaO`
            large_feature_card_benefits = driver.find_elements(By.CSS_SELECTOR,
                                                               ".Section_container__1p9AA.FeatureCard_container__g4ILO.FeatureCard_large__2yTaO .FeatureCard_content__cDd5P")
            for item in large_feature_card_benefits:
                benefits.add(normalize_text(item.text))

            # ✅ Extract benefits from new section `Section_container__1p9AA FeatureCard_container__g4ILO FeatureCard_small__M3wwU`
            small_feature_card_benefits = driver.find_elements(By.CSS_SELECTOR,
                                                               ".Section_container__1p9AA.FeatureCard_container__g4ILO.FeatureCard_small__M3wwU .FeatureCard_content__cDd5P")
            for item in small_feature_card_benefits:
                benefits.add(normalize_text(item.text))

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
                    accordion.click()
                    time.sleep(1)
                    expanded_benefits = accordion.find_elements(By.CLASS_NAME, "accordion__expanded__content")
                    for benefit in expanded_benefits:
                        benefits.add(normalize_text(benefit.text.strip()))
                except Exception:
                    continue

            print(f"✅ Scraped {len(benefits)} unique benefits for {card_url}")
            return list(benefits)

        except Exception as e:
            print(f"❌ Error scraping benefits for {card_url}: {e}")
            time.sleep(3)

    print(f"❌ Failed to scrape benefits for {card_url} after {max_retries} attempts.")
    return []

def map_benefits_to_csv(benefits, valid_columns=None):
    """Match benefits to CSV columns using regex patterns and provide debug output."""
    COLUMN_PATTERNS = {
        "Annual Fee": r"\b(annual fee|yearly fee)\b",
        "Interest Rate": r"\b(interest rate|apr)\b",
        "Cashback": r"\b(cashback|cash back)\b",
        "Rewards": r"\b(rewards|points|miles)\b",
        "Sign-up Bonus": r"\b(sign[- ]?up bonus|welcome bonus)\b",
        "Foreign Transaction Fee": r"\b(foreign transaction fee|international fee)\b",
        # Add more patterns as needed
    }

    mapped_benefits = {column: [] for column in COLUMN_PATTERNS.keys()}

    for benefit in benefits:
        matched = False
        for column, pattern in COLUMN_PATTERNS.items():
            if re.search(pattern, benefit, re.IGNORECASE):
                mapped_benefits[column].append(benefit)
                matched = True
                break
        if not matched:
            print(f"⚠️ Unmatched benefit: {benefit}")

    if valid_columns:
        mapped_benefits = {col: mapped_benefits[col] for col in valid_columns if col in mapped_benefits}

    return mapped_benefits
