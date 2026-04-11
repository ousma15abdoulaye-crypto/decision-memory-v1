"""Dépendances FastAPI — authentification et contrôle d'accès V4.1.0.

Nouveau moteur isolé — ne modifie pas src/auth.py (legacy).
ADR-M1-001 · ADR-M1-002.
"""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Callable
from dataclasses import dataclass

import psycopg
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.couche_a.auth.jwt_handler import verify_token
from src.couche_a.auth.rbac import ROLES
from src.db.tenant_context import set_db_tenant_id, set_rls_is_admin, set_rls_user_id

_bearer_scheme = HTTPBearer(auto_error=False)

# Cache module : évite un SELECT ``tenants`` par requête pour les JWT legacy.
# Invalidé si la valeur n’est pas un UUID valide.
_default_tenant_uuid_cache: str | None = None


def _default_tenant_code() -> str:
    """Code métier dans ``tenants.code`` (surcharge : ``DEFAULT_TENANT_CODE``)."""
    from src.core.config import get_settings

    code = get_settings().DEFAULT_TENANT_CODE.strip()
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

    from src.core.config import get_settings

    database_url = get_settings().DATABASE_URL
    if not database_url or not str(database_url).strip():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration invalide : DATABASE_URL n'est pas définie",
        )
    url = str(database_url).replace("postgresql+psycopg://", "postgresql://")
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
    Aligné sur ``get_current_user`` : résolution ``tenant_id`` → UUID RLS
    (``_resolve_tenant_uuid_for_rls``) et pose du contexte
    ``set_db_tenant_id`` / ``set_rls_is_admin`` / ``set_rls_user_id`` pour que
    ``get_connection()`` applique les mêmes GUC que les routes HTTP.

    Sans cette étape, un JWT legacy ``tenant-<id>`` provoque un 403 WebSocket
    (« workspace appartient à un autre tenant ») alors que les GET HTTP passent.

    Raises:
        ValueError: token absent, invalide ou expiré.
    """
    if not token:
        raise ValueError("Token manquant.")

    from src.core.config import get_settings

    database_url = get_settings().DATABASE_URL
    if not database_url or not str(database_url).strip():
        raise ValueError("Configuration invalide : DATABASE_URL n'est pas définie.")
    url = str(database_url).replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(url, autocommit=True)
    try:
        try:
            payload = verify_token(token, "access", conn)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        role = payload.get("role", "")
        if role not in ROLES:
            raise ValueError(f"Rôle non reconnu : '{role}'.")

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
        set_rls_user_id(str(payload.get("sub") or ""))

        return UserClaims(
            user_id=payload["sub"],
            role=role,
            jti=payload["jti"],
            tenant_id=tid,
            is_superuser=(role == "admin"),
        )
    finally:
        conn.close()


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
