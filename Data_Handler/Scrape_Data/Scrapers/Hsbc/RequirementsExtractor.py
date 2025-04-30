import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def extract_requirements(card_url, driver):
    """Extracts benefits, offers, and card features from the updated HTML structure."""
    print(f"🟡 Checking: {card_url}")

    driver.get(card_url)
    time.sleep(3)

    benefits = "N/A"
    offers = "N/A"
    card_features = "N/A"

    try:
        # ✅ Stap 1: Probeer de voordelen te scrapen
        benefits = extract_benefits(driver)

        # ✅ Stap 2: Probeer de aanbiedingen te scrapen
        offers = extract_offers(driver)

        # ✅ Stap 3: Probeer de kaartkenmerken te scrapen
        card_features = extract_card_features(driver)

        return {
            "Benefits": benefits,
            "Offers": offers,
            "Card_Features": card_features,
        }

    except Exception as e:
        print(f"⚠️ Error extracting details: {e}")
        return {
            "Benefits": "N/A",
            "Offers": "N/A",
            "Card_Features": "N/A",
        }

def extract_benefits(driver):
    """Extracts benefits from the 'content benefits' section."""
    try:
        benefits_section = driver.find_elements(By.CLASS_NAME, "productComparatorUnitList")

        benefits_texts = []
        for section in benefits_section:
            list_items = section.find_elements(By.TAG_NAME, "li")
            for item in list_items:
                benefits_texts.append(item.text.strip())

        benefits_text = "\n".join(filter(None, benefits_texts))

        if benefits_text:
            print(f"✅ Extracted Benefits: {benefits_text}")
            return benefits_text
        else:
            print("⚠️ No benefits found.")
            return "N/A"

    except Exception as e:
        print(f"⚠️ Unable to extract benefits: {e}")
        return "N/A"

def extract_offers(driver):
    """Extracts promotional offers from the relevant section."""
    try:
        offers_section = driver.find_element(By.ID, "pp_tools_richtext_3")
        list_items = offers_section.find_elements(By.TAG_NAME, "li")

        offers_texts = [item.text.strip() for item in list_items]
        offers_text = "\n".join(offers_texts)

        print(f"✅ Extracted Offers: {offers_text}")
        return offers_text

    except Exception as e:
        print(f"⚠️ Unable to extract offers: {e}")
        return "N/A"

def extract_card_features(driver):
    """Extracts key card features from the card section."""
    try:
        features_section = driver.find_elements(By.CLASS_NAME, "crh-master-cards__card")

        features_texts = []
        for section in features_section:
            headers = section.find_elements(By.CLASS_NAME, "crh-text")
            for header in headers:
                features_texts.append(header.text.strip())

        features_text = "\n".join(filter(None, features_texts))

        if features_text:
            print(f"✅ Extracted Card Features: {features_text}")
            return features_text
        else:
            print("⚠️ No card features found.")
            return "N/A"

    except Exception as e:
        print(f"⚠️ Unable to extract card features: {e}")
        return "N/A"
