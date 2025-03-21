import time
import re
from typing import TextIO

import unicodedata
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from Scrapers.BankFab.CSVHandler import CSVHandler


def normalize_text(text):
    """Verwijdert onzichtbare tekens en normaliseert Unicode."""
    return unicodedata.normalize("NFKC", text).replace("\xa0", " ").strip()


def scrape_benefit_titles(card_url, driver, max_retries=3):
    """Extracts benefits for a credit card from its FAB website page."""

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
                        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                        time.sleep(3)
                    else:
                        print("⚠️ No valid links found on the overview page.")
                        return []
                except Exception as e:
                    print(f"❌ Error clicking on card link: {str(e)}")
                    return []

            benefit_elements_front = driver.find_elements(By.CLASS_NAME, "lwiat-item-desc")
            benefit_elements_back = driver.find_elements(By.CLASS_NAME, "bpl-item-content-title")

            benefits = [normalize_text(elem.text) for elem in benefit_elements_front + benefit_elements_back if elem.text.strip()]

            if benefits:
                print(f"✅ Successfully extracted {len(benefits)} benefits for {card_url}")
                for idx, benefit in enumerate(benefits, start=1):
                    print(f"  {idx}. {benefit}")

                # ✅ Log alle benefits naar een bestand
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
    """Checkt of de pagina een overzichtspagina is met meerdere kaarten."""
    try:
        return bool(driver.find_elements(By.CLASS_NAME, "cards-list-grid-card"))
    except Exception:
        return False

