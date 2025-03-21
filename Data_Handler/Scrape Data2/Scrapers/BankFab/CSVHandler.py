import csv
import os


class CSVHandler:
    CSV_FILE = "credit_cards.csv"
    COLUMNS = [
        "Card_ID", "Card_Name", "Card_Link", "Card_Network", "Islamic",
        "Minimum_Income", "Interest_Rate_APR", "Annual_Fee", "Joining_Fee",
        "Cashback", "Cashback Grocery", "Cashback Fuel", "Cashback Dining", "Cashback Travel",
        "Discount Fashion", "Discount Shopping", "Discount Flights", "Discount Hotels",
        "Free Airport Transfers", "Fast Track Airport", "Free WiFi Flight",
        "Lounge Access", "Meet & Greet", "VIP Service", "Cinema Discount", "Golf Discount",
        "Theme Park Discount", "Travel Insurance", "Credit Shield", "Fraud Protection",
        "Purchase Protection", "Collision Damage Waiver", "Bonus Miles", "Valet Parking",
        "Gym & Sports Access", "Meet & Greet Airport", "Luxury Benefits", "Shopping Installments",
        "School Discounts", "Online Shopping Discount", "Transport Discounts", "Islamic Benefits",
        "Easy Payment Plans", "Balance Transfer", "Tier Miles", "Exclusive Dining",
        "Movie Tickets", "Visa Offers", "FAB Rewards", "Global Blue VIP",
        "Education Protection", "Islamic Exclusive",
        "Fast Track Membership", "Miles Accelerator", "School Fees Discount",
        "Concierge Service", "Gold Gift", "Unlimited SHARE Points", "Supplementary Cards", "Online Travel Discount",
        "Loyalty Miles Boost",
        "Valet Parking", "Global Car Rental Discount", "Religious Travel Benefits", "Luxury Lifestyle Perks",
        "Shopping Points", "Special Visa Offers", "No Foreign Transaction Fees", "10% off on du Easy Payment Plans",
        "Get instant Reward redemption", "Save more with exciting Mastercard offers",
        "Easier access anytime, anywhere with FAB Mobile",
        "Save money with low interest rates on card features and benefits", "The most affordable card in your wallet",
        "Convenient buy now, pay later plans", "Low interest rates per month for UAE nationals and expatriates",
        "3% minimum statement payment", "Zero foreign transaction bank fees", "Quick Cash",
        "Easy card management with FAB Mobile",
        "SMS alerts", "Set instructions for payments", "Wallet Shield", "Outstanding balance coverage",
        "Win exciting trips to Etihad Stadium in the UK",
        "Win official Man City jerseys", "Enjoy special discounts", "Buy 1 get 1 offers with Mastercard",
        "Instant redemption on Rewards", "First year free with a new card",
        "Free access to 60+ beach clubs, gyms and sports clubs with ADV+",
        "Get dedicated lifestyle concierge support 24/7", "Dine at over 150 restaurants in the UAE with up to 20% off",
        "Dine with up to 20% off at over 150 restaurants in the UAE",
        "Earn 1 FAB Reward on all other spending including abroad",
        "Receive 10% off car and truck rentals", "Exclusive SHARE member benefits", "SHARE with others",
        "Buy now, pay later plans", "Great rates on balance transfers", "Up to 3% extra value in BLUE",
        "Affordable airport transfers", "Easy payment plans", "Get fast tracked to Etihad Guest Gold status",
        "Discounted airport transfers", "Special Visa offers", "Free access to over 1,000 airport lounges worldwide",
        "Get fast tracked to Etihad Guest Silver status", "Exciting Visa offers", "No international transaction fees",
        "Earn and redeem FAB Miles", "Transfer miles between partners", "International airport transfers with UBER",
        "Earn more FAB Miles", "Excellent Mastercard benefits", "Free access to gyms and padel courts across the UAE",
        "Free access to gyms and padel courts", "Get 15 FAB Islamic Rewards at beauty and fragrance store shopping",
        "Get 10 FAB Islamic Rewards on international spending", "Get 5 FAB Islamic Rewards on all your other spending",
        "Fraudulent Card Misuse Protection"
    ]

    _existing_card_ids = set()

    @classmethod
    def initialize_csv(cls):
        """Maakt het CSV-bestand aan als het nog niet bestaat en voegt de kolomheaders toe."""
        if not os.path.exists(cls.CSV_FILE) or os.stat(cls.CSV_FILE).st_size == 0:
            with open(cls.CSV_FILE, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=cls.COLUMNS)
                writer.writeheader()
            print(f"✅ CSV bestand aangemaakt: {cls.CSV_FILE}")

        # ✅ Eenmalig laden bij start
        cls._existing_card_ids = set()
        for row in cls.read_csv():
            cls._existing_card_ids.add(row["Card_ID"])

    @classmethod
    def save_to_csv(cls, data_dict):
        """Voegt een nieuwe rij toe aan het CSV-bestand als deze nog niet bestaat."""
        if not os.path.exists(cls.CSV_FILE):
            cls.initialize_csv()

        valid_data = {key: str(data_dict.get(key, "0")).strip() for key in cls.COLUMNS}  # Trim spaties

        if valid_data["Card_ID"] in cls._existing_card_ids:
            print(f"⚠️ Kaart {valid_data['Card_ID']} bestaat al in de CSV. Skipping...")
            return
        cls._existing_card_ids.add(valid_data["Card_ID"])  # ✅ Updaten in cache

        with open(cls.CSV_FILE, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=cls.COLUMNS)
            writer.writerow(valid_data)
        print(f"✅ Kaart opgeslagen: {valid_data['Card_ID']}")

    @classmethod
    def read_csv(cls):
        """Leest het CSV-bestand en retourneert een lijst van dictionaries."""
        if not os.path.exists(cls.CSV_FILE):
            return []

        with open(cls.CSV_FILE, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            return list(reader)

    @classmethod
    def add_missing_category(cls, category_name):
        """Voegt een nieuwe kolom (categorie) toe aan het CSV-bestand als deze nog niet bestaat."""
        if category_name in cls.COLUMNS:
            return  # Categorie bestaat al, niets doen

        cls.COLUMNS.append(category_name)  # Voeg toe aan de kolommenlijst
        print(f"➕ Nieuwe categorie toegevoegd: {category_name}")

        # Lees de bestaande data
        existing_data = cls.read_csv()

        # Update alle rijen met de nieuwe categorie
        for row in existing_data:
            row[category_name] = "0"  # Standaardwaarde instellen

        # Schrijf de nieuwe CSV-header en data
        with open(cls.CSV_FILE, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=cls.COLUMNS)
            writer.writeheader()
            writer.writerows(existing_data)

        print(f"✅ CSV bijgewerkt met nieuwe categorie: {category_name}")
