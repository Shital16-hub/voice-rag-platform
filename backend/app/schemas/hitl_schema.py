from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ApprovalRequestResponse(BaseModel):
    id: str
    tool_name: str
    tool_input: dict
    status: str
    user_id: str
    conversation_id: Optional[str]
    expires_at: Optional[datetime]
    created_at: datetime


class ApprovalDecisionRequest(BaseModel):
    decision: str  # approved or rejected
    note: Optional[str] = ""


class ApprovalDecisionResponse(BaseModel):
    id: str
    tool_name: str
    status: str
    decision_at: Optional[datetime]
    decision_note: Optional[str]
    tool_result: Optional[dict] = None