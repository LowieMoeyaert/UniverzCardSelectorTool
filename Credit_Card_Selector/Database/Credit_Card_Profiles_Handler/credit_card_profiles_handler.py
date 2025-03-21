import json
from qdrant_client.models import PointStruct, ScoredPoint
from Credit_Card_Selector.Database.general_utils import (
    logger, encode_text, generate_unique_id, create_collection_if_not_exists
)
from Credit_Card_Selector.Database.qdrant_config import qdrant_client

# === Configuratie ===
SURVEY_COLLECTION = "credit_card_profiles"
CARDS_COLLECTION = "credit_cards"
OUTPUT_FILE = "recommended_cards.json"
SERVER_OUTPUT_FILE = "../../Database/Credit_Card_Profiles_Handler/recommended_cards.json"
SIMILARITY_THRESHOLD = 0.95
VECTOR_SEARCH_LIMIT = 5
CARD_FETCH_LIMIT = 1000

# Dynamische filterconfiguratie
FILTER_CONFIG = {
    "Minimum_Income": "min",
    "Interest_Rate": "min",
    "Card_Type": "match",
    "Rewards": "match"
}

def get_all_cards():
    """Haalt alle beschikbare creditcards op uit de database."""
    return qdrant_client.scroll(collection_name=CARDS_COLLECTION, limit=CARD_FETCH_LIMIT)[0]

def get_cards_by_ids(card_ids):
    """Haalt kaarten op basis van een lijst van Card_ID's."""
    return [card.payload for card in qdrant_client.scroll(
        collection_name=CARDS_COLLECTION,
        limit=len(card_ids),
        scroll_filter={"must": [{"key": "Card_ID", "match": {"any": card_ids}}]}
    )[0]]

def filter_cards(cards, survey_response):
    """Filtert creditcards op basis van surveygegevens."""
    filtered_cards = []
    for card in cards:
        match = True
        for field, filter_type in FILTER_CONFIG.items():
            survey_value = survey_response.get(field)
            card_value = card.payload.get(field)

            if survey_value in [None, 0, ""] or card_value in [None, 0, ""]:
                continue

            if filter_type == "match" and survey_value != card_value:
                match = False
                break
            elif filter_type == "min" and float(survey_value) > float(card_value):
                match = False
                break

        if match:
            filtered_cards.append(card)

    logger.info(f"📉 Handmatige filtering: {len(cards)} → {len(filtered_cards)} kaarten over.")
    return filtered_cards

def vector_search(filtered_cards, survey_vector):
    """Voert een vector search uit en beperkt het resultaat tot max 5 kaarten."""
    if not filtered_cards:
        logger.info("⚠️ Geen kaarten over na filtering.")
        return None, None

    filtered_ids = [card.id for card in filtered_cards]
    search_results = qdrant_client.search(
        collection_name=CARDS_COLLECTION,
        query_vector=survey_vector,
        limit=VECTOR_SEARCH_LIMIT,
        query_filter={"must": [{"key": "id", "match": {"any": filtered_ids}}]}
    )

    if search_results:
        sorted_results = sorted(search_results, key=lambda x: x.score, reverse=True)[:5]
        return [card.payload for card in sorted_results], [card.score for card in sorted_results]
    else:
        return [card.payload for card in filtered_cards[:VECTOR_SEARCH_LIMIT]], None

def find_existing_survey_match(survey_vector):
    """Checkt of er een gelijkaardige surveyrespons bestaat."""
    search_results = qdrant_client.search(
        collection_name=SURVEY_COLLECTION,
        query_vector=survey_vector,
        limit=1
    )
    return search_results[0] if search_results else None

def process_survey_response(response):
    """Verwerkt een survey response en retourneert de aanbevolen kaarten."""
    create_collection_if_not_exists(SURVEY_COLLECTION)
    survey_vector = encode_text(" ".join(str(value) for value in response.values()))

    existing_survey = find_existing_survey_match(survey_vector)
    if existing_survey and existing_survey.score > SIMILARITY_THRESHOLD:
        logger.info(f"⚠️ Survey niet opgeslagen: lijkt te veel op een bestaande (score: {existing_survey.score:.2f})")
        existing_card_ids = existing_survey.payload.get("Recommended_Cards", [])
        return get_cards_by_ids(existing_card_ids)

    all_cards = get_all_cards()
    filtered_cards = filter_cards(all_cards, response)
    best_cards, _ = vector_search(filtered_cards, survey_vector)

    recommended_cards = [{"Card_ID": card["Card_ID"], **card} for card in best_cards] if best_cards else []

    qdrant_client.upsert(
        collection_name=SURVEY_COLLECTION,
        points=[PointStruct(id=generate_unique_id(), vector=survey_vector, payload={
            **response,
            "Recommended_Cards": [card["Card_ID"] for card in recommended_cards]
        })]
    )

    logger.info(f"✅ Survey opgeslagen, gekoppeld aan {[card['Card_ID'] for card in recommended_cards]}")
    return recommended_cards

if __name__ == "__main__":
    logger.info("🔹 Start met toevoegen van surveygegevens...")

    example_response = {
        "Card_Usage": "Reizen",
        "Frequency": "Wekelijks",
        "Interest_Rate_Importance": "Hoog",
        "Credit_Score": 80,
        "Monthly_Income": "5000",
        "Minimum_Income": "12000",
        "Interest_Rate": "10"
    }

    process_survey_response(example_response)
    logger.info("🔹 Alle surveygegevens zijn succesvol opgeslagen!")