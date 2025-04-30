import os
import csv

CSV_FILE = "credit_cards.csv"

# Column names for the CSV
COLUMNS = [
    # Basic card details
    "Bank_ID", "Card_Link", "Card_Image", "Card_ID", "Card_Type", "Card_Network","Islamic",

    # Costs & Fees
    "Annual_Fee", "Joining_Fee", "Interest_Rate_APR", "Foreign_Transaction_Fee",
    "Balance_Transfer_Fee", "Cash_Advance_Fee", "Grace_Period_Days", "Late_Payment_Fee",

    # Requirements
    "Min_Age", "Max_Age", "Minimum_Credit_Score", "Minimum_Income", "Credit_Limit",

    # Rewards & Points System
    "Welcome_Bonus_Points", "Max_Annual_Points",
    "Points_per_1_Hotel", "Points_per_1_International", "Points_per_1_Domestic_Shopping",
    "Points_per_1_Domestic_Groceries", "Points_per_1_Domestic_Other",
    "Express_Points_Available", "Express_Points_Fee",

    # Travel & Hotel Benefits
    "Airport_Lounge_Access", "Mastercard_Lounge_Access", "Complimentary_Airport_Transfers",
    "Hotel_Free_Nights", "Marriott_Bonvoy_Elite_Status", "Elite_Night_Credits", "Free_Night_Award",
    "Rental_Collision_Loss_Damage_Waiver", "Travel_Insurance", "Travel_Insurance_Confirmation_Letter",

    # Lifestyle & Shopping Benefits
    "Dining_Benefits", "Shopping_Benefits", "Lifestyle_Benefits", "Health_Wellness_Benefits",
    "Subscription_Discounts", "Bicester_Village_Shopping_Offers", "Farfetch_Discount",
    "Bookingcom_Discount", "MyUS_Premium_Shipping", "Lingokids_Discount", "Complimentary_Food_Drink_Costa",

    # Transportation & Car Rental
    "Valet_Parking", "Hertz_Gold_Plus_Rewards", "Avis_Car_Rental_Discount",
    "Lime_Discounted_Rides", "Auto_Salik_Topup", "Instant_Cash_Withdrawal",

    # Security & Insurance
    "Insurance_Benefits", "Credit_Shield_Pro", "Purchase_Protection", "Extended_Warranty",
    "Roadside_Assistance", "24_Hour_Assistance", "DoubleSecure_Protection",
    "No_Foreign_Transaction_Fee", "Mastercard_Global_Emergency_Services",

    # Extra Services
    "Concierge_Service", "Movie_Benefits", "Golf_Privilege",
    "Flexible_Payment_Options", "Interest_Free_Days", "Online_Access", "SMS_Alerts",
    "Crypto_Rewards", "Mastercard_Experience_Offers"
]

'''
Column explanations:

### 🏦 Basic card details:
- Bank_ID – Unique ID for the bank (e.g., Emirates NBD = 1)
- Card_ID – Unique ID for the card (e.g., Marriott Bonvoy World Elite = 101)
- Card_Type – Type of card (1 = Credit, 2 = Charge, 3 = Prepaid)
- Card_Network – Card network provider (1 = Visa, 2 = Mastercard, 3 = Amex, 4 = Discover, etc.)

### 💰 Costs & Fees:
- Annual_Fee – Yearly fee in € (e.g., AED 1,575 ≈ €400)
- Joining_Fee – One-time joining fee in € (e.g., AED 1,575 ≈ €400)
- Interest_Rate_APR – Interest rate (APR %), if not available, set to 0
- Foreign_Transaction_Fee – Additional fee for foreign transactions (%)
- Balance_Transfer_Fee – Fee for balance transfers (%)
- Cash_Advance_Fee – Fee for cash withdrawals (% or fixed amount)
- Grace_Period_Days – Number of interest-free days if the balance is fully paid
- Late_Payment_Fee – Penalty fee for late payments in €

### 📊 Requirements:
- Min_Age – Minimum age required to apply for the card (e.g., 18)
- Max_Age – Maximum age limit for eligibility (if applicable, else 0)
- Minimum_Credit_Score – Minimum required credit score, if unknown, set to 0
- Minimum_Income – Minimum salary requirement in € (e.g., AED 25,000 ≈ €6,250)
- Credit_Limit – Maximum credit limit in € (if available)

### 🎁 Rewards & Points System:
- Welcome_Bonus_Points – Welcome bonus points (e.g., 150,000)
- Max_Annual_Points – Estimated maximum points earned per year (e.g., 169,380)
- Points_per_1_Hotel – Points earned per $1 spent at hotels (e.g., 6)
- Points_per_1_International – Points earned per $1 spent internationally (e.g., 3)
- Points_per_1_Domestic_Shopping – Points earned per $1 spent on retail/dining (e.g., 3)
- Points_per_1_Domestic_Groceries – Points earned per $1 spent at supermarkets (e.g., 0.75)
- Points_per_1_Domestic_Other – Points earned per $1 spent on real estate, utilities, etc. (e.g., 0.30)
- Express_Points_Available – Can the user enroll in Express Points? (1 = Yes, 0 = No)
- Express_Points_Fee – Monthly fee for Express Points in € (e.g., AED 300 ≈ €75)
'''

# ✅ CSV Management
class CSVHandler:
    @staticmethod
    def initialize_csv():
        """Maakt het CSV-bestand aan met de juiste kolomnamen als het niet bestaat."""
        if not os.path.exists(CSV_FILE):
            with open(CSV_FILE, "w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=COLUMNS)
                writer.writeheader()

    @staticmethod
    def save_to_csv(data_dict):
        """Slaat data op in de CSV met correcte kolomnamen."""
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=COLUMNS)
            writer.writerow(data_dict)



# test

