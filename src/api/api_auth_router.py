"""Routes JSON ``/api/auth/*`` pour frontend-v51 (isolé de ``auth_router``).

Préfixe : ``/api/auth`` — enregistrer via ``app.include_router`` **sans** prefix additionnel.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from src.api.auth_helpers import (
    authenticate_user,
    jwt_role_for_user_row,
    resolve_tenant_uuid_for_jwt,
)
from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.couche_a.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    create_ws_token,
)
from src.ratelimit import limiter

router = APIRouter(prefix="/api/auth", tags=["auth-v2"])
logger = logging.getLogger(__name__)


async def get_login_credentials(request: Request) -> tuple[str, str]:
    """Lit identifiant + mot de passe depuis JSON, form-urlencoded ou multipart.

    Évite les 422 « opaques » de Pydantic quand le client n'envoie pas exactement
    ``application/json`` + champs ``email``/``username`` et ``password``.
    """
    ct_header = request.headers.get("content-type") or ""
    ct_lower = ct_header.lower()

    login_id = ""
    password = ""
    raw: bytes = b""

    if "multipart/form-data" in ct_lower:
        form = await request.form()
        login_id = str(form.get("email") or form.get("username") or "").strip()
        pw = form.get("password")
        password = str(pw).strip() if pw is not None else ""
    else:
        raw = await request.body()
        if not raw.strip():
            logger.warning(
                "api_auth login: empty body content_type=%r",
                ct_header,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Corps de requête vide.",
            )

        if "application/x-www-form-urlencoded" in ct_lower:
            try:
                txt = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Encodage du corps invalide: {exc}",
                ) from exc
            pairs = dict(parse_qsl(txt, keep_blank_values=True))
            login_id = (pairs.get("email") or pairs.get("username") or "").strip()
            password = (pairs.get("password") or "").strip()
        else:
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"JSON invalide: {exc}",
                ) from exc
            if not isinstance(payload, dict):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Le corps JSON doit être un objet.",
                )
            e = payload.get("email")
            u = payload.get("username")
            login_id = (e.strip() if isinstance(e, str) else "") or (
                u.strip() if isinstance(u, str) else ""
            )
            pw = payload.get("password")
            password = pw.strip() if isinstance(pw, str) else ""

    if not login_id or not password:
        logger.warning(
            "api_auth login: missing credentials "
            "(login_id empty=%s password empty=%s) content_type=%r body_prefix=%r",
            not login_id,
            not password,
            ct_header,
            raw[:120] if raw else b"",
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Identifiant (champ « email » ou « username ») et « password » "
                "requis, non vides."
            ),
        )

    return login_id, password


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


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login_json(
    request: Request,
    creds: Annotated[tuple[str, str], Depends(get_login_credentials)],
):
    """Login — ``POST /api/auth/login`` (JSON, form-urlencoded ou multipart)."""
    login_id, password = creds
    user = authenticate_user(login_id, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = jwt_role_for_user_row(user)
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


class WsTokenResponse(BaseModel):
    token: str


@router.post("/ws-token", response_model=WsTokenResponse)
@limiter.limit("20/minute")
async def get_ws_token(
    request: Request,
    current_user: Annotated[UserClaims, Depends(get_current_user)],
) -> WsTokenResponse:
    """Émet un token WebSocket longue durée (type='ws', TTL 24 h).

    Requiert un Bearer access token valide. Retourne un JWT dédié aux
    connexions WebSocket, évitant les déconnexions dues à l'expiration
    du token d'accès standard (30 min).
    """
    try:
        ws_token = create_ws_token(
            current_user.user_id,
            current_user.role,
            current_user.tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return WsTokenResponse(token=ws_token)
