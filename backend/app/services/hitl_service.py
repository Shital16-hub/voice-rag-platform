from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import ApprovalRequest
from app.core.logger import get_logger

logger = get_logger(__name__)

# approval expires after 24 hours
APPROVAL_TIMEOUT_HOURS = 24


async def create_approval_request(
    tenant_id: str,
    agent_id: str,
    user_id: str,
    tool_name: str,
    tool_input: dict,
    agent_state: dict,
    conversation_id: str,
    db: AsyncSession
) -> ApprovalRequest:
    """
    Create a pending approval request.
    Stores the full agent state so we can resume later.
    """
    expires_at = datetime.utcnow() + timedelta(hours=APPROVAL_TIMEOUT_HOURS)

    # store agent state but remove non-serializable parts
    serializable_state = {
        k: v for k, v in agent_state.items()
        if isinstance(v, (str, int, float, bool, list, dict, type(None)))
    }

    approval = ApprovalRequest(
        tenant_id=tenant_id,
        agent_id=agent_id,
        conversation_id=conversation_id,
        user_id=user_id,
        tool_name=tool_name,
        tool_input=tool_input,
        agent_state=serializable_state,
        status="pending",
        expires_at=expires_at
    )
    db.add(approval)
    await db.commit()
    await db.refresh(approval)

    logger.info(
        f"Approval request created "
        f"id={approval.id} "
        f"tool={tool_name} "
        f"tenant={tenant_id}"
    )
    return approval


async def get_pending_approvals(
    tenant_id: str,
    db: AsyncSession
) -> list[ApprovalRequest]:
    """Get all pending approvals for a tenant."""
    result = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.tenant_id == tenant_id,
            ApprovalRequest.status == "pending"
        )
    )
    return result.scalars().all()


async def process_approval_decision(
    approval_id: str,
    tenant_id: str,
    approved_by: str,
    decision: str,
    note: str,
    db: AsyncSession
) -> ApprovalRequest:
    """
    Process approve or reject decision.
    Updates the approval record.
    """
    result = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.tenant_id == tenant_id,
            ApprovalRequest.status == "pending"
        )
    )
    approval = result.scalar_one_or_none()

    if not approval:
        raise ValueError(f"Approval not found or already processed id={approval_id}")

    # check if expired
    if approval.expires_at and datetime.utcnow() > approval.expires_at:
        approval.status = "expired"
        await db.commit()
        raise ValueError(f"Approval request has expired id={approval_id}")

    approval.status = decision
    approval.approved_by = approved_by
    approval.decision_at = datetime.utcnow()
    approval.decision_note = note
    await db.commit()
    await db.refresh(approval)

    logger.info(
        f"Approval decision processed "
        f"id={approval_id} "
        f"decision={decision} "
        f"by={approved_by}"
    )
    return approval