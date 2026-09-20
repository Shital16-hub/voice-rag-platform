from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import User, Tenant
from app.core.security import verify_password, create_access_token
from app.core.logger import get_logger

logger = get_logger(__name__)


async def login_user(email: str, password: str, db: AsyncSession):
    """
    Check credentials and return a token if correct.
    
    Steps:
    1. Find user by email
    2. Check password
    3. Check tenant is active
    4. Create and return token
    """
    logger.info(f"Login attempt for email={email}")

    # Step 1: find user by email
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"Login failed - user not found email={email}")
        return None

    # Step 2: check password
    if not verify_password(password, user.hashed_password):
        logger.warning(f"Login failed - wrong password email={email}")
        return None

    # Step 3: check user is active
    if not user.is_active:
        logger.warning(f"Login failed - user inactive email={email}")
        return None

    # Step 4: create token with user info inside
    token = create_access_token({
        "user_id": user.id,
        "tenant_id": user.tenant_id,
        "role": user.role
    })

    logger.info(f"Login successful user_id={user.id} tenant_id={user.tenant_id}")
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "tenant_id": user.tenant_id,
        "role": user.role
    }