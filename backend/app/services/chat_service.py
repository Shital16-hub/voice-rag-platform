import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Agent, Conversation, Message
from app.agents.generic_agent import generic_agent
from app.schemas.chat_schema import ChatResponse, SourceChunk
from app.core.logger import get_logger

logger = get_logger(__name__)


async def process_chat(
    question: str,
    agent_id: str,
    tenant_id: str,
    user_id: str,
    db: AsyncSession
) -> ChatResponse:
    start_time = time.time()
    logger.info(f"Chat request agent_id={agent_id} question={question[:50]}")

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

    tools_config = agent.tools_enabled or {}
    if isinstance(tools_config, list):
        builtin_tools = tools_config
        mcp_servers = []
    else:
        builtin_tools = tools_config.get("builtin", [])
        mcp_servers = tools_config.get("mcp_servers", [])

    initial_state = {
        "question": question,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "agent_id": agent_id,
        "system_prompt": agent.system_prompt or "You are a helpful assistant.",
        "tools_enabled": builtin_tools,
        "mcp_servers": mcp_servers,
        "retrieved_chunks": [],
        "route": None,
        "tool_name": None,
        "tool_input": None,
        "tool_result": None,
        "requires_approval": False,
        "approval_status": None,
        "answer": None,
        "error": None
    }

    logger.info(f"Running LangGraph agent tools={builtin_tools}")
    final_state = await generic_agent.ainvoke(initial_state)

    answer = final_state.get("answer") or "I could not generate an answer."
    chunks = final_state.get("retrieved_chunks", [])
    route = final_state.get("route", "unknown")

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
                "chunk_id": c.get("chunk_id", "tool"),
                "filename": c["filename"],
                "score": c["score"]
            }
            for c in chunks
        ],
        latency_ms=latency_ms
    )
    db.add(message)
    await db.commit()

    logger.info(f"Chat completed route={route} latency_ms={latency_ms}")

    real_chunks = [c for c in chunks if c.get("chunk_id") != "tool"]

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
            for c in real_chunks
        ],
        conversation_id=conversation.id,
        message_id=message.id
    )
