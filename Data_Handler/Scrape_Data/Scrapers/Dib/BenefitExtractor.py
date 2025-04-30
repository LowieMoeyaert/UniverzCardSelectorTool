import time
import unicodedata
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from Data_Handler.Scrape_Data.Scrapers.BankFab.CSVHandler import CSVHandler

def normalize_text(text):
    return unicodedata.normalize("NFKC", text).replace("\xa0", " ").strip()


def scrape_benefit_titles(card_url, driver, max_retries=3):
    for attempt in range(max_retries):
        try:
            print(f"🟡 Attempt {attempt + 1}: Scraping benefits for {card_url}")
            driver.get(card_url)

            WebDriverWait(driver, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
            time.sleep(3)

            if is_overview_page(driver):
                print("🔄 Overview page detected. Clicking the correct card link...")
                try:
                    card_elements = driver.find_elements(By.CLASS_NAME, "cl-card-desc-link")
                    if card_elements:
                        first_card_link = card_elements[0].find_element(By.TAG_NAME, "a").get_attribute("href")
                        print(f"➡️ Navigating to {first_card_link}")
                        driver.get(first_card_link)
                        WebDriverWait(driver, 10).until(
                            lambda d: d.execute_script("return document.readyState") == "complete")
                        time.sleep(3)
                    else:
                        print("⚠️ No valid links found on the overview page.")
                        return []
                except Exception as e:
                    print(f"❌ Error clicking on card link: {str(e)}")
                    return []

            benefit_elements = driver.find_elements(By.CSS_SELECTOR,
                                                    "div.accordion-content p, div.content-expandable p")
            benefits = [normalize_text(elem.text) for elem in benefit_elements if elem.text.strip()]

            if benefits:
                print(f"✅ Successfully extracted {len(benefits)} benefits for {card_url}")
                for idx, benefit in enumerate(benefits, start=1):
                    print(f"  {idx}. {benefit}")

                with open("benefits_log.txt", "a", encoding="utf-8") as log_file:
                    for benefit in benefits:
                        log_file.write(f"{benefit}\n")

                return benefits

        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1}: Error scraping benefits ({str(e)}), retrying...")
        time.sleep(5)

    print(f"❌ Failed to scrape benefits after {max_retries} attempts.")
    return []


def is_overview_page(driver):
    try:
        return bool(driver.find_elements(By.CLASS_NAME, "cards-list-grid-card"))
    except Exception:
        return False

def map_benefits_to_csv(benefits, valid_columns):
    """Match benefits to CSV columns using regex patterns and provide debug output."""
    COLUMN_PATTERNS = {
        # Add your regex patterns here
        # Example: "no_annual_fee": re.compile(r"no annual fee", re.IGNORECASE)
    }
    row_data = {col: "0" for col in valid_columns}
    unmapped_benefits = []

    for benefit in benefits:
        mapped = False
        for column, pattern in COLUMN_PATTERNS.items():
            if pattern.search(benefit):
                row_data[column] = "1"
                mapped = True
                break
        if not mapped:
            unmapped_benefits.append(benefit)

    for new_category in unmapped_benefits:
        formatted_category = f"Uncategorized - {new_category[:30]}"
        CSVHandler.add_missing_category(formatted_category)
        valid_columns.add(formatted_category)
        row_data[formatted_category] = "1"

    return row_data
