from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import require_admin, get_current_user
from app.schemas.auth_schema import CurrentUser
from app.schemas.hitl_schema import (
    ApprovalRequestResponse,
    ApprovalDecisionRequest,
    ApprovalDecisionResponse
)
from app.services.hitl_service import (
    get_pending_approvals,
    process_approval_decision
)
from app.agents.tool_registry import execute_builtin_tool
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalRequestResponse])
async def list_pending_approvals(
    current_user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List all pending approvals for this tenant.
    Only admins can see and act on approvals.
    """
    approvals = await get_pending_approvals(
        tenant_id=current_user.tenant_id,
        db=db
    )

    return [
        ApprovalRequestResponse(
            id=a.id,
            tool_name=a.tool_name,
            tool_input=a.tool_input or {},
            status=a.status,
            user_id=a.user_id,
            conversation_id=a.conversation_id,
            expires_at=a.expires_at,
            created_at=a.created_at
        )
        for a in approvals
    ]


@router.post("/{approval_id}/decide", response_model=ApprovalDecisionResponse)
async def decide_approval(
    approval_id: str,
    request: ApprovalDecisionRequest,
    current_user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve or reject a pending action.

    If approved: executes the tool and returns result.
    If rejected: marks as rejected, user gets notified.
    """
    if request.decision not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be 'approved' or 'rejected'"
        )

    logger.info(
        f"Approval decision "
        f"id={approval_id} "
        f"decision={request.decision} "
        f"by={current_user.user_id}"
    )

    try:
        approval = await process_approval_decision(
            approval_id=approval_id,
            tenant_id=current_user.tenant_id,
            approved_by=current_user.user_id,
            decision=request.decision,
            note=request.note or "",
            db=db
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    # if approved execute the tool now
    tool_result = None
    if request.decision == "approved":
        try:
            tool_result = execute_builtin_tool(
                approval.tool_name,
                approval.tool_input or {}
            )
            logger.info(
                f"Tool executed after approval "
                f"tool={approval.tool_name} "
                f"result={tool_result}"
            )
        except Exception as e:
            logger.error(f"Tool execution failed after approval error={e}")
            tool_result = {"error": str(e)}

    return ApprovalDecisionResponse(
        id=approval.id,
        tool_name=approval.tool_name,
        status=approval.status,
        decision_at=approval.decision_at,
        decision_note=approval.decision_note,
        tool_result=tool_result
    )