from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from app.core.security import decode_access_token
from app.schemas.auth_schema import CurrentUser
from app.core.logger import get_logger

logger = get_logger(__name__)

# this tells FastAPI to look for a Bearer token in the Authorization header
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> CurrentUser:
    """
    Reads JWT token from request header.
    Returns current user info.
    Raises 401 if token is missing or invalid.
    """
    token = credentials.credentials

    try:
        payload = decode_access_token(token)
        user = CurrentUser(
            user_id=payload["user_id"],
            tenant_id=payload["tenant_id"],
            role=payload["role"]
        )
        return user
    except (JWTError, KeyError) as e:
        logger.warning(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


async def require_admin(
    current_user: CurrentUser = Depends(get_current_user)
) -> CurrentUser:
    """
    Same as get_current_user but also checks the user is an admin.
    Used for endpoints that only admins can access.
    """
    if current_user.role != "admin":
        logger.warning(f"Non-admin access attempt user_id={current_user.user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user