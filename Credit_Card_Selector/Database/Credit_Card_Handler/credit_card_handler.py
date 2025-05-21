from qdrant_client.models import PointStruct, PointIdsList
from Credit_Card_Selector.Database.general_utils import get_logger, encode_text, generate_unique_id, load_csv_data, \
    normalize_value, create_collection_if_not_exists, create_snapshot
from Credit_Card_Selector.Database.qdrant_config import qdrant_client

# === Configuratie ===
CREDIT_CARDS_COLLECTION = "credit_cards"
CSV_PATH = "../../../Data_Handler/PreProcessor/merged_credit_cards.csv"
logger = get_logger(__file__)


def update_or_add_credit_card(credit_card):
    """Voegt een nieuwe creditcard toe of update een bestaande als er verschillen zijn."""
    try:
        create_collection_if_not_exists(CREDIT_CARDS_COLLECTION)

        card_id = credit_card.get("Card_ID")
        card_link = credit_card.get("Card_Link")
        existing_card = find_existing_credit_card(card_id, card_link)

        try:
            encoded_text = (f"{credit_card['Card_ID']} "
                        f"{credit_card['Card_Type']} "
                        f"{credit_card['Card_Network']} "
                        f"{credit_card['Eligibility_Requirements']}")
        except KeyError as e:
            logger.error(f"Ontbrekende sleutel in creditcard data: {e}")
            logger.error(f"Creditcard data: {credit_card}")
            return

        try:
            new_vector = encode_text(encoded_text)
        except Exception as e:
            logger.error(f"Fout bij het encoderen van tekst: {e}")
            return

        if existing_card:
            try:
                existing_payload = existing_card.payload
                differences = [
                    f"{key}: '{normalize_value(existing_payload.get(key))}' -> '{normalize_value(credit_card[key])}'"
                    for key in credit_card if
                    str(normalize_value(existing_payload.get(key))) != str(normalize_value(credit_card[key]))
                ]

                if differences:
                    logger.info(f"🔄 Verschil gevonden! Updaten van '{card_id or card_link}'...")

                    updated_card = PointStruct(
                        id=existing_card.id,
                        vector=new_vector,
                        payload=credit_card
                    )

                    qdrant_client.upsert(collection_name=CREDIT_CARDS_COLLECTION, points=[updated_card])
                    logger.info(f"✅ Creditcard '{card_id or card_link}' geüpdatet in de database.")
                else:
                    logger.info(f"✅ '{card_id or card_link}' is al up-to-date. Geen update nodig.")
            except Exception as e:
                logger.error(f"Fout bij het updaten van creditcard '{card_id or card_link}': {e}")
        else:
            try:
                new_card = PointStruct(
                    id=generate_unique_id(),
                    vector=new_vector,
                    payload=credit_card
                )
                qdrant_client.upsert(collection_name=CREDIT_CARDS_COLLECTION, points=[new_card])
                logger.info(f"✅ Nieuwe creditcard '{card_id or card_link}' toegevoegd!")
            except Exception as e:
                logger.error(f"Fout bij het toevoegen van nieuwe creditcard '{card_id or card_link}': {e}")
    except Exception as e:
        logger.error(f"Onverwachte fout in update_or_add_credit_card: {e}")


def find_existing_credit_card(card_id, card_link):
    """Zoekt een bestaande creditcard op ID of Link."""
    try:
        # First try exact match
        filters = {"should": []}
        if card_id:
            filters["should"].append({"key": "Card_ID", "match": {"value": card_id}})
        if card_link:
            filters["should"].append({"key": "Card_Link", "match": {"value": card_link}})

        if filters["should"]:
            results = qdrant_client.scroll(
                collection_name=CREDIT_CARDS_COLLECTION,
                limit=1,
                with_payload=True,
                with_vectors=True,
                scroll_filter=filters
            )
            if results and results[0]:
                return results[0][0]

            # If exact match fails and we have a card_id, try to get all cards and find a case-insensitive match
            if card_id:
                logger.info(f"Exact match failed for '{card_id}', trying case-insensitive match...")
                all_cards = qdrant_client.scroll(
                    collection_name=CREDIT_CARDS_COLLECTION,
                    limit=1000,  # Adjust based on your expected number of cards
                    with_payload=True,
                    with_vectors=True
                )

                if all_cards and all_cards[0]:
                    # Try to find a case-insensitive match
                    card_id_lower = card_id.lower()
                    for card in all_cards[0]:
                        if hasattr(card, "payload") and "Card_ID" in card.payload:
                            stored_card_id = card.payload["Card_ID"]
                            if stored_card_id and stored_card_id.lower() == card_id_lower:
                                logger.info(f"Found card with case-insensitive match: '{stored_card_id}'")
                                return card

                    logger.warning(f"No case-insensitive match found for '{card_id}'")

            return None
        else:
            logger.warning("Geen geldige Card_ID of Card_Link om te zoeken.")
    except Exception as e:
        logger.error(f"Fout bij zoeken naar creditcard: {e}")
    return None


