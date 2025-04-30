import logging
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
ENV_PATH = ".env"  # Path relative to the project root
VECTOR_SIZE = 384
DIFFERENCES_LOG_FILE = "differences.log"

# Load environment variables
load_dotenv(ENV_PATH)

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

# Bestand logging zonder kleur
file_handler = logging.FileHandler(DIFFERENCES_LOG_FILE, encoding="utf-8")
file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)
file_handler.setLevel(logging.INFO)

# Handlers toevoegen
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Model initialiseren
model = SentenceTransformer('all-MiniLM-L6-v2')


def encode_text(text):
    """Encodeert tekst naar een vector."""
    return model.encode(text).tolist()


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
    """Converteert NaN naar None en standaardiseert types voor vergelijking."""
    if isinstance(value, float) and np.isnan(value):
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
            logger.info(f"Collectie '{collection_name}' aangemaakt.")
        except Exception as e:
            logger.error(f"Fout bij aanmaken collectie: {e}")
    else:
        logger.info(f"Collectie '{collection_name}' bestaat al.")

def create_snapshot(collection_name):
    """Maak een snapshot van de collectie."""
    try:
        qdrant_client.create_snapshot(collection_name=collection_name)
        logger.info(f"Snapshot van collectie '{collection_name}' aangemaakt.")
    except Exception as e:
        logger.error(f"Fout bij maken snapshot: {e}")
