"""Authentication endpoints — moteur V4.1.0.

Migré en M2 UNIFY SYSTEM depuis src/auth.py (legacy).
Tokens émis : V4.1.0 (HS256 · jti · role · type · 30 min).
Helpers DB legacy (authenticate_user, create_user) : src/api/auth_helpers.py.
ADR-M2-001.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field

from src.api.auth_helpers import authenticate_user, create_user, get_user_by_id
from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.couche_a.auth.jwt_handler import create_access_token
from src.ratelimit import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])


class Token(BaseModel):
    access_token: str
    token_type: str


class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: str | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: str | None = None
    role_name: str
    is_active: bool
    is_superuser: bool


@router.post("/token", response_model=Token)
@limiter.limit("5/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """Login — émet un token V4.1.0 (jti · role · 30 min)."""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _role_mapping = {
        "admin": "admin",
        "procurement_officer": "buyer",
        "viewer": "viewer",
    }
    role_raw = user.get("role_name", user.get("role", "viewer"))
    role = _role_mapping.get(role_raw, "viewer")
    access_token = create_access_token(str(user["id"]), role)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("3/hour")
async def register(request: Request, user_data: UserRegister):
    """Enregistre nouvel utilisateur (role_id=2 legacy — DETTE-M1-04)."""
    user = create_user(
        email=user_data.email,
        username=user_data.username,
        password=user_data.password,
        full_name=user_data.full_name,
        role_id=2,
    )
    return UserResponse(**user)


@router.get("/me", response_model=UserResponse)
@limiter.limit("60/minute")
async def get_me(
    request: Request,
    current_user: Annotated[UserClaims, Depends(get_current_user)],
):
    """Retourne le profil complet depuis la DB (rechargement — ADR-M2-001)."""
    user = get_user_by_id(int(current_user.user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable",
        )
    return UserResponse(**user)
