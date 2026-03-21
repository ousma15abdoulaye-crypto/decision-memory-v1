"""JWT Handler — moteur V4.1.0.

Isolé du legacy src/auth.py.
Pas d'endpoints ici : utilitaires uniquement.
ADR-M1-001.

Claims obligatoires : sub · role · jti · iat · exp · type
Algorithme : HS256
Access TTL  : JWT_ACCESS_TTL_MINUTES (défaut 30)
Refresh TTL : JWT_REFRESH_TTL_DAYS   (défaut 7)
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
from jose import JWTError, jwt

VALID_ROLES = frozenset({"admin", "manager", "buyer", "viewer", "auditor"})


def _secret_key() -> str:
    key = os.environ.get("SECRET_KEY") or os.environ.get("JWT_SECRET")
    if not key:
        raise ValueError(
            "SECRET_KEY absent de l'environnement. "
            "Définir SECRET_KEY avant de démarrer l'application."
        )
    return key


def _access_ttl() -> int:
    return int(os.environ.get("JWT_ACCESS_TTL_MINUTES", 30))


def _refresh_ttl() -> int:
    return int(os.environ.get("JWT_REFRESH_TTL_DAYS", 7))


ALGORITHM = "HS256"


def _build_claims(
    user_id: str,
    role: str,
    token_type: str,
    expires_delta: timedelta,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + expires_delta,
        "type": token_type,
    }
    if tenant_id is not None:
        claims["tenant_id"] = str(tenant_id)
    return claims


def _validate_role(role: str) -> None:
    if role not in VALID_ROLES:
        raise ValueError(
            f"Rôle invalide : '{role}'. " f"Valeurs acceptées : {sorted(VALID_ROLES)}"
        )


def create_access_token(user_id: str, role: str, tenant_id: str | None = None) -> str:
    """Émet un access token signé HS256.

    Raises:
        ValueError: rôle non reconnu ou SECRET_KEY absent.
    """
    _validate_role(role)
    claims = _build_claims(
        user_id, role, "access", timedelta(minutes=_access_ttl()), tenant_id
    )
    return jwt.encode(claims, _secret_key(), algorithm=ALGORITHM)


def create_refresh_token(user_id: str, role: str, tenant_id: str | None = None) -> str:
    """Émet un refresh token signé HS256.

    Raises:
        ValueError: rôle non reconnu ou SECRET_KEY absent.
    """
    _validate_role(role)
    claims = _build_claims(
        user_id, role, "refresh", timedelta(days=_refresh_ttl()), tenant_id
    )
    return jwt.encode(claims, _secret_key(), algorithm=ALGORITHM)


def verify_token(
    token: str,
    expected_type: str,
    db_conn: psycopg.Connection,
) -> dict[str, Any]:
    """Valide un token JWT.

    Vérifie : signature, expiration, type, jti absent de token_blacklist.

    Raises:
        ValueError: token invalide, expiré, mauvais type ou blacklisté.
    """
    try:
        payload = jwt.decode(token, _secret_key(), algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError(f"Token invalide : {exc}") from exc

    if payload.get("type") != expected_type:
        raise ValueError(
            f"Type de token incorrect : attendu '{expected_type}', "
            f"reçu '{payload.get('type')}'"
        )

    jti = payload.get("jti")
    if not jti:
        raise ValueError("Token sans jti — rejeté")

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM token_blacklist WHERE token_jti = %s",
            (jti,),
        )
        if cur.fetchone():
            raise ValueError("Token révoqué (jti blacklisté)")

    return payload


def revoke_token(
    jti: str,
    expires_at: datetime,
    db_conn: psycopg.Connection,
) -> None:
    """Inscrit un jti dans token_blacklist.

    Idempotent : si le jti est déjà présent, ne lève pas d'erreur.
    """
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO token_blacklist (token_jti, expires_at)
            VALUES (%s, %s)
            ON CONFLICT (token_jti) DO NOTHING
            """,
            (jti, expires_at),
        )


def rotate_refresh_token(
    refresh_token: str,
    db_conn: psycopg.Connection,
) -> tuple[str, str]:
    """Rotation d'un refresh token.

    Valide le refresh token, révoque son jti, émet nouveau access + refresh.

    Returns:
        (new_access_token, new_refresh_token)

    Raises:
        ValueError: refresh token invalide, expiré ou déjà révoqué.
    """
    payload = verify_token(refresh_token, "refresh", db_conn)

    exp_ts = payload["exp"]
    if isinstance(exp_ts, int | float):
        expires_at = datetime.fromtimestamp(exp_ts, tz=UTC)
    else:
        expires_at = exp_ts

    revoke_token(payload["jti"], expires_at, db_conn)

    user_id = payload["sub"]
    role = payload["role"]
    tid = payload.get("tenant_id")
    if not tid:
        tid = None
        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            uid = None
        if uid is not None:
            with db_conn.cursor() as cur:
                cur.execute(
                    "SELECT tenant_id FROM user_tenants WHERE user_id = %s",
                    (uid,),
                )
                r = cur.fetchone()
            tid = r[0] if r else None
        if not tid:
            tid = f"tenant-{user_id}"
    else:
        tid = str(tid)
    new_access = create_access_token(user_id, role, tid)
    new_refresh = create_refresh_token(user_id, role, tid)
    return new_access, new_refresh
