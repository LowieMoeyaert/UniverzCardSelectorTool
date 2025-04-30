import csv
import os

class CSVHandler:
    CSV_FILE = "credit_cards.csv"
    COLUMNS = [
        "Bank_ID", "Card_Link", "Card_Image", "Card_ID", "Card_Type", "Card_Network", "Islamic",
        "Eligibility_Requirements",
        "Primary_Annual_Fee", "Supplementary_Annual_Fee", "Free_For_Life",
        "Bank_Relationship_Required", "Fatwa_Approval", "Benefits"  # <-- Hier toegevoegd

                                                        'For existing credit card customers: AED 500 Welcome Bonus on the card when you spend AED 9,000 or more in '
                                                        'the first 2 months post card issuance.',
        'Airport lounge access across the world\nRelax in 1000+ airport lounges by presenting your Card at the '
        'reception. Both Primary and Supplementary Solitaire Cardholders can visit along with a complimentary guest. '
        'Get details.',
        'Complimentary airport lounge\naccess to 1000+ lounges',
        'Let us valet park your car\nEnjoy 2 free valet parking per billing cycle at premium locations within Dubai '
        'and Abu Dhabi. Simply spend a minimum of AED 10,000 in your last billing cycle to avail. T&C’s.',
        'Mashreq Vantage points\nEarn rewards on spends and redeem them instantly',
        'Travel Easy\nDiscover a host of travel offers which offer peace of mind and great savings.',
        'Maximize Mashreq Vantage points on travel and on everyday spends\nEarn Mashreq Vantage reward points for all '
        'spends and redeem them instantly via Mashreq Mobile App or at a partner merchant for airmiles, gift cards, '
        'cashback and more. \nEarn 6 points per AED on international purchases, 4 points per AED on airlines, '
        'hotels and other travel spends, 2 points per AED on local spends and 1 point per AED on other local spends. '
        'To know more, mashreq.com/vantage.\n\nNote: Mashreq Vantage points cannot be earned on bill payments via '
        'Mashreq Online Banking or App.',
        'Car Assistance Services\nEnjoy 1 complimentary vehicle registration (renewal) pick up and drop off in a year '
        'and 2 complimentary vehicle servicing pick up or drop offs in a year. Simply spend AED 10,000 or more to '
        'avail. T&C\'s. For booking the service, please call +971 4 7047123',
        'Earn Mashreq Vantage points on all spends\nMore rewards when you travel',
        'Complimentary valet parking\nin Dubai & Abu Dhabi',
        'Tee off at premium golf clubs\nEnjoy complimentary games of golf per billing cycle at the UAE\'s exclusive '
        'Golf Clubs at Arabian Ranches Golf Club, Abu Dhabi Golf Club, The Track, Meydan Golf, The Els Club and Jebel '
        'Ali Golf Club.\nMaximum of 2 weekend games can be booked per billing cycle. Simply spend AED 10,000 or more '
        'in your last billing cycle to avail this benefit. T&C’s\nMake a booking',
        '50% discount on movie tickets\nGet 8 half price tickets across VOX, Reel and Novo Cinemas every billing '
        'month! Simply spend a minimum of AED 10,000 in the previous billing cycle to enjoy the benefit.\nClick here '
        'for details',
        'For new credit card customers: AED 2,500 Welcome Bonus on the card when you spend AED 9,000 or more in the '
        'first 2 months post card issuance.'
    ]


    _existing_card_ids = set()
    @classmethod
    def initialize_csv(cls):
        """Creates the CSV file if it doesn't exist and adds column headers."""
        if not os.path.exists(cls.CSV_FILE) or os.stat(cls.CSV_FILE).st_size == 0:
            try:
                with open(cls.CSV_FILE, mode="w", newline="", encoding="utf-8") as file:
                    writer = csv.DictWriter(file, fieldnames=cls.COLUMNS)
                    writer.writeheader()
                print(f"✅ CSV file created: {cls.CSV_FILE}")
            except Exception as e:
                print(f"❌ Error creating CSV file: {e}")

        # Load existing Card_IDs into the set
        cls._existing_card_ids = set()
        for row in cls.read_csv():
            cls._existing_card_ids.add(row["Card_ID"])

    @classmethod
    def save_to_csv(cls, data_dict):
        """Adds a new row to the CSV file if it doesn't already exist."""
        if not os.path.exists(cls.CSV_FILE):
            cls.initialize_csv()

        valid_data = {key: str(data_dict.get(key, "0")).strip() for key in cls.COLUMNS}  # Trim spaces

        if valid_data["Card_ID"] in cls._existing_card_ids:
            print(f"⚠️ Card {valid_data['Card_ID']} already exists in the CSV. Skipping...")
            return

        try:
            with open(cls.CSV_FILE, mode="a", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=cls.COLUMNS)
                writer.writerow(valid_data)
            cls._existing_card_ids.add(valid_data["Card_ID"])  # Update cache
            print(f"✅ Card saved: {valid_data['Card_ID']}")
        except Exception as e:
            print(f"❌ Error writing to CSV file: {e}")

    @classmethod
    def read_csv(cls):
        """Reads the CSV file and returns a list of dictionaries."""
        if not os.path.exists(cls.CSV_FILE):
            return []

        try:
            with open(cls.CSV_FILE, mode="r", newline="", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                return list(reader)
        except Exception as e:
            print(f"❌ Error reading CSV file: {e}")
            return []

    @classmethod
    def add_missing_category(cls, category_name):
        """Adds a new column (category) to the CSV file if it doesn't already exist."""
        if category_name in cls.COLUMNS:
            return  # Category already exists, do nothing

        cls.COLUMNS.append(category_name)  # Add to the list of columns
        print(f"➕ New category added: {category_name}")

        # Read existing data
        existing_data = cls.read_csv()

        # Update all rows with the new category
        for row in existing_data:
            row[category_name] = "0"  # Set default value

        # Write the new CSV header and data
        try:
            with open(cls.CSV_FILE, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=cls.COLUMNS)
                writer.writeheader()
                writer.writerows(existing_data)
            print(f"✅ CSV updated with new category: {category_name}")
        except Exception as e:
            print(f"❌ Error updating CSV file: {e}")
