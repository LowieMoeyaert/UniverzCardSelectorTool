import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def extract_requirements(card_url, driver):
    """Extracts eligibility requirements and fees from the updated HTML structure."""
    print(f"🟡 Checking: {card_url}")

    driver.get(card_url)
    time.sleep(3)

    eligibility_text = "N/A"
    min_salary = "N/A"
    min_age = "N/A"
    fees_text = "N/A"

    try:
        # ✅ Stap 1: Probeer de oude 'Eligibility' sectie te scrapen
        try:
            eligibility_section = driver.find_element(By.CLASS_NAME, "eligibility-criteria__list")
            eligibility_items = eligibility_section.find_elements(By.TAG_NAME, "li")

            eligibility_texts = [item.text.strip() for item in eligibility_items]
            eligibility_text = "\n".join(eligibility_texts)

            min_salary = extract_min_salary(eligibility_text)
            min_age = extract_min_age(eligibility_text)

            print(f"✅ Extracted Eligibility: {eligibility_text}")

        except Exception:
            print("⚠️ 'Eligibility' section niet gevonden, probeer 'Who Can Apply?'")
            eligibility_text = extract_who_can_apply(driver)

        # ✅ Stap 2: Probeer de fees te scrapen
        try:
            fees_text = extract_fees(driver)
            print(f"✅ Extracted Fees: {fees_text}")
        except Exception as e:
            print(f"⚠️ Error extracting fees: {e}")

        return {
            "Eligibility_Requirements": eligibility_text,
            "Minimum_Income": min_salary,
            "Minimum_Age": min_age,
            "Fees_and_Charges": fees_text,
        }

    except Exception as e:
        print(f"⚠️ Error extracting requirements: {e}")
        return {
            "Eligibility_Requirements": "N/A",
            "Minimum_Income": "N/A",
            "Minimum_Age": "N/A",
            "Fees_and_Charges": "N/A",
        }

# ✅ Nieuwe functie om de 'Who Can Apply?' sectie te scrapen
def extract_who_can_apply(driver):
    """Extracts 'Who Can Apply?' section when the standard eligibility section is missing."""
    try:
        who_can_apply_section = driver.find_element(By.CLASS_NAME, "col-lg-6.mb-lg-0.mb-4.col-bottom-margin")
        list_items = who_can_apply_section.find_elements(By.TAG_NAME, "li")

        eligibility_texts = [item.text.strip() for item in list_items]
        eligibility_text = "\n".join(eligibility_texts)

        print(f"✅ Extracted 'Who Can Apply?': {eligibility_text}")
        return eligibility_text

    except Exception as e:
        print(f"⚠️ Unable to extract 'Who Can Apply?': {e}")
        return "N/A"

# ✅ Hulpfuncties blijven hetzelfde
def extract_min_salary(text):
    """Extracts the minimum salary requirement from eligibility text."""
    match = re.search(r"minimum monthly salary of AED\s?([\d,]+)", text, re.IGNORECASE)
    return match.group(1).replace(",", "").strip() if match else "N/A"

def extract_min_age(text):
    """Extracts the minimum age requirement from eligibility text."""
    match = re.search(r"(\d+)\s*years", text, re.IGNORECASE)
    return match.group(1).strip() if match else "N/A"

def extract_fees(driver):
    """Extracts the fees from the modal if available, otherwise from the main page."""
    try:
        fee_button = driver.find_element(By.XPATH, "//a[contains(text(), 'Click here for an updated Schedule of Charges')]")
        driver.execute_script("arguments[0].click();", fee_button)
        time.sleep(2)

        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "modal-body")))
        modal_body = driver.find_element(By.CLASS_NAME, "modal-body")
        return modal_body.text.strip()

    except Exception:
        try:
            fee_section = driver.find_element(By.XPATH, "//h3[contains(text(), 'Fees and Charges')]/following-sibling::div")
            return fee_section.text.strip()
        except Exception as e:
            print(f"⚠️ Unable to extract fees: {e}")
            return "N/A"
