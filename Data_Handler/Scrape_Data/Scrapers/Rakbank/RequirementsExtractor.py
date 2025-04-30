import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def extract_requirements(card_url, driver):
    """Extracts eligibility requirements from the updated HTML structure."""
    print(f"🟡 Checking: {card_url}")

    driver.get(card_url)
    time.sleep(3)

    eligibility_text = "N/A"
    min_salary = "N/A"
    min_age = "N/A"

    try:
        # ✅ Step 1: Locate the Eligibility tab and click it if necessary
        try:
            eligibility_tab = driver.find_element(By.XPATH, "//button[contains(text(), 'Eligibility')]")
            if "aria-selected" in eligibility_tab.get_attribute("outerHTML") and "true" not in eligibility_tab.get_attribute("aria-selected"):
                print("🔄 Clicking 'Eligibility' tab...")
                driver.execute_script("arguments[0].click();", eligibility_tab)
                time.sleep(2)
        except Exception as e:
            print(f"⚠️ Unable to locate 'Eligibility' tab: {e}")

        # ✅ Step 2: Extract eligibility details from the tab content
        try:
            eligibility_section = driver.find_element(By.CLASS_NAME, "eligibility-criteria__list")
            eligibility_items = eligibility_section.find_elements(By.TAG_NAME, "li")

            eligibility_texts = []
            for item in eligibility_items:
                eligibility_texts.append(item.text.strip())

            eligibility_text = "\n".join(eligibility_texts)

            # ✅ Extract details separately
            min_salary = extract_min_salary(eligibility_text)
            min_age = extract_min_age(eligibility_text)

            print(f"✅ Extracted Eligibility: {eligibility_text}")
            return {
                "Eligibility_Requirements": eligibility_text,
                "Minimum_Income": min_salary,
                "Minimum_Age": min_age,
            }

        except Exception as e:
            print(f"⚠️ Error extracting eligibility criteria: {e}")

        print(f"⚠️ No 'Eligibility' section found on {card_url}")
        return {
            "Eligibility_Requirements": "N/A",
            "Minimum_Income": "N/A",
            "Minimum_Age": "N/A",
        }

    except Exception as e:
        print(f"⚠️ Error extracting requirements: {e}")
        return {
            "Eligibility_Requirements": "N/A",
            "Minimum_Income": "N/A",
            "Minimum_Age": "N/A",
        }

# ✅ Helper function to extract minimum salary
def extract_min_salary(text):
    """Extracts the minimum salary requirement from eligibility text."""
    match = re.search(r"minimum monthly salary of AED\s?([\d,]+)", text, re.IGNORECASE)
    return match.group(1).replace(",", "").strip() if match else "N/A"

# ✅ Helper function to extract minimum age
def extract_min_age(text):
    """Extracts the minimum age requirement from eligibility text."""
    match = re.search(r"(\d+)\s*years", text, re.IGNORECASE)
    return match.group(1).strip() if match else "N/A"
