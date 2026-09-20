from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# single qdrant client instance
client = QdrantClient(
    host=settings.qdrant_host,
    port=settings.qdrant_port
)


def get_collection_name(tenant_id: str, agent_id: str) -> str:
    """
    Each agent gets its own Qdrant collection.
    This is how we enforce knowledge isolation.
    
    Example: tenant_abc_agent_xyz
    """
    return f"tenant_{tenant_id}_agent_{agent_id}"


async def ensure_collection_exists(tenant_id: str, agent_id: str):
    """
    Create Qdrant collection for this agent if it does not exist.
    nomic-embed-text produces 768 dimensional vectors.
    """
    collection_name = get_collection_name(tenant_id, agent_id)

    existing = client.get_collections()
    existing_names = [c.name for c in existing.collections]

    if collection_name not in existing_names:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=768,
                distance=Distance.COSINE
            )
        )
        logger.info(f"Created Qdrant collection: {collection_name}")
    else:
        logger.info(f"Qdrant collection already exists: {collection_name}")

    return collection_name