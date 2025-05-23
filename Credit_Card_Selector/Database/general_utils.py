import logging
import os
from pathlib import Path
from typing import Any, Callable, Optional

import colorlog
import uuid
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from qdrant_client.conversions.common_types import VectorParams
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from Credit_Card_Selector.Database.qdrant_config import qdrant_client

# === Configuratie ===
ENV_PATH = Path("CREDIT_CARD_SELECTOR/.env")


# === Load environment variables ===
def load_env():
    load_dotenv(dotenv_path=ENV_PATH)


load_env()


def load_env_value(
        key: str,
        default: Any = None,
        cast: Optional[Callable[[str], Any]] = None,
        log: Optional[Callable[[str], None]] = print
) -> Any:
    """Load a value from environment with optional type casting and fallback."""
    raw_value = os.getenv(key)

    if raw_value is None:
        log(f"[env] {key} not set. Using default: {default}")
        return default

    try:
        value = cast(raw_value) if cast else raw_value
        log(f"[env] {key} loaded: {value}")
        return value
    except Exception as e:
        log(f"[env] Failed to cast {key}: {e}. Using default: {default}")
        return default


# === Load model settings ===
VECTOR_SIZE = load_env_value("VECTOR_SIZE", default=1024, cast=int)
MODEL_NAME = load_env_value("SENTENCE_TRANSFORMER_MODEL", default="intfloat/multilingual-e5-large")

try:
    MODEL = SentenceTransformer(MODEL_NAME)
    print(f"[model] Loaded model: {MODEL_NAME}")
except Exception as e:
    fallback_model = "all-MiniLM-L6-v2"
    print(f"[model] Failed to load '{MODEL_NAME}', using fallback '{fallback_model}': {e}")
    MODEL = SentenceTransformer(fallback_model)

# === Logging configuratie ===
logger = logging.getLogger("credit_card_logger")
logger.setLevel(logging.DEBUG)

# Console logging met kleuren
console_handler = logging.StreamHandler()
console_formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }
)
console_handler.setFormatter(console_formatter)


# Handlers toevoegen
logger.addHandler(console_handler)


def get_logger(module_file: str) -> logging.Logger:
    script_name = Path(module_file).stem

    # Bepaal project root en log map
    project_root = Path(__file__).resolve().parents[2]
    log_dir = project_root / "Credit_Card_Selector" / "Logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = log_dir / f"{script_name}.log"

    logger = logging.getLogger(script_name)
    logger.setLevel(logging.DEBUG)

    if not logger.hasHandlers():
        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            }
        )
        console_handler.setFormatter(console_formatter)

        # File handler
        file_handler = logging.FileHandler(str(log_file_path), encoding="utf-8")
        file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.INFO)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger


def encode_text(text):
    """Encodeert tekst naar een vector."""
    vector = MODEL.encode(text)
    if len(vector) != VECTOR_SIZE:
        # Padding naar VECTOR_SIZE dimensies
        padded_vector = np.zeros(1024, dtype=np.float32)
        padded_vector[:len(vector)] = vector
        return padded_vector.tolist()
    return vector.tolist()


def generate_unique_id():
    """Genereert een unieke ID."""
    return str(uuid.uuid4())


def load_csv_data(csv_path):
    """Lees de CSV en laad de gegevens dynamisch in."""
    try:
        df = pd.read_csv(csv_path)
        logger.info(f"CSV met {len(df)} rijen geladen.")
        return df
    except Exception as e:
        logger.error(f"Fout bij het laden van CSV: {e}")
        return None


def normalize_value(value):
    """Converteert NaN of None naar None en stript strings."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, str):
        return value.strip()
    return value



def collection_exists(collection_name):
    """Check of een collectie bestaat."""
    try:
        collections = qdrant_client.get_collections()
        return collection_name in [col.name for col in collections.collections]
    except Exception as e:
        logger.error(f"Fout bij ophalen collecties: {e}")
        return False


def create_collection_if_not_exists(collection_name):
    """Maak een collectie aan als deze nog niet bestaat."""
    if not collection_exists(collection_name):
        try:
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance="Cosine")
            )
            # Create index for Card_ID field
            qdrant_client.create_payload_index(
                collection_name=collection_name,
                field_name="Card_ID",
                field_schema="keyword"
            )
            # Create index for Card_Link field
            qdrant_client.create_payload_index(
                collection_name=collection_name,
                field_name="Card_Link",
                field_schema="keyword"
            )
            logger.info(f"Collectie '{collection_name}' aangemaakt met indexen voor Card_ID en Card_Link.")
        except Exception as e:
            logger.error(f"Fout bij aanmaken collectie: {e}")
    else:
        logger.info(f"Collectie '{collection_name}' bestaat al.")
        # Ensure indexes exist even for existing collections
        try:
            qdrant_client.create_payload_index(
                collection_name=collection_name,
                field_name="Card_ID",
                field_schema="keyword"
            )
            logger.info(f"Index voor Card_ID aangemaakt in bestaande collectie '{collection_name}'.")
        except Exception as e:
            # If index already exists, this will throw an error, which is fine
            logger.debug(f"Index voor Card_ID bestaat mogelijk al: {e}")

        try:
            qdrant_client.create_payload_index(
                collection_name=collection_name,
                field_name="Card_Link",
                field_schema="keyword"
            )
            logger.info(f"Index voor Card_Link aangemaakt in bestaande collectie '{collection_name}'.")
        except Exception as e:
            # If index already exists, this will throw an error, which is fine
            logger.debug(f"Index voor Card_Link bestaat mogelijk al: {e}")


def create_snapshot(collection_name):
    """Maak een snapshot van de collectie."""
    try:
        qdrant_client.create_snapshot(collection_name=collection_name)
        logger.info(f"Snapshot van collectie '{collection_name}' aangemaakt.")
    except Exception as e:
        logger.error(f"Fout bij maken snapshot: {e}")