def delete_credit_card(card_id):
    """Verwijdert een creditcard uit de database op basis van het ID."""
    try:
        qdrant_client.delete(
            collection_name=CREDIT_CARDS_COLLECTION,
            points=PointIdsList(ids=[str(card_id)])  # Correct formaat voor Qdrant
        )
        logger.info(f"🗑️ Creditcard met ID '{card_id}' verwijderd.")
    except Exception as e:
        logger.error(f"Fout bij verwijderen creditcard met ID '{card_id}': {e}")


def remove_outdated_credit_cards(existing_card_ids):
    """Verwijdert creditcards die niet in de CSV staan op basis van hun Point ID."""
    try:
        # Haal alle opgeslagen creditcards op
        results = qdrant_client.scroll(
            collection_name=CREDIT_CARDS_COLLECTION,
            limit=10000,
            with_payload=True,  # We hebben de payload nodig om `Card_ID` te checken
            with_vectors=False
        )

        # Maak een mapping van Card_ID → Point ID
        card_id_to_point_id = {
            point.payload.get("Card_ID"): point.id for point in results[0] if "Card_ID" in point.payload
        }

        # Zoek welke kaarten niet meer in de CSV staan
        outdated_card_ids = set(card_id_to_point_id.keys()) - set(existing_card_ids)

        # Zoek bijhorende Point ID's
        outdated_point_ids = [card_id_to_point_id[card_id] for card_id in outdated_card_ids]

        if outdated_point_ids:
            qdrant_client.delete(
                collection_name=CREDIT_CARDS_COLLECTION,
                points=outdated_point_ids  # 🔥 Nu verwijderen we met Point ID's
            )
            logger.info(f"🗑️ {len(outdated_point_ids)} verouderde creditcards verwijderd.")
        else:
            logger.info("✅ Geen verouderde creditcards gevonden.")

    except Exception as e:
        logger.error(f"Fout bij verwijderen verouderde creditcards: {e}")


if __name__ == "__main__":
    logger.info("🔹 Script gestart...")

    try:
        create_snapshot(CREDIT_CARDS_COLLECTION)
    except Exception as e:
        logger.error(f"Fout bij het maken van een snapshot: {e}")
        # Continue execution even if snapshot creation fails

    try:
        create_collection_if_not_exists(CREDIT_CARDS_COLLECTION)
    except Exception as e:
        logger.error(f"Fout bij het controleren/aanmaken van collectie: {e}")
        logger.error("Script wordt gestopt omdat de collectie nodig is voor verdere verwerking.")
        exit(1)  # Exit if collection creation fails as it's critical

    try:
        data = load_csv_data(CSV_PATH)
        if data is not None:
            existing_card_ids = set()
            error_count = 0
            success_count = 0

            for _, row in data.iterrows():
                try:
                    credit_card = row.to_dict()
                    update_or_add_credit_card(credit_card)
                    card_id = credit_card.get("Card_ID")
                    if card_id:
                        existing_card_ids.add(card_id)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"Fout bij verwerken van creditcard rij: {e}")
                    # Continue with next card even if this one fails

            logger.info(f"✅ {success_count} creditcards succesvol verwerkt.")
            if error_count > 0:
                logger.warning(f"⚠️ {error_count} creditcards konden niet worden verwerkt vanwege fouten.")

            try:
                remove_outdated_credit_cards(existing_card_ids)
            except Exception as e:
                logger.error(f"Fout bij het verwijderen van verouderde creditcards: {e}")
        else:
            logger.error("Geen data geladen uit CSV bestand.")
    except Exception as e:
        logger.error(f"Onverwachte fout tijdens uitvoering: {e}")

    logger.info("🔹 Database-update voltooid!")
