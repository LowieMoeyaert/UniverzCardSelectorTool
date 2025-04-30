import json
import re
import requests
from qdrant_client.models import PointStruct
from qdrant_client.models import MatchValue as match
import tiktoken
from Credit_Card_Selector.Database.general_utils import (
    logger, encode_text, generate_unique_id, create_collection_if_not_exists
)
from Credit_Card_Selector.Database.qdrant_config import qdrant_client

# === Configuratie ===
SURVEY_COLLECTION = "credit_card_profiles"
CARDS_COLLECTION = "credit_cards"
OUTPUT_FILE = "recommended_cards.json"
SERVER_OUTPUT_FILE = "../../Database/Credit_Card_Profiles_Handler/recommended_cards.json"
SIMILARITY_THRESHOLD = 0.97
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


def get_all_cards():
    """Haalt alle beschikbare creditcards op uit de database."""
    cards = qdrant_client.scroll(collection_name=CARDS_COLLECTION, limit=CARD_FETCH_LIMIT)[0]
    logger.debug(f"📋 Opgehaalde kaarten uit DB: {len(cards)} kaarten")
    return cards


def get_cards_by_ids(card_ids):
    """Haalt kaarten op basis van een lijst van Card_ID's."""
    results = qdrant_client.scroll(
        collection_name=CARDS_COLLECTION,
        limit=len(card_ids),
        scroll_filter={"must": [{"key": "Card_ID", "match": {"any": card_ids}}]}
    )[0]
    logger.debug(f"🔍 Opgehaalde kaarten via ID's: {results}")
    return [{**card.payload, "Card_Name": card.payload["Card_ID"]} for card in results]


def filter_cards(cards, survey_response):
    """Filtert creditcards op basis van surveygegevens."""
    filtered_cards = []
    for card in cards:
        is_match = True
        for field, filter_type in FILTER_CONFIG.items():
            survey_value = survey_response.get(field)
            card_value = card.payload.get(field)

            if survey_value in [None, 0, ""] or card_value in [None, 0, ""]:
                continue

            if filter_type == "match" and survey_value != card_value:
                is_match = False
                break
            elif filter_type == "min" and float(survey_value) > float(card_value):
                is_match = False
                break

        if is_match:
            filtered_cards.append(card)

    logger.info(f"📉 Handmatige filtering: {len(cards)} → {len(filtered_cards)} kaarten over.")
    return filtered_cards


def vector_search(user_input_vector):
    """Voert een vector search uit met de gevectoriseerde input van de gebruiker en vergelijkt met de Survey_Vector in de database."""
    search_results = qdrant_client.search(
        collection_name=SURVEY_COLLECTION,
        query_vector=user_input_vector,
        limit=1,
        with_vectors=True
    )


    if search_results:
        best_result = sorted(search_results, key=lambda x: x.score, reverse=True)[0]  # Het beste resultaat
        logger.debug(f"🔍 Beste vector search resultaat: {best_result}")

        # Log de vector (de opgeslagen vector van de survey_response)
        logger.debug(f"🔍 Vector uit DB: {best_result.vector}")
        logger.debug(f"🔍 Binnengekomen vector van de gebruiker: {user_input_vector}")

        # Log de beste score
        logger.info(
            f"🔝 Beste vector search score: {best_result.score} voor Survey_ID: {best_result.payload.get('Survey_Response', {}).get('Survey_ID', 'Onbekend')}")

        if best_result.score >= SIMILARITY_THRESHOLD:
            logger.info(f"✅ Resultaat boven drempel gevonden: {best_result.score}")
            return best_result.payload["Survey_Response"], best_result.score
        else:
            logger.info(f"🔹 Similarity score te laag of geen resultaten, vragen aan LLM voor selectie...")
            return None, None
    else:
        logger.warning("⚠️ Vector search gaf geen resultaten.")
        return None, None

def generate_vector_from_survey_response(survey_response):
    """Genereert een consistente vectorrepresentatie van de survey_response."""
    normalized = {k: str(v).strip() for k, v in sorted(survey_response.items())}
    flat_text = json.dumps(normalized, separators=(",", ":"), sort_keys=True)
    return encode_text(flat_text)



