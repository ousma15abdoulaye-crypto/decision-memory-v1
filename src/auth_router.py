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

from src.api.auth_helpers import (
    authenticate_user,
    create_user,
    get_tenant_id_for_user,
    get_user_by_id,
)
from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.couche_a.auth.jwt_handler import create_access_token
from src.db import db_execute_one, get_connection
from src.ratelimit import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])

_ROLE_MAPPING = {
    # Legacy V4.x roles → V4.1.0 JWT roles
    "admin": "admin",
    "procurement_officer": "buyer",
    "viewer": "viewer",
    # V5.2 roles — pass through directly (src/auth/permissions.py ROLE_PERMISSIONS)
    "supply_chain": "supply_chain",
    "finance": "finance",
    "technical": "technical",
    "budget_holder": "budget_holder",
    "observer": "observer",
}


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
    tenant_id: str | None = None


class LoginJsonRequest(BaseModel):
    """Identifiant = email **ou** username (même champ que le formulaire Next)."""

    email: str = Field(..., min_length=1, description="Email ou nom d'utilisateur")
    password: str = Field(..., min_length=1)


class LoginJsonResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None


def _tenant_for_jwt(user: dict) -> str:
    with get_connection() as conn:
        trow = db_execute_one(
            conn,
            "SELECT tenant_id FROM user_tenants WHERE user_id = :id",
            {"id": user["id"]},
        )
    return trow["tenant_id"] if trow else f"tenant-{user['id']}"


def _issue_access_token(user: dict) -> str:
    role_raw = user.get("role_name", user.get("role", "viewer"))
    role = _ROLE_MAPPING.get(role_raw, "viewer")
    tenant_id = _tenant_for_jwt(user)
    return create_access_token(str(user["id"]), role, tenant_id)


def _user_to_response(user: dict) -> UserResponse:
    return UserResponse(
        id=user["id"],
        email=user["email"],
        username=user["username"],
        full_name=user.get("full_name"),
        role_name=user["role_name"],
        is_active=user["is_active"],
        is_superuser=user["is_superuser"],
        tenant_id=get_tenant_id_for_user(user["id"]),
    )


def _unauthorized_login() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/token", response_model=Token)
@limiter.limit("5/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """Login — émet un token V4.1.0 (jti · role · 30 min)."""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise _unauthorized_login()
    try:
        access_token = _issue_access_token(user)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=LoginJsonResponse)
@limiter.limit("5/minute")
async def login_json(request: Request, body: LoginJsonRequest):
    """Login JSON — contrat frontend-v51 (user + access_token). Pas de refresh_token (phase 1)."""
    user = authenticate_user(body.email.strip(), body.password)
    if not user:
        raise _unauthorized_login()
    try:
        access_token = _issue_access_token(user)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return LoginJsonResponse(
        user=_user_to_response(user),
        access_token=access_token,
        token_type="bearer",
        refresh_token=None,
    )


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
    return _user_to_response(user)


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
    return _user_to_response(user)
