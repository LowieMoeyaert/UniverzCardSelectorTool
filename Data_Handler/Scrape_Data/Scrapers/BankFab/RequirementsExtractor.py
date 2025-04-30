import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from Data_Handler.Scrape_Data.Scrapers.BankFab.CreditCardScraper import CreditCardScraper


def extract_requirements(card_url, driver):
    """Extracts credit card requirements from FAB pages, handling overview pages dynamically."""

    print(f"🟡 Checking: {card_url}")

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
            EC.presence_of_element_located((By.CLASS_NAME, "infographic-number"))
        )

        sections = driver.find_elements(By.CLASS_NAME, "infographic-item")

        for i, section in enumerate(sections):
            try:
                value_element = section.find_element(By.CLASS_NAME, "infographic-heading")
                label_element = section.find_element(By.CLASS_NAME, "infographic-text")

                value = value_element.text.strip()
                label = label_element.text.strip().lower()

                print(f"🔍 Found label: {label} -> Value: {value}")

                # Alternatieve namen voor minimum inkomen
                if "minimum salary" in label or "monthly salary" in label or "income" in label:
                    requirements["Minimum_Income"] = value.replace("AED", "").replace(",", "").strip()
                elif "annual fee" in label:
                    requirements["Annual_Fee"] = value.replace("AED", "").replace(",", "").strip()
                elif "interest rate" in label or "apr" in label:
                    requirements["Interest_Rate_APR"] = value.replace("%", "").strip()
                elif "joining fee" in label:
                    requirements["Joining_Fee"] = value.replace("AED", "").replace(",", "").strip()

            except Exception as e:
                print(f"⚠️ Error processing section {i}: {e}")
                continue

    except Exception as e:
        print(f"⚠️ Error extracting details: {e}")
        return requirements

    print(f"✅ Extracted requirements: {requirements}")
    return requirements

