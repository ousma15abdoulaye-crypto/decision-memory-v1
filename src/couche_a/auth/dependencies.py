"""Dépendances FastAPI — authentification et contrôle d'accès V4.1.0.

Nouveau moteur isolé — ne modifie pas src/auth.py (legacy).
ADR-M1-001 · ADR-M1-002.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import psycopg
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.couche_a.auth.jwt_handler import verify_token
from src.couche_a.auth.rbac import ROLES

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class UserClaims:
    """Claims extraits et validés d'un token JWT."""

    user_id: str
    role: str
    jti: str


def _get_db_conn() -> psycopg.Connection:
    """Fournit une connexion psycopg.

    À remplacer par injection de dépendance FastAPI réelle lors du
    raccordement du nouveau moteur aux endpoints (mandat post-M1).
    """
    import os

    from dotenv import load_dotenv

    load_dotenv()
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    return psycopg.connect(url, autocommit=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db_conn: psycopg.Connection = Depends(_get_db_conn),
) -> UserClaims:
    """Dépendance FastAPI : extrait et valide le JWT Bearer.

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

    try:
        payload = verify_token(credentials.credentials, "access", db_conn)
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

    return UserClaims(
        user_id=payload["sub"],
        role=role,
        jti=payload["jti"],
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
