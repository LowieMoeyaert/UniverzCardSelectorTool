# === Configuratie ===
SURVEY_COLLECTION = "credit_card_profiles"
CARDS_COLLECTION = "credit_cards"
OUTPUT_FILE = "recommended_cards.json"
SERVER_OUTPUT_FILE = "../../Database/Credit_Card_Profiles_Handler/recommended_cards.json"
SIMILARITY_THRESHOLD = 0.98
CARD_FETCH_LIMIT = 1000

# Dynamische filterconfiguratie
FILTER_CONFIG = {
    "Minimum_Income": "min",
    "Interest_Rate": "min",
    "Card_Type": "match",
    "Rewards": "match"
}

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"

RELEVANT_FIELDS = [
    "Bank_ID", "Card_Link", "Card_Image", "Card_ID", "Card_Type", "Card_Network", "Islamic", "Minimum_Income",
    "Minimum_Age", "Minimum_Credit_Limit", "Eligibility_Requirements", "Employment_Type", "Nationality",
    "Residency_Required", "Credit_Score_Required", "Bank_Relationship_Required"
]

#
max_tokens = 4096