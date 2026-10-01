from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.auth_schema import CurrentUser
from app.models.models import Agent
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("")
async def list_agents(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all active agents for the logged in user's tenant.
    Works for both admin and regular users.
    Tenant isolation enforced via JWT token.
    """
    result = await db.execute(
        select(Agent).where(
            Agent.tenant_id == current_user.tenant_id,
            Agent.is_active == True
        )
    )
    agents = result.scalars().all()

    logger.info(
        f"Listed {len(agents)} agents "
        f"tenant_id={current_user.tenant_id}"
    )

    return [
        {
            "id": a.id,
            "name": a.name,
            "slug": a.slug,
            "system_prompt": a.system_prompt,
            "is_active": a.is_active
        }
        for a in agents
    ]