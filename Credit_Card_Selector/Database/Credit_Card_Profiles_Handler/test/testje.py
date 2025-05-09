import json
import re
import requests
from qdrant_client.models import PointStruct
import tiktoken
from Credit_Card_Selector.Database.general_utils import (
    get_logger, encode_text, generate_unique_id, create_collection_if_not_exists
)
from Credit_Card_Selector.Database.qdrant_config import qdrant_client
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.credit_card_profiles_handler_config import *

logger = get_logger(__file__)


def fetch_all_cards(collection_name, fetch_limit):
    """Haalt alle beschikbare creditcards op uit de database."""
    cards = qdrant_client.scroll(collection_name=collection_name, limit=fetch_limit)[0]
    logger.debug(f"📋 Opgehaalde kaarten uit DB: {len(cards)} kaarten")
    return cards


def fetch_cards_by_ids(collection_name, card_ids):
    """Haalt kaarten op basis van een lijst van Card_ID's."""
    results = qdrant_client.scroll(
        collection_name=collection_name,
        limit=len(card_ids),
        scroll_filter={"must": [{"key": "Card_ID", "match": {"any": card_ids}}]}
    )[0]
    logger.debug(f"🔍 Opgehaalde kaarten via ID's: {results}")
    return [{**card.payload, "Card_Name": card.payload["Card_ID"]} for card in results]


def apply_manual_filters(cards, survey_response):
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


def embed_survey_response(survey_response):
    """Genereert een consistente vectorrepresentatie van de survey_response."""
    normalized = {k: str(v).strip() for k, v in sorted(survey_response.items())}
    flat_text = json.dumps(normalized, separators=(",", ":"), sort_keys=True)
    return encode_text(flat_text)


def search_similar_survey(survey_vector):
    """Checkt of er een gelijkaardige surveyrespons bestaat en geeft het beste resultaat terug met logging."""
    search_results = qdrant_client.search(
        collection_name=SURVEY_COLLECTION,
        query_vector=survey_vector,
        limit=1,
        with_vectors=True
    )

    if search_results:
        best_result = search_results[0]  # Het beste resultaat
        logger.debug(f"🔍 Beste vector search resultaat: {best_result}")
        logger.debug(f"🔍 Vector uit DB: {best_result.vector}")
        logger.debug(f"🔍 Binnengekomen vector: {survey_vector}")
        logger.info(
            f"🔝 Beste vector search score: {best_result.score} voor Survey_ID: {best_result.payload.get('Survey_Response', {}).get('Survey_ID', 'Onbekend')}")
        return best_result
    else:
        logger.warning("⚠️ Vector search gaf geen resultaten.")
        return None


def count_prompt_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")  # Fallback voor onbekende modellen
    return len(encoding.encode(text))


def build_llm_prompt_prefix(survey_response):
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


def truncate_cards_to_token_limit(cards, base_prompt_prefix, survey_json):
    filtered_cards = []
    current_token_count = count_prompt_tokens(base_prompt_prefix + survey_json, model=OLLAMA_MODEL)

    for card in cards:
        temp_card = {key: card.payload[key] for key in RELEVANT_FIELDS if key in card.payload}
        filtered_cards.append(temp_card)  # Directly add the card

        # Recalculate the token count with the updated list
        test_prompt = base_prompt_prefix + json.dumps(filtered_cards, indent=2)
        test_token_count = count_prompt_tokens(test_prompt, model=OLLAMA_MODEL)

        # If the new token count exceeds the max, stop adding more cards
        if current_token_count + test_token_count >= MAX_TOKENS:
            filtered_cards.pop()  # Remove the last added card
            break

    return filtered_cards


def call_llm_api(prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    logger.debug(f"📤 Sending prompt to LLM (tokens: {count_prompt_tokens(prompt)}):\n{json.dumps(payload, indent=2)}")

    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        logger.debug(f"📥 Received response from LLM: {response.text}")
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"⚠️ Error in communication with Ollama: {e}")
        return None


def check_response_ok(response):
    return response is not None and response.status_code == 200


def safe_json_parse(response):
    try:
        return response.json()
    except json.JSONDecodeError:
        logger.error(f"⚠️ Invalid JSON received from LLM: {response.text}")
        return None


def extract_json_from_llm_output(llm_output):
    try:
        parsed_json = json.loads(llm_output)
        if isinstance(parsed_json, list) and all("Card_ID" in item for item in parsed_json):
            return parsed_json
    except json.JSONDecodeError:
        pass
    return None


