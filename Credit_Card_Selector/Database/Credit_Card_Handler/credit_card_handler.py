from qdrant_client.models import PointStruct
from Credit_Card_Selector.Database.general_utils import logger, encode_text, generate_unique_id, load_csv_data, normalize_value, \
    create_collection_if_not_exists
from Credit_Card_Selector.Database.qdrant_config import qdrant_client

# === Configuratie ===
CREDIT_CARDS_COLLECTION = "credit_cards"
CSV_PATH = "../../../Data_Handler/PreProcessor/merged_credit_cards.csv"
SERVER_CSV_PATH = "../../Data_Handler/PreProcessor/merged_credit_cards.csv"


def update_or_add_credit_card(credit_card):
    """Voegt een nieuwe creditcard toe of update een bestaande als er verschillen zijn."""
    create_collection_if_not_exists(CREDIT_CARDS_COLLECTION)

    card_id = credit_card.get("Card_ID")
    card_link = credit_card.get("Card_Link")
    existing_card = find_existing_credit_card(card_id, card_link)

    encoded_text = f"{credit_card['Card_ID']} {credit_card['Card_Type']} {credit_card['Card_Network']} {credit_card['Eligibility_Requirements']}"
    new_vector = encode_text(encoded_text)

    if existing_card:
        existing_payload = existing_card.payload

        differences = []

        for key in credit_card:
            old_value = normalize_value(existing_payload.get(key, None))
            new_value = normalize_value(credit_card[key])

            if str(old_value) != str(new_value):
                differences.append(f"{key}: '{old_value}' -> '{new_value}'")

        if differences:
            logger.info(f"🔄 Verschil gevonden! Updaten van '{card_id or card_link}'...")
            for diff in differences:
                logger.info(f"🔄 {card_id or card_link} | {diff}")
                logger.info(f"{card_id or card_link} | {diff}", extra={"logfile": True})

            updated_card = PointStruct(
                id=existing_card.id,
                vector=new_vector,
                payload=credit_card
            )

            qdrant_client.upsert(collection_name=CREDIT_CARDS_COLLECTION, points=[updated_card])
            logger.info(f"✅ Creditcard '{card_id or card_link}' geüpdatet in de database.")
        else:
            logger.info(f"✅ '{card_id or card_link}' is al up-to-date. Geen update nodig.")
    else:
        new_card = PointStruct(
            id=generate_unique_id(),
            vector=new_vector,
            payload=credit_card
        )
        qdrant_client.upsert(collection_name=CREDIT_CARDS_COLLECTION, points=[new_card])
        logger.info(f"✅ Nieuwe creditcard '{card_id or card_link}' toegevoegd!")


def find_existing_credit_card(card_id, card_link):
    """Zoekt een bestaande creditcard op ID of Link."""
    try:
        filters = {
            "should": [
                {"key": "Card_ID", "match": {"value": card_id}},
                {"key": "Card_Link", "match": {"value": card_link}}
            ]
        }
        results = qdrant_client.scroll(
            collection_name=CREDIT_CARDS_COLLECTION,
            limit=1,
            with_payload=True,
            with_vectors=True,
            scroll_filter=filters
        )
        if results and results[0]:
            return results[0][0]
    except Exception as e:
        logger.error(f"Fout bij zoeken naar creditcard: {e}")
    return None


if __name__ == "__main__":
    logger.info("🔹 Script gestart...")
    create_collection_if_not_exists(CREDIT_CARDS_COLLECTION)

    data = load_csv_data(CSV_PATH)
    if data is not None:
        for _, row in data.iterrows():
            credit_card = row.to_dict()
            update_or_add_credit_card(credit_card)

    logger.info("🔹 Database-update voltooid!")