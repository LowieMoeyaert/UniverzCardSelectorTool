import csv
import re
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

def parse_eligibility_requirements(requirements_text):
    """Parses the eligibility requirements text and splits it into categories."""
    primary_fee = "N/A"
    supplementary_fee = "N/A"
    free_for_life = False

    if "free for life" in requirements_text.lower():
        free_for_life = True
    else:
        primary_match = re.search(r"Primary(?: Card)?: AED ([\d,]+(?:\.\d+)?(?: \+\d+% VAT)?)", requirements_text, re.IGNORECASE)
        supplementary_match = re.search(r"Supplementary(?: Card)?: AED ([\d,]+(?:\.\d+)?(?: \+\d+% VAT)?)", requirements_text, re.IGNORECASE)

        if primary_match:
            primary_fee = primary_match.group(1).replace(",", "").strip()
        if supplementary_match:
            supplementary_fee = supplementary_match.group(1).replace(",", "").strip()

    return {
        "Primary_Annual_Fee": primary_fee,
        "Supplementary_Annual_Fee": supplementary_fee,
        "Free_For_Life": free_for_life
    }

def extract_requirements(card_url, driver):
    """Extracts eligibility requirements, handling multiple formats."""
    print(f"🟡 Checking: {card_url}")

    driver.get(card_url)
    time.sleep(3)

    eligibility_text = "N/A"
    min_salary = "N/A"
    min_age = "N/A"
    min_credit_limit = "N/A"
    annual_fee = "N/A"

    try:
        # Step 1: Try extracting from accordion
        accordion_items = driver.find_elements(By.CLASS_NAME, "accordion-item")
        for item in accordion_items:
            try:
                title_element = item.find_element(By.CLASS_NAME, "js-acc-title")
                if "eligibility" in title_element.text.strip().lower():
                    print("🔄 Expanding 'Eligibility' section...")

                    parent_element = title_element.find_element(By.XPATH, "./..")
                    is_expanded = parent_element.get_attribute("data-state") == "expanded"
                    if not is_expanded:
                        driver.execute_script("arguments[0].click();", title_element)
                        time.sleep(2)

                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "accordion-item__content"))
                    )
                    content_element = item.find_element(By.CLASS_NAME, "c-cms-content")
                    eligibility_text = content_element.text.strip()

                    # Extract details separately
                    min_salary = extract_min_salary(eligibility_text)
                    min_age = extract_min_age(eligibility_text)
                    min_credit_limit = extract_credit_limit(eligibility_text)

                    parsed_requirements = parse_eligibility_requirements(eligibility_text)
                    print(f"✅ Extracted Eligibility: {eligibility_text}")
                    return {
                        "Eligibility_Requirements": eligibility_text,
                        "Minimum_Income": min_salary,
                        "Minimum_Age": min_age,
                        "Minimum_Credit_Limit": min_credit_limit,
                        **parsed_requirements
                    }

            except Exception as e:
                print(f"⚠️ Error processing accordion item")
                continue

        # Step 2: Check static content (MarketingAccordion)
        print("🔍 Checking for static 'Eligibility' section...")
        try:
            marketing_section = driver.find_element(By.ID, "MarketingAccordion")
            content_element = marketing_section.find_element(By.CLASS_NAME, "c-cms-content")
            eligibility_text = content_element.text.strip()

            min_salary = extract_min_salary(eligibility_text)
            min_age = extract_min_age(eligibility_text)
            min_credit_limit = extract_credit_limit(eligibility_text)

            if "eligibility" in eligibility_text.lower():
                parsed_requirements = parse_eligibility_requirements(eligibility_text)
                print(f"✅ Extracted Static Eligibility: {eligibility_text}")
                return {
                    "Eligibility_Requirements": eligibility_text,
                    "Minimum_Income": min_salary,
                    "Minimum_Age": min_age,
                    "Minimum_Credit_Limit": min_credit_limit,
                    **parsed_requirements
                }

        except NoSuchElementException:
            print("⚠️ No static 'Eligibility' section found.")

        # Step 3: Extract eligibility from `.o-lightgray-background`
        print("🔍 Checking for alternative 'Eligibility' format...")
        try:
            feature_section = driver.find_element(By.CLASS_NAME, "o-lightgray-background")
            content_items = feature_section.find_elements(By.CLASS_NAME, "c-feature__content-item")

            eligibility_texts = []
            for item in content_items:
                eligibility_texts.append(item.text.strip())

            eligibility_text = "\n".join(eligibility_texts)

            min_salary = extract_min_salary(eligibility_text)
            min_age = extract_min_age(eligibility_text)
            min_credit_limit = extract_credit_limit(eligibility_text)

            if eligibility_text:
                parsed_requirements = parse_eligibility_requirements(eligibility_text)
                print(f"✅ Extracted Alternative Eligibility: {eligibility_text}")
                return {
                    "Eligibility_Requirements": eligibility_text,
                    "Minimum_Income": min_salary,
                    "Minimum_Age": min_age,
                    "Minimum_Credit_Limit": min_credit_limit,
                    **parsed_requirements
                }

        except NoSuchElementException as e:
            print(f"⚠️ No alternative 'Eligibility' section found")

        # Step 4: Extract eligibility from `FeesAndChargesCard_container__2HPb_`
        print("🔍 Checking for 'FeesAndChargesCard' section...")
        try:
            fees_section = driver.find_element(By.CLASS_NAME, "FeesAndChargesCard_container__2HPb_")
            eligibility_text = fees_section.text.strip()

            min_salary = extract_min_salary(eligibility_text)
            min_age = extract_min_age(eligibility_text)
            min_credit_limit = extract_credit_limit(eligibility_text)

            if eligibility_text:
                parsed_requirements = parse_eligibility_requirements(eligibility_text)
                print(f"✅ Extracted Fees and Charges Eligibility: {eligibility_text}")
                return {
                    "Eligibility_Requirements": eligibility_text,
                    "Minimum_Income": min_salary,
                    "Minimum_Age": min_age,
                    "Minimum_Credit_Limit": min_credit_limit,
                    **parsed_requirements
                }

        except NoSuchElementException as e:
            print(f"⚠️ No 'FeesAndChargesCard' section found")

        print(f"⚠️ No 'Eligibility' section found on {card_url}")
        return {
            "Eligibility_Requirements": "N/A",
            "Minimum_Income": "N/A",
            "Minimum_Age": "N/A",
            "Minimum_Credit_Limit": "N/A",
            "Primary_Annual_Fee": "N/A",
            "Supplementary_Annual_Fee": "N/A",
            "Free_For_Life": False
        }

    except Exception as e:
        print(f"⚠️ Error extracting requirements")
        return {
            "Eligibility_Requirements": "N/A",
            "Minimum_Income": "N/A",
            "Minimum_Age": "N/A",
            "Minimum_Credit_Limit": "N/A",
            "Primary_Annual_Fee": "N/A",
            "Supplementary_Annual_Fee": "N/A",
            "Free_For_Life": False
        }

def extract_min_salary(text):
    """Extracts the minimum salary requirement from eligibility text."""
    match = re.search(r"minimum salary of AED\s?([\d,]+)", text, re.IGNORECASE)
    return match.group(1).replace(",", "").strip() if match else "N/A"

def extract_min_age(text):
    """Extracts the minimum age requirement from eligibility text."""
    match = re.search(r"minimum age of (\d+)", text, re.IGNORECASE)
    return match.group(1).strip() if match else "N/A"

def extract_credit_limit(text):
    """Extracts the minimum credit limit requirement from eligibility text."""
    match = re.search(r"credit limit of at least AED\s?([\d,]+)", text, re.IGNORECASE)
    return match.group(1).replace(",", "").strip() if match else "N/A"