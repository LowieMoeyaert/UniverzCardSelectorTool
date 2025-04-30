import csv
import os


class CSVHandler:
    CSV_FILE = "credit_cards.csv"
    COLUMNS = [
        # Basic card details
        "Bank_ID", "Card_Link", "Card_Image", "Card_ID", "Card_Type", "Card_Network", "Islamic",

        "Minimum_Income", "Minimum_Age", "Minimum_Credit_Limit", "Eligibility_Requirements",
        "Employment_Type", "Nationality", "Residency_Required", "Credit_Score_Required",
        "Bank_Relationship_Required", "Fatwa_Approval",
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
