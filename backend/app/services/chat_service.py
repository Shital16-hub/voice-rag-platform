import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Agent, Conversation, Message
from app.services.retrieval_service import retrieve_relevant_chunks
from app.services.llm_service import generate_answer
from app.schemas.chat_schema import ChatResponse, SourceChunk
from app.core.logger import get_logger

logger = get_logger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant. "
    "Answer questions based only on the provided sources. "
    "If you cannot find the answer in the sources, say so clearly."
)


async def process_chat(
    question: str,
    agent_id: str,
    tenant_id: str,
    user_id: str,
    db: AsyncSession
) -> ChatResponse:
    """
    Main chat flow:
    1. Load agent to get system prompt
    2. Retrieve relevant chunks
    3. Generate answer with LLM
    4. Save conversation and message
    5. Return answer with sources
    """
    start_time = time.time()
    logger.info(
        f"Chat request "
        f"agent_id={agent_id} "
        f"question={question[:50]}"
    )

    # Step 1: load agent
    result = await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.tenant_id == tenant_id,
            Agent.is_active == True
        )
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise ValueError(f"Agent not found agent_id={agent_id}")

    system_prompt = agent.system_prompt or DEFAULT_SYSTEM_PROMPT

    # Step 2: retrieve relevant chunks
    chunks = await retrieve_relevant_chunks(
        question=question,
        tenant_id=tenant_id,
        agent_id=agent_id
    )

    # Step 3: generate answer
    answer = await generate_answer(
        question=question,
        chunks=chunks,
        system_prompt=system_prompt
    )

    # Step 4: save conversation and message
    conversation = Conversation(
        tenant_id=tenant_id,
        agent_id=agent_id,
        user_id=user_id,
        channel="text",
        status="active"
    )
    db.add(conversation)
    await db.flush()

    latency_ms = int((time.time() - start_time) * 1000)

    message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        sources=[
            {
                "chunk_id": c["chunk_id"],
                "filename": c["filename"],
                "score": c["score"]
            }
            for c in chunks
        ],
        latency_ms=latency_ms
    )
    db.add(message)
    await db.commit()

    logger.info(
        f"Chat completed "
        f"latency_ms={latency_ms} "
        f"sources={len(chunks)}"
    )

    # Step 5: return response
    return ChatResponse(
        answer=answer,
        sources=[
            SourceChunk(
                chunk_id=c["chunk_id"],
                content=c["content"],
                filename=c["filename"],
                chunk_index=c["chunk_index"],
                score=c["score"]
            )
            for c in chunks
        ],
        conversation_id=conversation.id,
        message_id=message.id
    )