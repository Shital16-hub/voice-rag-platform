from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class TenantCreateRequest(BaseModel):
    name: str
    slug: str


class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    is_active: bool
    created_at: datetime


class AgentCreateRequest(BaseModel):
    name: str
    slug: str
    system_prompt: Optional[str] = None


class AgentResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    slug: str
    system_prompt: Optional[str]
    is_active: bool
    created_at: datetime


class UserCreateRequest(BaseModel):
    email: str
    password: str
    role: str = "user"


class UserResponse(BaseModel):
    id: str
    tenant_id: str
    email: str
    role: str
    is_active: bool
    created_at: datetime