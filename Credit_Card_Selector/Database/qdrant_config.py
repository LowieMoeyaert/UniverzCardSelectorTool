import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

# Zoek en laad de .env (stel het pad in als nodig)
dotenv_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(dotenv_path)

# Controleer of de variabelen geladen zijn
qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_API_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)