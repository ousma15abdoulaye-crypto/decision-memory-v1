"""Routes JSON ``/api/auth/*`` pour frontend-v51 (isolé de ``auth_router``).

Préfixe : ``/api/auth`` — enregistrer via ``app.include_router`` **sans** prefix additionnel.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.api.auth_helpers import authenticate_user, resolve_tenant_uuid_for_jwt
from src.couche_a.auth.jwt_handler import create_access_token, create_refresh_token
from src.ratelimit import limiter

router = APIRouter(prefix="/api/auth", tags=["auth-v2"])

_ROLE_MAPPING = {
    "admin": "admin",
    "procurement_officer": "buyer",
    "viewer": "viewer",
}


class LoginRequest(BaseModel):
    """Champ ``email`` : adresse ou nom d'utilisateur."""

    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginUserOut(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    role: str
    tenant_id: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: LoginUserOut


def _jwt_role_from_user(user: dict) -> str:
    role_raw = user.get("role_name", user.get("role", "viewer"))
    return _ROLE_MAPPING.get(role_raw, "viewer")


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login_json(request: Request, body: LoginRequest):
    """Login JSON — ``POST /api/auth/login`` (contrat frontend-v51)."""
    user = authenticate_user(body.email.strip(), body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = _jwt_role_from_user(user)
    tenant_id = resolve_tenant_uuid_for_jwt(int(user["id"]))
    uid = str(user["id"])
    try:
        access_token = create_access_token(uid, role, tenant_id)
        refresh_token = create_refresh_token(uid, role, tenant_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=LoginUserOut(
            id=int(user["id"]),
            email=str(user["email"]),
            username=str(user["username"]),
            full_name=str(user.get("full_name") or ""),
            role=role,
            tenant_id=tenant_id,
        ),
    )
