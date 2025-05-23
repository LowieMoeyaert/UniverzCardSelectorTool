import numpy as np
import os
from typing import Dict, Any, List, Tuple, Optional
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue, PointIdsList
from Credit_Card_Selector.Database.general_utils import get_logger, encode_text, generate_unique_id, load_csv_data, \
    normalize_value, create_collection_if_not_exists, create_snapshot
from Credit_Card_Selector.Database.qdrant_config import qdrant_client
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.card_filtering import apply_manual_filters
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.database_operations import fetch_all_cards
from Credit_Card_Selector.Database.Credit_Card_Profiles_Handler.credit_card_profiles_handler_config import CARD_FETCH_LIMIT

CREDIT_CARDS_COLLECTION = "credit_cards"
# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get the root directory (three levels up from current script)
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
# Define path to CSV file
CSV_PATH = os.path.join(root_dir, 'Data_Handler', 'PreProcessor', 'merged_credit_cards.csv')
logger = get_logger(__file__)


def update_or_add_credit_card(credit_card):
    """Voegt een nieuwe creditcard toe of update een bestaande als er verschillen zijn."""
    try:
        create_collection_if_not_exists(CREDIT_CARDS_COLLECTION)

        # Get card identifiers for lookup
        card_id = credit_card.get("Card_ID", "")
        card_link = credit_card.get("Card_Link", "")
        existing_card = find_existing_credit_card(card_id, card_link)

        # Use .get() with default values to handle missing fields for encoding
        card_type = credit_card.get('Card_Type', '')
        card_network = credit_card.get('Card_Network', '')
        eligibility = credit_card.get('Eligibility_Requirements', '')

        # Log warning if any required fields are missing
        missing_fields = []
        if not card_id:
            missing_fields.append('Card_ID')
        if not card_type:
            missing_fields.append('Card_Type')
        if not card_network:
            missing_fields.append('Card_Network')
        if not eligibility:
            missing_fields.append('Eligibility_Requirements')

        if missing_fields:
            logger.warning(f"Ontbrekende velden in creditcard data: {', '.join(missing_fields)}")
            logger.warning(f"Creditcard data: {credit_card}")

        # Create encoded text with available fields
        encoded_text = f"{card_id} {card_type} {card_network} {eligibility}"

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

        conditions = []

        if card_id and not (isinstance(card_id, float) and np.isnan(card_id)):
            conditions.append(
                FieldCondition(
                    key="Card_ID",
                    match=MatchValue(value=str(card_id))
                )
            )

        if card_link and not (isinstance(card_link, float) and np.isnan(card_link)):
            conditions.append(
                FieldCondition(
                    key="Card_Link",
                    match=MatchValue(value=str(card_link))
                )
            )

        if conditions:
            results = qdrant_client.scroll(
                collection_name=CREDIT_CARDS_COLLECTION,
                limit=1,
                with_payload=True,
                with_vectors=True,
                scroll_filter=Filter(should=conditions)
            )

            if results and results[0]:
                return results[0][0]

            # If exact match fails and we have a card_id, try to get all cards and find a case-insensitive match
            if card_id and not (isinstance(card_id, float) and np.isnan(card_id)):
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
            points_selector=PointIdsList(ids=[str(card_id)])  # Correct formaat voor Qdrant
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
                points_selector=PointIdsList(ids=outdated_point_ids)  # 🔥 Nu verwijderen we met Point ID's
            )
            logger.info(f"🗑️ {len(outdated_point_ids)} verouderde creditcards verwijderd.")
        else:
            logger.info("✅ Geen verouderde creditcards gevonden.")

    except Exception as e:
        logger.error(f"Fout bij verwijderen verouderde creditcards: {e}")

def update_credit_cards_from_csv(csv_path=CSV_PATH):
    """
    Update the credit card database with data from a CSV file.

    Args:
        csv_path (str, optional): Path to the CSV file. Defaults to CSV_PATH.

    Returns:
        tuple: (success, message, stats) where:
            - success (bool): True if the update was successful, False otherwise
            - message (str): A message describing the result of the operation
            - stats (dict): Statistics about the update operation (cards processed, errors, etc.)
    """
    logger.info("🔹 Database update started...")
    stats = {
        "success_count": 0,
        "error_count": 0,
        "outdated_removed": 0
    }

    try:
        # Create a snapshot for backup
        try:
            create_snapshot(CREDIT_CARDS_COLLECTION)
        except Exception as e:
            logger.error(f"Fout bij het maken van een snapshot: {e}")
            # Continue execution even if snapshot creation fails

        # Create collection if it doesn't exist
        try:
            create_collection_if_not_exists(CREDIT_CARDS_COLLECTION)
        except Exception as e:
            logger.error(f"Fout bij het controleren/aanmaken van collectie: {e}")
            return False, "Failed to create or check collection", stats

        # Load and process CSV data
        data = load_csv_data(csv_path)
        if data is not None:
            existing_card_ids = set()

            for _, row in data.iterrows():
                try:
                    credit_card = row.to_dict()
                    update_or_add_credit_card(credit_card)
                    card_id = credit_card.get("Card_ID")
                    if card_id:
                        existing_card_ids.add(card_id)
                    stats["success_count"] += 1
                except Exception as e:
                    stats["error_count"] += 1
                    logger.error(f"Fout bij verwerken van creditcard rij: {e}")
                    # Continue with the next card even if this one fails

            logger.info(f"✅ {stats['success_count']} creditcards succesvol verwerkt.")
            if stats["error_count"] > 0:
                logger.warning(f"⚠️ {stats['error_count']} creditcards konden niet worden verwerkt vanwege fouten.")

            # Remove outdated cards
            try:
                remove_outdated_credit_cards(existing_card_ids)
                # Note: We don't have a way to count how many were removed here
                # This would require modifying remove_outdated_credit_cards to return the count
            except Exception as e:
                logger.error(f"Fout bij het verwijderen van verouderde creditcards: {e}")

            logger.info("🔹 Database-update voltooid!")
            return True, f"Successfully processed {stats['success_count']} credit cards", stats
        else:
            error_msg = "Geen data geladen uit CSV bestand."
            logger.error(error_msg)
            return False, error_msg, stats
    except Exception as e:
        error_msg = f"Onverwachte fout tijdens uitvoering: {e}"
        logger.error(error_msg)
        return False, error_msg, stats


if __name__ == "__main__":
    logger.info("🔹 Script gestart...")
    success, message, stats = update_credit_cards_from_csv()
    if success:
        logger.info(f"✅ {message}")
    else:
        logger.error(f"❌ {message}")
    logger.info("🔹 Database-update voltooid!")
