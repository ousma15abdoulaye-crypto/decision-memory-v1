"""Tests token_blacklist — révocation JWT + fn_cleanup_expired_tokens().

RÈGLE-07 : assertions explicites.
RÈGLE-21 : zéro appel API réel.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import psycopg
import psycopg.rows
import pytest

from src.couche_a.auth.jwt_handler import (
    create_access_token,
    revoke_token,
    verify_token,
)

# ── Révocation ────────────────────────────────────────────────────────────────


def test_jti_revoque_bloque_get_current_user(db_conn):
    """jti révoqué en DB → verify_token lève ValueError."""
    token = create_access_token("user-rev", "viewer")
    from jose import jwt as _jwt

    payload = _jwt.get_unverified_claims(token)
    jti = payload["jti"]
    expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)

    revoke_token(jti, expires_at, db_conn)

    with pytest.raises(ValueError, match="révoqué"):
        verify_token(token, "access", db_conn)

    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM token_blacklist WHERE token_jti = %s", (jti,))


def test_jti_non_revoque_retourne_user(db_conn):
    """jti absent de token_blacklist → verify_token retourne le payload."""
    token = create_access_token("user-ok", "manager")
    payload = verify_token(token, "access", db_conn)

    assert payload["sub"] == "user-ok"
    assert payload["role"] == "manager"


# ── fn_cleanup_expired_tokens ─────────────────────────────────────────────────


def test_cleanup_supprime_expires_passes(db_conn):
    """fn_cleanup_expired_tokens() supprime les tokens avec expires_at < now()."""
    jti_expired = f"expired-{uuid.uuid4()}"
    jti_valid = f"valid-{uuid.uuid4()}"

    past = datetime.now(UTC) - timedelta(hours=1)
    future = datetime.now(UTC) + timedelta(hours=1)

    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO token_blacklist (token_jti, expires_at) VALUES (%s, %s)",
            (jti_expired, past),
        )
        cur.execute(
            "INSERT INTO token_blacklist (token_jti, expires_at) VALUES (%s, %s)",
            (jti_valid, future),
        )

    with db_conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute("SELECT fn_cleanup_expired_tokens()")
        result = cur.fetchone()
        deleted = result["fn_cleanup_expired_tokens"]

    assert deleted >= 1

    with db_conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            "SELECT token_jti FROM token_blacklist WHERE token_jti = %s",
            (jti_expired,),
        )
        assert cur.fetchone() is None

    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM token_blacklist WHERE token_jti = %s", (jti_valid,))


def test_cleanup_conserve_expires_futurs(db_conn):
    """fn_cleanup_expired_tokens() conserve les tokens expires_at > now()."""
    jti_future = f"future-{uuid.uuid4()}"
    future = datetime.now(UTC) + timedelta(hours=2)

    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO token_blacklist (token_jti, expires_at) VALUES (%s, %s)",
            (jti_future, future),
        )

    with db_conn.cursor() as cur:
        cur.execute("SELECT fn_cleanup_expired_tokens()")

    with db_conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            "SELECT token_jti FROM token_blacklist WHERE token_jti = %s",
            (jti_future,),
        )
        row = cur.fetchone()

    assert row is not None
    assert row["token_jti"] == jti_future

    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM token_blacklist WHERE token_jti = %s", (jti_future,))


# ── Contrainte UNIQUE ─────────────────────────────────────────────────────────


def test_unique_constraint_jti_double_revocation(db_conn):
    """Double révocation du même jti → IntegrityError (UNIQUE violation)."""
    jti = f"dup-{uuid.uuid4()}"
    future = datetime.now(UTC) + timedelta(hours=1)

    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO token_blacklist (token_jti, expires_at) VALUES (%s, %s)",
            (jti, future),
        )

    with pytest.raises(psycopg.errors.UniqueViolation):
        with db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO token_blacklist (token_jti, expires_at) VALUES (%s, %s)",
                (jti, future),
            )

    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM token_blacklist WHERE token_jti = %s", (jti,))


def test_revoke_token_idempotent(db_conn):
    """revoke_token() avec ON CONFLICT DO NOTHING — pas d'erreur sur double appel."""
    token = create_access_token("user-idem", "viewer")
    from jose import jwt as _jwt

    payload = _jwt.get_unverified_claims(token)
    jti = payload["jti"]
    expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)

    revoke_token(jti, expires_at, db_conn)
    revoke_token(jti, expires_at, db_conn)  # pas d'exception

    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM token_blacklist WHERE token_jti = %s", (jti,))