def find_existing_survey_match(survey_vector):
    """Checkt of er een gelijkaardige surveyrespons bestaat."""
    search_results = qdrant_client.search(
        collection_name=SURVEY_COLLECTION,
        query_vector=survey_vector,
        limit=1,
        with_vectors=True
    )
    return search_results[0] if search_results else None


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")  # Fallback voor onbekende modellen
    return len(encoding.encode(text))


def create_base_prompt(survey_response):
    survey_json = json.dumps(survey_response, indent=2)
    return (
        f"""
            You are an API that selects the best credit cards. 
            Your output **must only be a JSON list** with exactly 5 recommended credit cards with their values shown in "Expected Output", without any extra text or explanations. I want only JSON in the response, nothing else.

            **Expected Output:**  
            [
                {{"Card_ID": "ValueOfCardID","Reason For Choice": "ReasonExplainedHere"}},
                {{"Card_ID": "ValueOfCardID","Reason For Choice": "ReasonExplainedHere"}},
                {{"Card_ID": "ValueOfCardID","Reason For Choice": "ReasonExplainedHere"}},
                {{"Card_ID": "ValueOfCardID","Reason For Choice": "ReasonExplainedHere"}},
                {{"Card_ID": "ValueOfCardID","Reason For Choice": "ReasonExplainedHere"}}
            ]

            **Survey Response:**
            {survey_json}

            **Available Credit Cards (only relevant fields):**
        """, survey_json)


def filter_cards_to_token_limit(cards, base_prompt_prefix, survey_json):
    max_tokens = 4096
    filtered_cards = []
    current_token_count = count_tokens(base_prompt_prefix + survey_json, model=OLLAMA_MODEL)

    for card in cards:
        temp_card = {key: card.payload[key] for key in RELEVANT_FIELDS if key in card.payload}
        test_cards = filtered_cards + [temp_card]
        test_prompt = base_prompt_prefix + json.dumps(test_cards, indent=2)
        test_token_count = count_tokens(test_prompt, model=OLLAMA_MODEL)

        if current_token_count + test_token_count >= max_tokens:
            break

        filtered_cards = test_cards
        current_token_count += test_token_count

    return filtered_cards


def send_prompt_to_llm(prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    logger.debug(f"📤 Sending prompt to LLM (tokens: {count_tokens(prompt)}):\n{json.dumps(payload, indent=2)}")

    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        logger.debug(f"📥 Received response from LLM: {response.text}")
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"⚠️ Error in communication with Ollama: {e}")
        return None


def is_valid_response(response):
    return response is not None and response.status_code == 200


def parse_json_response(response):
    try:
        return response.json()
    except json.JSONDecodeError:
        logger.error(f"⚠️ Invalid JSON received from LLM: {response.text}")
        return None


def parse_llm_output(llm_output):
    try:
        parsed_json = json.loads(llm_output)
        if isinstance(parsed_json, list) and all("Card_ID" in item for item in parsed_json):
            return parsed_json
    except json.JSONDecodeError:
        pass
    return None


def extract_fallback_from_text(text):
    matches = re.findall(r"\[\s*\{(?:.|\n)*?}\s*]", text)
    for match in matches:
        try:
            recommended_cards = json.loads(match)
            if isinstance(recommended_cards, list) and all("Card_ID" in card for card in recommended_cards):
                return recommended_cards
        except json.JSONDecodeError:
            continue
    return None


def extract_cards_from_response(response):
    if not is_valid_response(response):
        logger.error(f"⚠️ Invalid or failed response from Ollama: {getattr(response, 'status_code', 'No response')}")
        return []

    response_json = parse_json_response(response)
    if not response_json:
        return []

    llm_output = response_json.get("response", "").strip()

    parsed_cards = parse_llm_output(llm_output)
    if parsed_cards:
        return parsed_cards

    fallback_cards = extract_fallback_from_text(llm_output)
    if fallback_cards:
        return fallback_cards

    logger.error(f"⚠️ No valid JSON list found in the LLM response: {llm_output}")
    return []


def get_top_5_from_llm(cards, survey_response):
    ensure_ollama_running()
    base_prompt_prefix, survey_json = create_base_prompt(survey_response)
    filtered_cards = filter_cards_to_token_limit(cards, base_prompt_prefix, survey_json)
    full_prompt = base_prompt_prefix + json.dumps(filtered_cards, indent=2)
    response = send_prompt_to_llm(full_prompt)
    return extract_cards_from_response(response)