def map_benefits_to_csv(benefits):
    """Match benefits to CSV columns using regex patterns and provide debug output."""
    COLUMN_PATTERNS = {
        "Cashback": re.compile(r"\b(cashback|rebate|reward points|money back|discount)\b", re.IGNORECASE),
        "Cashback Grocery": re.compile(r"\b(grocery|supermarket|Carrefour|food shopping)\b", re.IGNORECASE),
        "Cashback Fuel": re.compile(r"\b(fuel|gas station|petrol|diesel)\b", re.IGNORECASE),
        "Cashback Dining": re.compile(r"\b(dining|restaurant|Talabat|Costa|cafe|coffee shop)\b", re.IGNORECASE),
        "Cashback Travel": re.compile(r"\b(travel|international spend|flight ticket|hotel booking|trip discount)\b",
                                      re.IGNORECASE),
        "Discount Fashion": re.compile(r"\b(fashion|Farfetch|Bicester|clothing|apparel|outfits)\b", re.IGNORECASE),
        "Discount Shopping": re.compile(r"\b(shop|Carrefour|retail|6thStreet|Namshi|Ounass)\b", re.IGNORECASE),
        "Discount Flights": re.compile(r"\b(flight|airline|Etihad Guest Miles|airfare|plane ticket)\b", re.IGNORECASE),
        "Discount Hotels": re.compile(r"\b(hotel|stay|Visa Luxury Hotel Collection|VLHC|Halalbooking|lodging)\b",
                                      re.IGNORECASE),
        "Free Airport Transfers": re.compile(r"\b(free airport transfers|Careem|Uber airport)\b", re.IGNORECASE),
        "Fast Track Airport": re.compile(r"\b(fast track|expedited airport service|priority check-in)\b",
                                         re.IGNORECASE),
        "Free WiFi Flight": re.compile(r"\b(free inflight Wi-Fi|airplane internet|flight internet)\b", re.IGNORECASE),
        "Lounge Access": re.compile(r"\b(lounge|airport lounge|VIP lounge)\b", re.IGNORECASE),
        "Meet & Greet": re.compile(r"\b(meet and greet|airport welcome)\b", re.IGNORECASE),
        "VIP Service": re.compile(r"\b(VIP services|luxury concierge)\b", re.IGNORECASE),
        "Cinema Discount": re.compile(r"\b(cinema|movie ticket|VOX)\b", re.IGNORECASE),
        "Golf Discount": re.compile(r"\b(golf|golf course)\b", re.IGNORECASE),
        "Theme Park Discount": re.compile(r"\b(attractions|Emaar|IMG Worlds)\b", re.IGNORECASE),
        "Travel Insurance": re.compile(r"\b(travel insurance|medical assistance)\b", re.IGNORECASE),
        "Credit Shield": re.compile(r"\b(credit shield|debt protection)\b", re.IGNORECASE),
        "Fraud Protection": re.compile(r"\b(fraudulent transaction protection|anti-fraud|fraud misuse protection)\b",
                                       re.IGNORECASE),
        "Purchase Protection": re.compile(r"\b(purchase protection|extended warranty)\b", re.IGNORECASE),
        "Collision Damage Waiver": re.compile(r"\b(rental collision|car rental insurance)\b", re.IGNORECASE),
        "Bonus Miles": re.compile(r"\b(miles bonus|Etihad Guest Miles)\b", re.IGNORECASE),
        "FAB Rewards": re.compile(r"\b(FAB Rewards|extra points)\b", re.IGNORECASE),
        "Visa Offers": re.compile(r"\b(Visa Luxury Hotel Collection|Visa promotions)\b", re.IGNORECASE),
        "Islamic Benefits": re.compile(r"\b(Halal|Islamic banking|Shariah-compliant)\b", re.IGNORECASE),
        "Easy Payment Plans": re.compile(r"\b(installment|buy now pay later|BNPL|0% payment plan|Buy Now, Pay Later)\b",
                                         re.IGNORECASE),
        "Balance Transfer": re.compile(r"\b(balance transfer|0% interest)\b", re.IGNORECASE),
        "Tier Miles": re.compile(r"\b(Tier Miles|upgrade fast track)\b", re.IGNORECASE),
        "Global Blue VIP": re.compile(r"\b(Global Blue VIP|international Global Blue VIP services)\b", re.IGNORECASE),
        "Exclusive Dining": re.compile(
            r"\b(five-star restaurants|premium dining|20% off dining|restaurant discounts)\b", re.IGNORECASE),
        "Movie Tickets": re.compile(r"\b(movie tickets)\b", re.IGNORECASE),
        "Education Protection": re.compile(r"\b(Education protection|school fees discount)\b", re.IGNORECASE),
        "Fast Track Membership": re.compile(
            r"\b(fast track to Etihad Guest Silver|fast track to Etihad Guest Gold|VIP upgrade)\b", re.IGNORECASE),
        "Miles Accelerator": re.compile(r"\b(Miles Accelerator|optional miles accelerator)\b", re.IGNORECASE),
        "School Fees Discount": re.compile(r"\b(school fees|GEMS school discount|4.25% on school fees)\b",
                                           re.IGNORECASE),
        "Concierge Service": re.compile(r"\b(24/7 concierge|global concierge|VIP concierge service)\b", re.IGNORECASE),
        "Gold Gift": re.compile(r"\b(gold gift|gold rewards|gold membership)\b", re.IGNORECASE),
        "Unlimited SHARE Points": re.compile(r"\b(unlimited SHARE points|no limit on SHARE points)\b", re.IGNORECASE),
        "Supplementary Cards": re.compile(r"\b(free supplementary cards|extra cards for family)\b", re.IGNORECASE),
        "Online Travel Discount": re.compile(r"\b(MakeMyTrip|Cleartrip|travel discount|flight booking discount)\b",
                                             re.IGNORECASE),
        "Loyalty Miles Boost": re.compile(r"\b(double your miles|extra miles|bonus miles boost|miles accelerator)\b",
                                          re.IGNORECASE),
        "Valet Parking": re.compile(r"\b(valet parking|free valet|parking service)\b", re.IGNORECASE),
        "Global Car Rental Discount": re.compile(r"\b(Avis|Hertz|rental car discount|car rental deal)\b",
                                                 re.IGNORECASE),
        "Religious Travel Benefits": re.compile(r"\b(Umrah|Hajj package|Islamic pilgrimage)\b", re.IGNORECASE),
        "Luxury Lifestyle Perks": re.compile(r"\b(VIP services|luxury shopping|high-end rewards|exclusive lifestyle)\b",
                                             re.IGNORECASE),
        "Shopping Points": re.compile(r"\b(SHARE points|shopping rewards|loyalty points)\b", re.IGNORECASE),
        "Special Visa Offers": re.compile(
            r"\b(Visa offer|Visa benefit|Visa partnership discount|Special Visa offers)\b", re.IGNORECASE),
        "No Foreign Transaction Fees": re.compile(
            r"\b(zero foreign transaction fee|no forex markup|no international fee)\b", re.IGNORECASE),
        "10% off on du Easy Payment Plans": re.compile(
            r"\b(10% off du Easy Payment Plans|du Easy Payment Plan discount | 10% off on du Easy Payment Plans)\b",
            re.IGNORECASE),
        "Get instant Reward redemption": re.compile(r"\b(instant reward redemption|redeem rewards instantly)\b",
                                                    re.IGNORECASE),
        "Save more with exciting Mastercard offers": re.compile(r"\b(Mastercard offers|exciting Mastercard deals)\b",
                                                                re.IGNORECASE),
        "Easier access anytime, anywhere with FAB Mobile": re.compile(
            r"\b(FAB Mobile access|manage card with FAB Mobile)\b", re.IGNORECASE),
        "Save money with low interest rates on card features and benefits": re.compile(
            r"\b(low interest rates|affordable card benefits)\b", re.IGNORECASE),
        "The most affordable card in your wallet": re.compile(r"\b(affordable card|low-cost credit card)\b",
                                                              re.IGNORECASE),
        "Convenient buy now, pay later plans": re.compile(r"\b(buy now pay later|BNPL plans|0% installment plans)\b",
                                                          re.IGNORECASE),
        "Low interest rates per month for UAE nationals and expatriates": re.compile(
            r"\b(low monthly interest rates|low rates for UAE residents)\b", re.IGNORECASE),
        "3% minimum statement payment": re.compile(
            r"\b(3% minimum payment|minimum due amount|3% minimum statement payment)\b", re.IGNORECASE),
        "Zero foreign transaction bank fees": re.compile(
            r"\b(zero foreign transaction fees|no forex markup|Zero foreign transaction bank fees)\b", re.IGNORECASE),
        "Quick Cash": re.compile(r"\b(Quick Cash|cash advance|instant cash)\b", re.IGNORECASE),
        "Easy card management with FAB Mobile": re.compile(
            r"\b(manage card with FAB Mobile|FAB Mobile banking|Easy card management with FAB Mobile)\b",
            re.IGNORECASE),
        "SMS alerts": re.compile(r"\b(SMS alerts|transaction notifications)\b", re.IGNORECASE),
        "Set instructions for payments": re.compile(
            r"\b(payment instructions|automatic payment setup|Set instructions for payments)\b", re.IGNORECASE),
        "Wallet Shield": re.compile(r"\b(Wallet Shield|card protection)\b", re.IGNORECASE),
        "Outstanding balance coverage": re.compile(r"\b(balance coverage|debt protection)\b", re.IGNORECASE),
        "Win exciting trips to Etihad Stadium in the UK": re.compile(
            r"\b(Etihad Stadium trip|Manchester City experience)\b", re.IGNORECASE),
        "Win official Man City jerseys": re.compile(r"\b(Man City jersey|Manchester City merchandise)\b",
                                                    re.IGNORECASE),
        "Enjoy special discounts": re.compile(r"\b(special discounts|exclusive savings)\b", re.IGNORECASE),
        "Buy 1 get 1 offers with Mastercard": re.compile(r"\b(Buy 1 Get 1|BOGO Mastercard offers)\b", re.IGNORECASE),
        "Instant redemption on Rewards": re.compile(
            r"\b(instant reward redemption|redeem FAB Rewards instantly|Instant redemption on Rewards)\b",
            re.IGNORECASE),
        "First year free with a new card": re.compile(r"\b(first year free|no annual fee first year)\b", re.IGNORECASE),
        "Free access to 60+ beach clubs, gyms and sports clubs with ADV+": re.compile(
            r"\b(free ADV+ access|beach clubs|gyms|sports clubs)\b", re.IGNORECASE),
        "Get dedicated lifestyle concierge support 24/7": re.compile(r"\b(lifestyle concierge|24/7 VIP support)\b",
                                                                     re.IGNORECASE),
        "Dine at over 150 restaurants in the UAE with up to 20% off": re.compile(
            r"\b(20% dining discount|150+ restaurants in UAE)\b", re.IGNORECASE),
        "Dine with up to 20% off at over 150 restaurants in the UAE": re.compile(
            r"\b(20% off dining|UAE restaurant discounts)\b", re.IGNORECASE),
        "Earn 1 FAB Reward on all other spending including abroad": re.compile(
            r"\b(1 FAB Reward per spend|FAB Rewards abroad)\b", re.IGNORECASE),
        "Receive 10% off car and truck rentals": re.compile(r"\b(10% off car rental|truck rental discount)\b",
                                                            re.IGNORECASE),
        "Exclusive SHARE member benefits": re.compile(r"\b(SHARE member benefits|SHARE loyalty perks)\b",
                                                      re.IGNORECASE),
        "SHARE with others": re.compile(r"\b(share rewards|SHARE points transfer)\b", re.IGNORECASE),
        "Buy now, pay later plans": re.compile(r"\b(Buy Now Pay Later|BNPL plans|installment payment)\b",
                                               re.IGNORECASE),
        "Great rates on balance transfers": re.compile(r"\b(balance transfer deals|low-interest balance transfer)\b",
                                                       re.IGNORECASE),
        "Up to 3% extra value in BLUE": re.compile(r"\b(3% extra in BLUE|BLUE rewards bonus)\b", re.IGNORECASE),
        "Affordable airport transfers": re.compile(r"\b(discounted airport transfers|cheap airport rides)\b",
                                                   re.IGNORECASE),
        "Easy payment plans": re.compile(r"\b(easy payment plan|0% installment plan)\b", re.IGNORECASE),
        "Get fast tracked to Etihad Guest Gold status": re.compile(
            r"\b(fast track Etihad Guest Gold|Etihad Gold upgrade)\b", re.IGNORECASE),
        "Discounted airport transfers": re.compile(r"\b(airport transfer discount|cheap airport taxi)\b",
                                                   re.IGNORECASE),
        "Special Visa offers": re.compile(r"\b(Visa special offers|Visa exclusive discounts)\b", re.IGNORECASE),
        "Free access to over 1,000 airport lounges worldwide": re.compile(
            r"\b(airport lounge access|1000+ free lounges)\b", re.IGNORECASE),
        "Get fast tracked to Etihad Guest Silver status": re.compile(
            r"\b(fast track Etihad Guest Silver|Etihad Silver upgrade)\b", re.IGNORECASE),
        "Exciting Visa offers": re.compile(r"\b(exclusive Visa deals|Visa card promotions)\b", re.IGNORECASE),
        "No international transaction fees": re.compile(r"\b(zero forex fees|no international fees)\b", re.IGNORECASE),
        "Earn and redeem FAB Miles": re.compile(r"\b(earn FAB Miles|redeem FAB Miles)\b", re.IGNORECASE),
        "Transfer miles between partners": re.compile(r"\b(transfer miles|loyalty miles exchange)\b", re.IGNORECASE),
        "International airport transfers with UBER": re.compile(
            r"\b(UBER airport rides|discounted UBER airport trips)\b", re.IGNORECASE),
        "Earn more FAB Miles": re.compile(r"\b(double FAB Miles|bonus FAB Miles)\b", re.IGNORECASE),
        "Excellent Mastercard benefits": re.compile(r"\b(Mastercard perks|exclusive Mastercard offers)\b",
                                                    re.IGNORECASE),
        "Free access to gyms and padel courts across the UAE": re.compile(r"\b(free gym access|padel courts UAE)\b",
                                                                          re.IGNORECASE),
        "Free access to gyms and padel courts": re.compile(r"\b(free gym & padel court entry|UAE fitness access)\b",
                                                           re.IGNORECASE),
        "Get 15 FAB Islamic Rewards at beauty and fragrance store shopping": re.compile(
            r"\b(15 FAB Islamic Rewards|beauty store rewards)\b", re.IGNORECASE),
        "Get 10 FAB Islamic Rewards on international spending": re.compile(
            r"\b(10 FAB Islamic Rewards|Islamic Rewards on travel)\b", re.IGNORECASE),
        "Get 5 FAB Islamic Rewards on all your other spending": re.compile(r"\b(5 FAB Islamic Rewards|Islamic Rewards "
                                                                           r"general spending)\b", re.IGNORECASE),
        "Fraudulent Card Misuse Protection": re.compile(r"\b(fraud protection|card misuse security)\b", re.IGNORECASE),
        "Mobile App Management": re.compile(r"\b(FAB Mobile access|Easier access anytime|mobile banking)\b",
                                            re.IGNORECASE),
        "International Transaction Fee Waiver": re.compile(r"\b(zero foreign transaction fee|no forex markup|no "
                                                           r"international fee)\b", re.IGNORECASE),
        "Discounted Airport Transfers": re.compile(r"\b(discounted airport transfers|cheap airport taxi|Affordable "
                                                   r"airport transfers)\b", re.IGNORECASE),
        "Special Mastercard Benefits": re.compile(r"\b(Mastercard perks|Mastercard discounts|exclusive Mastercard "
                                                  r"offers)\b", re.IGNORECASE),
        "Visa offers": re.compile(r"\b(Visa special offers|Visa exclusive discounts)\b", re.IGNORECASE),
    }

    COLUMN_PATTERNS.update({
        "Fast Track Etihad Gold": re.compile(r"\b(fast track to Etihad Guest Gold|Etihad Gold upgrade)\b",
                                             re.IGNORECASE),
        "Fast Track Etihad Silver": re.compile(r"\b(fast track to Etihad Guest Silver|Etihad Silver upgrade)\b",
                                               re.IGNORECASE),
        "Etihad Guest Miles Bonus": re.compile(r"\b(Etihad Guest Miles bonus|Earn Etihad Miles)\b", re.IGNORECASE),
        "Discounted Balance Transfer": re.compile(
            r"\b(balance transfer deal|low-interest balance transfer|Move your existing credit card balance)\b",
            re.IGNORECASE),
        "Instant Reward Redemption": re.compile(r"\b(instant reward redemption|redeem rewards instantly)\b",
                                                re.IGNORECASE),
        "Zero Foreign Transaction Fees": re.compile(
            r"\b(zero foreign transaction fees|no forex markup|no international fee)\b", re.IGNORECASE),
        "International Airport Transfers": re.compile(
            r"\b(international airport transfers|UBER airport rides|discounted UBER airport trips)\b", re.IGNORECASE),
        "Cinema Offers": re.compile(r"\b(cinema tickets|head to the cinema|discounted movie tickets)\b", re.IGNORECASE),
        "Dine at 150+ Restaurants": re.compile(r"\b(Dine at over 150 restaurants|20% off at 150 restaurants)\b",
                                               re.IGNORECASE),
        "Car and Truck Rentals Discount": re.compile(r"\b(10% off car rental|truck rental discount)\b", re.IGNORECASE),
        "Lifestyle Concierge": re.compile(r"\b(dedicated lifestyle concierge|concierge support 24/7)\b", re.IGNORECASE),
        "Global Blue VIP": re.compile(r"\b(Global Blue VIP|international shopping perks)\b", re.IGNORECASE),
        "Mastercard Exclusive Offers": re.compile(r"\b(Mastercard exclusive offers|special Mastercard deals)\b",
                                                  re.IGNORECASE),
        "Man City Experiences": re.compile(r"\b(Win exciting trips to Etihad Stadium|official Man City jerseys)\b",
                                           re.IGNORECASE),
        "FAB Islamic Rewards": re.compile(r"\b(FAB Islamic Rewards|Islamic cashback rewards)\b", re.IGNORECASE),
        "Hassle-Free Visa Fulfillment": re.compile(r"\b(travel visa fulfillment|hassle-free visa processing)\b",
                                                   re.IGNORECASE),
    })
    COLUMN_PATTERNS["10% off on du Easy Payment Plans"] = re.compile(
        r"10%\s*off\s*(on\s*)?du\s*Easy\s*Payment\s*Plans", re.IGNORECASE
    )
    """Match benefits met CSV-kolommen en voeg automatisch nieuwe categorieën toe als nodig."""
    row_data = {col: "0" for col in COLUMN_PATTERNS.keys()}  # Initieel alles op 0
    unmapped_benefits = []  # Opslaan van niet-gematchte voordelen

    for benefit in benefits:
        mapped = False
        for column, pattern in COLUMN_PATTERNS.items():
            if pattern.search(benefit):  # ✅ Controleer op match
                row_data[column] = "1"
                mapped = True
        if not mapped:
            unmapped_benefits.append(benefit)  # Onbekende voordelen opslaan

    # ✅ Voeg ontbrekende categorieën toe aan de CSV als ze niet bestaan
    for new_category in unmapped_benefits:
        formatted_category = f"Uncategorized - {new_category[:30]}"  # Max 30 tekens om te vermijden dat het te lang wordt
        CSVHandler.add_missing_category(formatted_category)
        row_data[formatted_category] = "1"  # Markeer deze categorie als aanwezig voor deze kaart

    return row_data
