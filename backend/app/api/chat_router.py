from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.auth_schema import CurrentUser
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.services.chat_service import process_chat
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message", response_model=ChatResponse)
async def chat_message(
    request: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a question to an agent and get an answer.
    Answer is grounded in the agent knowledge base.
    """
    logger.info(
        f"Chat message received "
        f"agent_id={request.agent_id} "
        f"tenant_id={current_user.tenant_id}"
    )

    try:
        response = await process_chat(
            question=request.question,
            agent_id=request.agent_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
            db=db
        )
        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message"
        )