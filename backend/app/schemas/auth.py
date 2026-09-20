from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """What the user sends when logging in."""
    email: str
    password: str


class TokenResponse(BaseModel):
    """What we send back after successful login."""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    tenant_id: str
    role: str


class CurrentUser(BaseModel):
    """Represents the logged in user extracted from JWT token."""
    user_id: str
    tenant_id: str
    role: str