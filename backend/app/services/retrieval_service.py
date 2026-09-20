from qdrant_client.models import Filter, FieldCondition, MatchValue
from app.core.qdrant_client import client as qdrant_client, get_collection_name
from app.services.embedding_service import get_embedding
from app.core.logger import get_logger

logger = get_logger(__name__)


async def retrieve_relevant_chunks(
    question: str,
    tenant_id: str,
    agent_id: str,
    top_k: int = 3
) -> list[dict]:
    """
    Search Qdrant for chunks most relevant to the question.
    
    Steps:
    1. Convert question to embedding
    2. Search Qdrant collection for this agent
    3. Return top K most similar chunks
    
    tenant_id and agent_id together determine which
    collection to search. This enforces isolation.
    """
    logger.info(
        f"Retrieving chunks "
        f"agent_id={agent_id} "
        f"top_k={top_k} "
        f"question={question[:50]}"
    )

    # Step 1: convert question to embedding
    question_embedding = await get_embedding(question)

    # Step 2: get collection name for this agent
    collection_name = get_collection_name(tenant_id, agent_id)

    # Step 3: search Qdrant
    results = qdrant_client.search(
        collection_name=collection_name,
        query_vector=question_embedding,
        limit=top_k,
        with_payload=True
    )

    # Step 4: format results
    chunks = []
    for result in results:
        chunk = {
            "chunk_id": result.id,
            "content": result.payload["text"],
            "filename": result.payload["filename"],
            "chunk_index": result.payload["chunk_index"],
            "score": result.score
        }
        chunks.append(chunk)
        logger.debug(
            f"Retrieved chunk "
            f"score={result.score:.3f} "
            f"filename={result.payload['filename']}"
        )

    logger.info(f"Retrieved {len(chunks)} chunks for question")
    return chunks