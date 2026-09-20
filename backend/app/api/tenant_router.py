from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import require_admin, get_current_user
from app.schemas.auth_schema import CurrentUser
from app.schemas.tenant_schema import (
    TenantCreateRequest, TenantResponse,
    AgentCreateRequest, AgentResponse,
    UserCreateRequest, UserResponse
)
from app.services.tenant_service import (
    create_tenant, create_agent,
    create_user, get_all_tenants,
    get_tenant_agents
)
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantResponse)
async def create_new_tenant(
    request: TenantCreateRequest,
    current_user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new tenant. Admin only."""
    try:
        tenant = await create_tenant(
            name=request.name,
            slug=request.slug,
            db=db
        )
        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            is_active=tenant.is_active,
            created_at=tenant.created_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=list[TenantResponse])
async def list_tenants(
    current_user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all tenants. Admin only."""
    tenants = await get_all_tenants(db)
    return [
        TenantResponse(
            id=t.id,
            name=t.name,
            slug=t.slug,
            is_active=t.is_active,
            created_at=t.created_at
        )
        for t in tenants
    ]


@router.post("/{tenant_id}/agents", response_model=AgentResponse)
async def create_new_agent(
    tenant_id: str,
    request: AgentCreateRequest,
    current_user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new agent for a tenant.
    Admin can only create agents for their own tenant.
    """
    # ensure admin can only create agents for their own tenant
    if current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create agents for another tenant"
        )

    agent = await create_agent(
        tenant_id=tenant_id,
        name=request.name,
        slug=request.slug,
        system_prompt=request.system_prompt or "",
        db=db
    )
    return AgentResponse(
        id=agent.id,
        tenant_id=agent.tenant_id,
        name=agent.name,
        slug=agent.slug,
        system_prompt=agent.system_prompt,
        is_active=agent.is_active,
        created_at=agent.created_at
    )


@router.get("/{tenant_id}/agents", response_model=list[AgentResponse])
async def list_agents(
    tenant_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all agents for a tenant."""
    if current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view agents for another tenant"
        )

    agents = await get_tenant_agents(tenant_id, db)
    return [
        AgentResponse(
            id=a.id,
            tenant_id=a.tenant_id,
            name=a.name,
            slug=a.slug,
            system_prompt=a.system_prompt,
            is_active=a.is_active,
            created_at=a.created_at
        )
        for a in agents
    ]


@router.post("/{tenant_id}/users", response_model=UserResponse)
async def create_new_user(
    tenant_id: str,
    request: UserCreateRequest,
    current_user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new user for a tenant. Admin only."""
    if current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create users for another tenant"
        )

    try:
        user = await create_user(
            tenant_id=tenant_id,
            email=request.email,
            password=request.password,
            role=request.role,
            db=db
        )
        return UserResponse(
            id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )