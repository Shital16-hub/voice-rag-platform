from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.dependencies import require_admin, get_current_user
from app.schemas.auth_schema import CurrentUser
from app.models.models import User
from app.core.security import hash_password
from pydantic import BaseModel
from typing import Optional
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


class CreateUserRequest(BaseModel):
    email: str
    password: str
    role: str = "user"


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    tenant_id: str


@router.post("", response_model=UserResponse)
async def create_user(
    request: CreateUserRequest,
    current_user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user for the admin's tenant.
    Admin only. Tenant isolation enforced via JWT.
    """
    # check email not already taken in this tenant
    result = await db.execute(
        select(User).where(
            User.email == request.email,
            User.tenant_id == current_user.tenant_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

    if request.role not in ["admin", "user"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be admin or user"
        )

    user = User(
        tenant_id=current_user.tenant_id,
        email=request.email,
        hashed_password=hash_password(request.password),
        role=request.role,
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(
        f"User created "
        f"email={request.email} "
        f"role={request.role} "
        f"tenant_id={current_user.tenant_id}"
    )

    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        tenant_id=user.tenant_id
    )


@router.get("", response_model=list[UserResponse])
async def list_users(
    current_user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List all users in admin's tenant.
    Admin only.
    """
    result = await db.execute(
        select(User).where(
            User.tenant_id == current_user.tenant_id
        ).order_by(User.created_at)
    )
    users = result.scalars().all()

    logger.info(
        f"Listed {len(users)} users "
        f"tenant_id={current_user.tenant_id}"
    )

    return [
        UserResponse(
            id=u.id,
            email=u.email,
            role=u.role,
            is_active=u.is_active,
            tenant_id=u.tenant_id
        )
        for u in users
    ]


@router.patch("/{user_id}/toggle")
async def toggle_user(
    user_id: str,
    current_user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Enable or disable a user.
    Admin cannot disable themselves.
    """
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own account"
        )

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_active = not user.is_active
    await db.commit()

    action = "enabled" if user.is_active else "disabled"
    logger.info(f"User {action} user_id={user_id}")

    return {"id": user.id, "is_active": user.is_active}