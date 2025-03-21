import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from selenium.webdriver.support import expected_conditions as EC


def extract_requirements(card_url, driver):
    """Extracts card requirements like Minimum Salary, Interest Rate, Annual Fee, and Joining Fee."""
    driver.get(card_url)
    time.sleep(3)

    requirements = {
        "Minimum_Income": "N/A",
        "Interest_Rate_APR": "N/A",
        "Annual_Fee": "N/A",
        "Joining_Fee": "N/A"
    }

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "rates"))
        )
        sections = driver.find_elements(By.CLASS_NAME, "rates")

        for section in sections:
            requirement_cards = section.find_elements(By.CLASS_NAME, "rates__box-desc")

            for req in requirement_cards:
                text = req.text.lower()

                # Extract Minimum Salary
                if "minimum salary" in text:
                    match = re.search(r"minimum salary:\s*aed\s*([\d,]+)", text)
                    if match:
                        requirements["Minimum_Income"] = match.group(1).replace(",", "")

                # Extract Interest Rate
                elif "interest rate" in text:
                    match = re.search(r"interest rate:\s*([\d.]+)%", text)
                    if match:
                        requirements["Interest_Rate_APR"] = match.group(1)

                # Extract Annual Fee
                elif "annual fee" in text:
                    match = re.search(r"annual fees?:\s*aed\s*([\d,]+)", text)
                    if match:
                        requirements["Annual_Fee"] = match.group(1).replace(",", "")

                # Extract Joining Fee
                elif "joining fee" in text:
                    match = re.search(r"joining fee:\s*aed\s*([\d,]+)", text)
                    if match:
                        requirements["Joining_Fee"] = match.group(1).replace(",", "")

    except Exception as e:
        print(f"⚠️ Error extracting requirements: {e}")

    return requirements
