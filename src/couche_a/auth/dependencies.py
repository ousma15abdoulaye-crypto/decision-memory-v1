"""Dépendances FastAPI — authentification et contrôle d'accès V4.1.0.

Nouveau moteur isolé — ne modifie pas src/auth.py (legacy).
ADR-M1-001 · ADR-M1-002.
"""

from __future__ import annotations

import os
import uuid as _uuid
from collections.abc import Callable
from dataclasses import dataclass

import psycopg
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.couche_a.auth.jwt_handler import verify_token
from src.couche_a.auth.rbac import ROLES
from src.db.tenant_context import set_db_tenant_id, set_rls_is_admin

_bearer_scheme = HTTPBearer(auto_error=False)

# Cache module : évite un SELECT ``tenants`` par requête pour les JWT legacy.
# Invalidé si la valeur n’est pas un UUID valide.
_default_tenant_uuid_cache: str | None = None


def _default_tenant_code() -> str:
    """Code métier dans ``tenants.code`` (surcharge : ``DEFAULT_TENANT_CODE``)."""
    code = (os.environ.get("DEFAULT_TENANT_CODE") or "sci_mali").strip()
    return code or "sci_mali"


def _resolve_tenant_uuid_for_rls(
    tenant_id: str | None, db_conn: psycopg.Connection
) -> str | None:
    """Aligne tenant_id JWT / user_tenants sur l'UUID réel dans ``tenants``.

    Les lignes legacy ``user_tenants`` portent encore ``tenant-<user_id>`` (TEXT).
    Les tables V4.2.0 (``process_workspaces``, etc.) attendent ``tenants.id`` (UUID).
    Sans résolution, INSERT échoue (cast UUID) ou viole la FK.

    Ne renvoie jamais une chaîne non-UUID : sinon ``set_config(..., ::uuid)`` / RLS échouent.
    """
    global _default_tenant_uuid_cache

    if not tenant_id:
        return None
    s = str(tenant_id).strip()
    try:
        _uuid.UUID(s)
        return s
    except ValueError:
        pass

    if _default_tenant_uuid_cache:
        try:
            _uuid.UUID(_default_tenant_uuid_cache)
            return _default_tenant_uuid_cache
        except ValueError:
            _default_tenant_uuid_cache = None

    code = _default_tenant_code()
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT id::text FROM tenants WHERE code = %s LIMIT 1",
            (code,),
        )
        row = cur.fetchone()
    if not row or not row[0]:
        return None
    resolved = str(row[0]).strip()
    try:
        _uuid.UUID(resolved)
    except ValueError:
        return None
    _default_tenant_uuid_cache = resolved
    return resolved


@dataclass(frozen=True)
class UserClaims:
    """Claims extraits et validés d'un token JWT."""

    user_id: str
    role: str
    jti: str
    tenant_id: str | None = None
    is_superuser: bool = False


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> UserClaims:
    """Dépendance FastAPI : extrait et valide le JWT Bearer.

    Aucune connexion DB n'est ouverte si le Bearer est absent (évite un
    ``psycopg.connect`` inutile sur les 401 « token manquant »).

    Raises:
        HTTPException 401: token absent, invalide, expiré ou révoqué.
        HTTPException 401: rôle non reconnu.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'authentification manquant",
            headers={"WWW-Authenticate": "Bearer"},
        )

    load_dotenv()
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(url, autocommit=True)
    try:
        try:
            payload = verify_token(credentials.credentials, "access", conn)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        role = payload.get("role", "")
        if role not in ROLES:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Rôle non reconnu : '{role}'",
                headers={"WWW-Authenticate": "Bearer"},
            )

        tid = payload.get("tenant_id")
        if not tid:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT tenant_id FROM user_tenants WHERE user_id = %s",
                    (int(payload["sub"]),),
                )
                r = cur.fetchone()
            tid = r[0] if r else None
        else:
            tid = str(tid)

        tid = _resolve_tenant_uuid_for_rls(tid, conn)

        set_db_tenant_id(tid)
        set_rls_is_admin(role == "admin")

        return UserClaims(
            user_id=payload["sub"],
            role=role,
            jti=payload["jti"],
            tenant_id=tid,
        )
    finally:
        conn.close()


def get_current_user_from_token(token: str) -> UserClaims:
    """Valide un token JWT brut (hors contexte FastAPI dependency).

    Utilisé par les handlers WebSocket qui reçoivent le token en query param.
    Ne peut pas vérifier la révocation (pas de connexion DB fournie).

    Raises:
        ValueError: token absent, invalide ou expiré.
    """
    import os

    import psycopg
    from dotenv import load_dotenv

    if not token:
        raise ValueError("Token manquant.")

    load_dotenv()
    url = os.environ.get("DATABASE_URL", "").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    conn = psycopg.connect(url, autocommit=True)
    try:
        payload = verify_token(token, "access", conn)
    finally:
        conn.close()

    role = payload.get("role", "")
    if role not in ROLES:
        raise ValueError(f"Rôle non reconnu : '{role}'.")

    return UserClaims(
        user_id=payload["sub"],
        role=role,
        jti=payload["jti"],
        tenant_id=str(payload.get("tenant_id") or ""),
        is_superuser=(role == "admin"),
    )


def require_role(*roles: str) -> Callable:
    """Retourne une dépendance FastAPI qui exige un rôle parmi la liste.

    Raises:
        HTTPException 403: rôle de l'utilisateur non autorisé.
    """
    allowed = frozenset(roles)

    def _check(current_user: UserClaims = Depends(get_current_user)) -> UserClaims:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Accès refusé. Rôles autorisés : {sorted(allowed)}. "
                    f"Rôle actuel : '{current_user.role}'"
                ),
            )
        return current_user

    return _check


def require_any_role(*roles: str) -> Callable:
    """Alias explicite de require_role avec logique OR.

    Identique à require_role — nommé séparément pour la lisibilité
    dans les endpoints qui acceptent plusieurs rôles de natures différentes.
    """
    return require_role(*roles)
