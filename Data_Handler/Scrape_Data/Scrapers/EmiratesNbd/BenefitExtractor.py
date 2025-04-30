import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def scrape_benefit_titles(card_url, driver):
    """Scrape all benefits from a credit card detail page."""
    driver.get(card_url)
    time.sleep(3)  # Ensure page loads

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".support-card")))
        benefit_cards = driver.find_elements(By.CSS_SELECTOR, ".support-card")

        benefit_titles = []
        for card in benefit_cards:
            title_element = driver.execute_script("return arguments[0].querySelector('h4')", card)
            title = title_element.text.strip() if title_element else None
            if title:
                benefit_titles.append(title)

        print(f"🟢 Found {len(benefit_titles)} benefits for {card_url}:")
        for benefit in benefit_titles:
            print(f"   - {benefit}")

    except Exception as e:
        print(f"Error finding benefits: {e}")  # Debugging
        benefit_titles = []

    return benefit_titles

# ✅ Function to Map Benefits to CSV Columns
def map_benefits_to_csv(benefits):
    """Match benefits to CSV columns using regex patterns."""
    COLUMN_PATTERNS = {
        "Airport_Lounge_Access": r"\b(lounge access|airport lounge|visa airport companion)\b",
        "Complimentary_Airport_Transfers": r"\b(airport transfer|airport transport)\b",
        "Valet_Parking": r"\b(valet parking)\b",
        "Insurance_Benefits": r"\b(travel insurance|medical insurance|insurance benefits)\b",
        "Purchase_Protection": r"\b(purchase protection)\b",
        "Extended_Warranty": r"\b(extended warranty)\b",
        "Roadside_Assistance": r"\b(roadside assistance|24-hour assistance)\b",
        "No_Foreign_Transaction_Fee": r"\b(no foreign transaction fee)\b",
        "Credit_Shield_Pro": r"\b(credit shield pro)\b",
        "Concierge_Service": r"\b(concierge desk|digital concierge)\b",
        "Avis_Car_Rental_Discount": r"\b(avis car rental|car rental)\b",
        "Hertz_Gold_Plus_Rewards": r"\b(hertz gold plus rewards)\b",
        "Lingokids_Discount": r"\b(lingokids discount)\b",
        "MyUS_Premium_Shipping": r"\b(myus premium shipping)\b",
        "Mastercard_Experience_Offers": r"\b(mastercard discounts experiences|offers)\b",
        "Travel_Insurance_Confirmation_Letter": r"\b(travel insurance confirmation letter)\b",
        "Mastercard_Global_Emergency_Services": r"\b(mastercard global emergency services)\b",
        "Farfetch_Discount": r"\b(farfetch discount)\b",
        "Auto_Salik_Topup": r"\b(auto salik top-up)\b",
        "Instant_Cash_Withdrawal": r"\b(instant cash withdrawal)\b",
        "Interest_Free_Days": r"\b(interest-free days)\b",
        "Online_Access": r"\b(online access)\b",
        "SMS_Alerts": r"\b(sms alerts)\b",
        "Rental_Collision_Loss_Damage_Waiver": r"\b(rental collision and loss damage waiver)\b",
        "Lime_Discounted_Rides": r"\b(lime discounted rides)\b",
        "Complimentary_Food_Drink_Costa": r"\b(complimentary food and drink from costa)\b",
        "Bookingcom_Discount": r"\b(booking.com discount)\b",
    }

    # ✅ Start with "0" for all benefits
    row_data = {col: "0" for col in COLUMN_PATTERNS.keys()}

    # ✅ Only update to "1" if a benefit is found
    for benefit in benefits:
        for column, pattern in COLUMN_PATTERNS.items():
            if re.search(pattern, benefit, re.IGNORECASE):
                row_data[column] = "1"

    return row_data