def save_to_qdrant(recommended_cards, survey_response):
    """Saves the recommended cards to Qdrant along with the survey response and its vector."""
    # Maak de vector van de survey response
    survey_vector = generate_vector_from_survey_response(survey_response)

    points = [
        PointStruct(
            id=generate_unique_id(),
            vector=survey_vector,  # De gevectoriseerde survey_response
            payload={
                "Survey_Response": survey_response,
                "Recommended_Cards": recommended_cards,
                "Survey_Vector": survey_vector  # Sla de vector zelf op
            }
        )
    ]

    qdrant_client.upsert(
        collection_name=SURVEY_COLLECTION,
        points=points
    )
    logger.info("✅ Recommended cards and survey vector successfully saved to Qdrant.")


def ensure_ollama_running():
    """Controleert of Llama3 draait en start het indien nodig."""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200 and OLLAMA_MODEL in response.json().get("models", []):
            logger.info(f"✅ {OLLAMA_MODEL} draait al.")
            return
    except requests.exceptions.RequestException as e:
        logger.warning(f"⚠️ Ollama-server lijkt niet te draaien: {e}. Controleer of Ollama is gestart.")

    logger.info(f"🔄 Start {OLLAMA_MODEL}...")
    start_response = requests.post("http://localhost:11434/api/pull", json={"name": OLLAMA_MODEL})

    if start_response.status_code == 200:
        logger.info(f"✅ {OLLAMA_MODEL} succesvol gestart!")
    else:
        logger.error(f"❌ Fout bij starten van {OLLAMA_MODEL}: {start_response.text}")


def create_survey_vector(response):
    """Genereert een vector vanuit een survey response op consistente manier."""
    survey_data = response.get("Survey_Response", response)
    return generate_vector_from_survey_response(survey_data)




def is_duplicate_survey(survey_vector):
    existing_survey = find_existing_survey_match(survey_vector)
    if existing_survey and existing_survey.score > SIMILARITY_THRESHOLD:
        logger.info(f"⚠️ Survey niet opgeslagen: lijkt te veel op een bestaande (score: {existing_survey.score:.2f})")
        return existing_survey
    return None


def retrieve_filtered_cards(response):
    all_cards = get_all_cards()
    filtered_cards = filter_cards(all_cards, response)
    if not filtered_cards:
        logger.warning("⚠️ Geen kaarten over na filtering! Controleer de filtering.")
    return filtered_cards


def process_survey_response(response):
    """Verwerkt een survey response en retourneert de aanbevolen kaarten, zonder duplicaten op te slaan."""
    create_collection_if_not_exists(SURVEY_COLLECTION)

    # Genereer de vector van de survey response
    survey_vector = create_survey_vector(response)

    # Controleer op bestaande gelijkaardige survey in de database
    existing_survey = find_existing_survey_match(survey_vector)
    if existing_survey and existing_survey.score >= SIMILARITY_THRESHOLD:
        logger.info(f"⚠️ Survey niet opgeslagen: lijkt te veel op een bestaande (score: {existing_survey.score:.2f})")

        # Haal de Card_ID's uit de bestaande survey payload
        card_dicts = existing_survey.payload.get("Recommended_Cards", [])
        existing_card_ids = [card['Card_ID'] for card in card_dicts if isinstance(card, dict) and 'Card_ID' in card]

        return get_cards_by_ids(existing_card_ids)

    # Filter de kaarten op basis van de survey response
    filtered_cards = retrieve_filtered_cards(response)
    if not filtered_cards:
        return []

    # Genereer de top 5 kaarten met behulp van LLM
    best_cards = get_top_5_from_llm(filtered_cards, response)

    # Sla enkel op als er daadwerkelijk kaarten gegenereerd zijn
    if best_cards:
        save_to_qdrant(best_cards, response)

    return best_cards if best_cards else []


if __name__ == "__main__":
    example_response = {
        "Card_Usage": "Boodschappen",
        "Frequency": "Maandelijks",
        "Interest_Rate_Importance": "Laag",
        "Credit_Score": 800,
        "Monthly_Income": "8700",
        "Minimum_Income": "6700",
        "Interest_Rate": "20"
    }

    process_survey_response(example_response)
    logger.info("🔹 Alle surveygegevens zijn succesvol opgeslagen!")
