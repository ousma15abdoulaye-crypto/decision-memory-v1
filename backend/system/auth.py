"""JWT authentication and authorization utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from backend.system.settings import get_settings

__all__ = [
    "auth_router",
    "create_access_token",
    "get_current_user",
    "require_role",
    "UserPayload",
]

ROLES = {"buyer", "committee", "admin"}

security = HTTPBearer()


# ---- Models ----------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    role: str = "buyer"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserPayload(BaseModel):
    id: str
    username: str
    role: str


# ---- Token helpers ----------------------------------------------------------

def create_access_token(data: dict) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode = {**data, "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# ---- Dependencies -----------------------------------------------------------

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> UserPayload:
    payload = _decode_token(credentials.credentials)
    return UserPayload(
        id=payload.get("sub", ""),
        username=payload.get("username", ""),
        role=payload.get("role", "buyer"),
    )


def require_role(roles: list[str]):
    """Dependency factory – ensures current user has one of *roles*."""

    async def _check(user: Annotated[UserPayload, Depends(get_current_user)]) -> UserPayload:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' not in allowed roles {roles}",
            )
        return user

    return _check


# ---- Router (mock login) ---------------------------------------------------

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


@auth_router.post("/login", response_model=TokenResponse)
async def mock_login(body: LoginRequest):
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Choose from {ROLES}")
    import uuid

    user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, body.username))
    token = create_access_token({"sub": user_id, "username": body.username, "role": body.role})
    return TokenResponse(access_token=token)
