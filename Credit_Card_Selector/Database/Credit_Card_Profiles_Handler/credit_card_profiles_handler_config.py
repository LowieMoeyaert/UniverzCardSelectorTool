# === Configuratie ===
from Credit_Card_Selector.Database.general_utils import load_env, load_env_value

SURVEY_COLLECTION = "credit_card_profiles"
CARDS_COLLECTION = "credit_cards"
OUTPUT_FILE = "recommended_cards.json"
SERVER_OUTPUT_FILE = "../../Database/Credit_Card_Profiles_Handler/recommended_cards.json"
SIMILARITY_THRESHOLD = 0.98

load_env()
OLLAMA_API_URL = load_env_value("OLLAMA_API_URL")
OLLAMA_MODEL = load_env_value("OLLAMA_MODEL")
MAX_TOKENS = load_env_value("MAX_TOKENS", cast=int)
CARD_FETCH_LIMIT = load_env_value("CARD_FETCH_LIMIT", default=1000, cast=int)
LLM_API_TIMEOUT = load_env_value("LLM_API_TIMEOUT", default=180, cast=int)  # Timeout in seconds for LLM API calls
# Dynamische filterconfiguratie
FILTER_CONFIG = {
    "Minimum_Income": "min",
    "Interest_Rate": "min",
    "Card_Type": "match",
    "Rewards": "match"
}


RELEVANT_FIELDS = [
    "Bank_ID", "Card_Link", "Card_Image", "Card_ID", "Card_Type", "Card_Network", "Islamic", "Minimum_Income",
    "Minimum_Age", "Minimum_Credit_Limit", "Eligibility_Requirements", "Employment_Type", "Nationality",
    "Residency_Required", "Credit_Score_Required", "Bank_Relationship_Required"
]