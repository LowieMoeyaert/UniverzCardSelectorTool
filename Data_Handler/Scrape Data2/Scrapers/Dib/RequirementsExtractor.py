import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from Scrapers.Dib.CreditCardScraper import CreditCardScraper

MAX_RETRIES = 3
WAIT_TIME = 5

def extract_requirements(card_url, driver):
    if not card_url:
        print("❌ Invalid card URL.")
        return {"Minimum_Income": "N/A", "Interest_Rate_APR": "N/A", "Annual_Fee": "N/A", "Joining_Fee": "N/A"}

    print(f"🟡 Checking: {card_url}")
    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            driver.get(card_url)
            time.sleep(3)

            requirements = {
                "Minimum_Income": "N/A",
                "Interest_Rate_APR": "N/A",
                "Annual_Fee": "N/A",
                "Joining_Fee": "N/A"
            }

            scraper = CreditCardScraper(driver)

            if is_overview_page(driver):
                print(f"🔄 Overview page detected. Extracting individual card links...")
                card_links = scraper.extract_cards(scraper.fetch_page_source(card_url), is_islamic_source=False)

                all_card_details = []
                seen_links = set()

                for card in card_links:
                    detail_url = card.get("Card_Link", "")
                    if not detail_url or detail_url in seen_links:
                        continue

                    seen_links.add(detail_url)
                    driver.get(detail_url)
                    time.sleep(3)
                    details = extract_card_details(driver)

                    if details:
                        all_card_details.append(details)

                return all_card_details if all_card_details else requirements

            return extract_card_details(driver)
        except Exception as e:
            print(f"⚠️ Error: {e}. Retrying ({attempt + 1}/{MAX_RETRIES})...")
            attempt += 1
            time.sleep(WAIT_TIME)
    print("❌ Failed after maximum retries.")
    return {"Minimum_Income": "N/A", "Interest_Rate_APR": "N/A", "Annual_Fee": "N/A", "Joining_Fee": "N/A"}

def is_overview_page(driver):
    try:
        return bool(driver.find_elements(By.CLASS_NAME, "cards-list-grid-card"))
    except Exception:
        return False

def extract_card_details(driver):
    requirements = {
        "Minimum_Income": "N/A",
        "Interest_Rate_APR": "N/A",
        "Annual_Fee": "N/A",
        "Joining_Fee": "N/A"
    }

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "cc-side-details"))
        )

        try:
            minimum_income_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH,
                                                "//div[@class='cc-side-details']//li[.//div[@class='cc-title' and text()='Free for Life*']]"))
            )
            if minimum_income_element:
                requirements["Minimum_Income"] = "AED 60,000"
        except Exception as e:
            print("⚠️ Error extracting minimum income:", e)

        try:
            annual_fee_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@class='accordion-content']//p[contains(text(), 'No annual fee')]"))
            )
            if annual_fee_element:
                requirements["Annual_Fee"] = "AED 0"
        except Exception as e:
            print("⚠️ Error extracting annual fee:", e)

        try:
            joining_fee_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@class='accordion-content']//p[contains(text(), 'joining fee')]"))
            )
            if joining_fee_element:
                requirements["Joining_Fee"] = "N/A"
        except Exception as e:
            print("⚠️ Error extracting joining fee:", e)

        try:
            apr_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@class='accordion-content']//p[contains(text(), 'Interest rate')]"))
            )
            if apr_element:
                requirements["Interest_Rate_APR"] = apr_element.text.strip()
        except Exception as e:
            print("⚠️ Error extracting APR:", e)

    except Exception as e:
        print(f"⚠️ Error extracting details: {e}")
        return requirements

    print(f"✅ Extracted requirements: {requirements}")
    return requirements