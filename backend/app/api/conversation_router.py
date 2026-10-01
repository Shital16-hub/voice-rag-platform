from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.auth_schema import CurrentUser
from app.models.models import Conversation, Message
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("")
async def list_conversations(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List conversations.
    Admin sees all tenant conversations.
    Regular user sees only their own.
    """
    if current_user.role == "admin":
        result = await db.execute(
            select(Conversation).where(
                Conversation.tenant_id == current_user.tenant_id
            ).order_by(Conversation.created_at.desc()).limit(50)
        )
    else:
        result = await db.execute(
            select(Conversation).where(
                Conversation.tenant_id == current_user.tenant_id,
                Conversation.user_id == current_user.user_id
            ).order_by(Conversation.created_at.desc()).limit(50)
        )

    conversations = result.scalars().all()
    logger.info(f"Listed {len(conversations)} conversations")

    return [
        {
            "id": c.id,
            "agent_id": c.agent_id,
            "channel": c.channel,
            "status": c.status,
            "created_at": c.created_at.isoformat()
        }
        for c in conversations
    ]


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get messages for a specific conversation.
    Enforces tenant isolation.
    """
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == current_user.tenant_id
        )
    )
    conversation = conv_result.scalar_one_or_none()

    if not conversation:
        return {"error": "Conversation not found"}

    msg_result = await db.execute(
        select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()

    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "sources": m.sources,
            "latency_ms": m.latency_ms,
            "created_at": m.created_at.isoformat()
        }
        for m in messages
    ]