def fallback_extract_json_list(text):
    # First try the original method - looking for JSON lists
    matches = re.findall(r"\[\s*\{(?:.|\n)*?}\s*]", text)
    for match in matches:
        try:
            recommended_cards = json.loads(match)
            if isinstance(recommended_cards, list) and all("Card_ID" in card for card in recommended_cards):
                return recommended_cards
        except json.JSONDecodeError:
            continue

    # If no JSON list found, try to extract card information from formatted text
    # Look for patterns like "Card_ID": "SomeCardName" or **CardName** (CardProvider)
    card_names = []

    # Pattern 1: Look for numbered list items with card names in bold or quotes
    numbered_items = re.findall(r'\d+\.\s+\*\*([^*]+)\*\*(?:\s+\(([^)]+)\))?', text)
    if numbered_items:
        for i, (card_name, provider) in enumerate(numbered_items):
            if i >= 5:  # Limit to 5 cards
                break
            full_name = card_name.strip()
            if provider:
                reason = f"Recommended by LLM. Provider: {provider.strip()}"
            else:
                reason = "Recommended by LLM"
            card_names.append({"Card_ID": full_name, "Reason For Choice": reason})

    # If we found cards using the numbered list pattern, return them
    if card_names:
        return card_names

    # Pattern 2: Look for card names in sections or bullet points
    sections = re.split(r'\n\s*\n', text)
    for section in sections:
        if '**' in section or '*' in section:
            # Try to extract card name from bold text
            bold_match = re.search(r'\*\*([^*]+)\*\*', section)
            if bold_match:
                card_name = bold_match.group(1).strip()
                # Extract some context for the reason
                reason_text = re.sub(r'\*\*[^*]+\*\*', '', section)
                reason = f"Recommended by LLM: {reason_text[:100].strip()}..."
                card_names.append({"Card_ID": card_name, "Reason For Choice": reason})
                if len(card_names) >= 5:
                    break

    return card_names if card_names else None


def parse_recommendations_from_llm(response):
    if not check_response_ok(response):
        logger.error(f"⚠️ Invalid or failed response from Ollama: {getattr(response, 'status_code', 'No response')}")
        return []

    response_json = safe_json_parse(response)
    if not response_json:
        return []

    llm_output = response_json.get("response", "").strip()

    parsed_cards = extract_json_from_llm_output(llm_output)
    if parsed_cards:
        return parsed_cards

    fallback_cards = fallback_extract_json_list(llm_output)
    if fallback_cards:
        return fallback_cards

    logger.error(f"⚠️ No valid JSON list found in the LLM response: {llm_output}")
    return []


def generate_top_5_with_llm(cards, survey_response):
    ensure_ollama_running()
    base_prompt_prefix, survey_json = build_llm_prompt_prefix(survey_response)
    filtered_cards = truncate_cards_to_token_limit(cards, base_prompt_prefix, survey_json)
    full_prompt = base_prompt_prefix + json.dumps(filtered_cards, indent=2)
    response = call_llm_api(full_prompt)
    return parse_recommendations_from_llm(response)


def store_recommendation_in_qdrant(recommended_cards, survey_response):
    """Saves the recommended cards to Qdrant along with the survey response and its vector."""
    # Maak de vector van de survey response
    survey_vector = embed_survey_response(survey_response)

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


def build_survey_vector(response):
    """Genereert een vector vanuit een survey response op consistente manier."""
    survey_data = response.get("Survey_Response", response)
    return embed_survey_response(survey_data)


def is_similar_survey_existing(survey_vector):
    existing_survey = search_similar_survey(survey_vector)
    if existing_survey and existing_survey.score > SIMILARITY_THRESHOLD:
        logger.info(f"⚠️ Survey niet opgeslagen: lijkt te veel op een bestaande (score: {existing_survey.score:.2f})")
        return existing_survey
    return None


def retrieve_filtered_cards(response):
    all_cards = fetch_all_cards(CARDS_COLLECTION, CARD_FETCH_LIMIT)
    filtered_cards = apply_manual_filters(all_cards, response)
    if not filtered_cards:
        logger.warning("⚠️ Geen kaarten over na filtering! Controleer de filtering.")
    return filtered_cards


def handle_survey_response(response):
    """Verwerkt een survey response en retourneert de aanbevolen kaarten, zonder duplicaten op te slaan."""
    create_collection_if_not_exists(SURVEY_COLLECTION)

    # Genereer de vector van de survey response
    survey_vector = build_survey_vector(response)

    # Controleer op bestaande gelijkaardige survey in de database
    existing_survey = search_similar_survey(survey_vector)
    if existing_survey and existing_survey.score >= SIMILARITY_THRESHOLD:
        logger.info(f"⚠️ Survey niet opgeslagen: lijkt te veel op een bestaande (score: {existing_survey.score:.2f})")

        # Haal de Card_ID's uit de bestaande survey payload
        card_dicts = existing_survey.payload.get("Recommended_Cards", [])
        # existing_card_ids = [card['Card_ID'] for card in card_dicts if isinstance(card, dict) and 'Card_ID' in card]
        # #return fetch_cards_by_ids(CARDS_COLLECTION, existing_card_ids)
        return card_dicts

    # Filter de kaarten op basis van de survey response
    filtered_cards = retrieve_filtered_cards(response)
    if not filtered_cards:
        return []

    # Genereer de top 5 kaarten met behulp van LLM
    best_cards = generate_top_5_with_llm(filtered_cards, response)

    # Sla enkel op als er daadwerkelijk kaarten gegenereerd zijn
    if best_cards:
        store_recommendation_in_qdrant(best_cards, response)

    return best_cards if best_cards else []


if __name__ == "__main__":
    example_response = {
        "Card_Usage": "Luxe uitgaven",
        "Frequency": "Dagelijks",
        "Interest_Rate_Importance": "Laag",
        "Credit_Score": 95,
        "Monthly_Income": "20000",
        "Minimum_Income": "25000",
        "Interest_Rate": "20",
        "Rewards": "Travel Miles",
        "Islamic": 1
    }

    handle_survey_response(example_response)
    logger.info("🔹 Alle surveygegevens zijn succesvol opgeslagen!")
