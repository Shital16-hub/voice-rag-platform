import httpx
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

OLLAMA_URL = f"http://{settings.ollama_host}:{settings.ollama_port}"


async def get_embedding(text: str) -> list[float]:
    """
    Send text to Ollama and get back an embedding vector.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/embed",
            json={
                "model": settings.ollama_embed_model,
                "input": text
            }
        )
        response.raise_for_status()
        data = response.json()
        embedding = data["embeddings"][0]
        logger.debug(
            f"Embedding created "
            f"model={settings.ollama_embed_model} "
            f"dimensions={len(embedding)}"
        )
        return embedding

async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """
    Get embeddings for multiple texts one by one.
    Returns list of embedding vectors.
    """
    embeddings = []
    for i, text in enumerate(texts):
        logger.debug(f"Embedding chunk {i+1} of {len(texts)}")
        embedding = await get_embedding(text)
        embeddings.append(embedding)
    return embeddings