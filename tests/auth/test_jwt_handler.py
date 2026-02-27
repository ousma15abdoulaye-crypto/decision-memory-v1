"""Tests jwt_handler — moteur JWT V4.1.0.

RÈGLE-07 : Assertions explicites.
RÈGLE-21 : Zéro appel API réel.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest
from jose import jwt as _jwt

from src.couche_a.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    rotate_refresh_token,
    verify_token,
)

# ── Émission ──────────────────────────────────────────────────────────────────


def test_access_token_claims(db_conn):
    """Token émis contient sub · role · jti · iat · exp · type."""
    token = create_access_token("user-123", "admin")
    payload = _jwt.get_unverified_claims(token)

    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"
    assert "jti" in payload
    assert "iat" in payload
    assert "exp" in payload
    assert payload["type"] == "access"


def test_refresh_token_type(db_conn):
    """Refresh token a type='refresh'."""
    token = create_refresh_token("user-456", "viewer")
    payload = _jwt.get_unverified_claims(token)

    assert payload["type"] == "refresh"
    assert payload["sub"] == "user-456"
    assert payload["role"] == "viewer"


def test_access_token_ttl(db_conn):
    """TTL access token = JWT_ACCESS_TTL_MINUTES (défaut 30 min)."""
    token = create_access_token("user-ttl", "buyer")
    payload = _jwt.get_unverified_claims(token)

    exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
    iat = datetime.fromtimestamp(payload["iat"], tz=UTC)
    delta = exp - iat

    expected_minutes = int(os.environ.get("JWT_ACCESS_TTL_MINUTES", 30))
    assert abs(delta.total_seconds() - expected_minutes * 60) < 5


# ── Validation ────────────────────────────────────────────────────────────────


def test_valid_token_verify(db_conn):
    """verify_token retourne le payload pour un token valide."""
    token = create_access_token("user-verify", "manager")
    payload = verify_token(token, "access", db_conn)

    assert payload["sub"] == "user-verify"
    assert payload["role"] == "manager"
    assert payload["type"] == "access"


def test_expired_token_raises(expired_access_token, db_conn):
    """Token expiré → ValueError."""
    with pytest.raises(ValueError, match="Token invalide"):
        verify_token(expired_access_token, "access", db_conn)


def test_invalid_signature_raises(db_conn):
    """Token signature invalide → ValueError."""
    token = create_access_token("user-sig", "viewer")
    tampered = token[:-4] + "XXXX"
    with pytest.raises(ValueError, match="Token invalide"):
        verify_token(tampered, "access", db_conn)


def test_blacklisted_token_raises(blacklisted_token, db_conn):
    """Token blacklisté → ValueError."""
    with pytest.raises(ValueError, match="révoqué"):
        verify_token(blacklisted_token, "access", db_conn)


def test_wrong_type_raises(db_conn):
    """Refresh token présenté comme access → ValueError."""
    token = create_refresh_token("user-type", "viewer")
    with pytest.raises(ValueError, match="Type de token incorrect"):
        verify_token(token, "access", db_conn)


# ── Rotation ─────────────────────────────────────────────────────────────────


def test_rotate_refresh_emits_new_tokens(db_conn):
    """Refresh valide → émet nouveau access + nouveau refresh."""
    refresh = create_refresh_token("user-rotate", "buyer")
    new_access, new_refresh = rotate_refresh_token(refresh, db_conn)

    old_jti = _jwt.get_unverified_claims(refresh)["jti"]
    new_access_payload = _jwt.get_unverified_claims(new_access)
    new_refresh_payload = _jwt.get_unverified_claims(new_refresh)

    assert new_access_payload["type"] == "access"
    assert new_refresh_payload["type"] == "refresh"
    assert new_access_payload["sub"] == "user-rotate"

    # JTIs différents de l'original
    assert new_access_payload["jti"] != old_jti
    assert new_refresh_payload["jti"] != old_jti

    # Cleanup
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM token_blacklist WHERE token_jti = %s", (old_jti,))


def test_rotate_blacklists_old_refresh_jti(db_conn):
    """Après rotation, l'ancien refresh jti est dans token_blacklist."""
    refresh = create_refresh_token("user-bl", "auditor")
    old_jti = _jwt.get_unverified_claims(refresh)["jti"]

    rotate_refresh_token(refresh, db_conn)

    with db_conn.cursor(
        row_factory=__import__("psycopg.rows", fromlist=["dict_row"]).dict_row
    ) as cur:
        cur.execute(
            "SELECT token_jti FROM token_blacklist WHERE token_jti = %s",
            (old_jti,),
        )
        row = cur.fetchone()

    assert row is not None
    assert row["token_jti"] == old_jti

    # Cleanup
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM token_blacklist WHERE token_jti = %s", (old_jti,))


def test_rotate_rejects_second_use(db_conn):
    """Refresh déjà utilisé (jti blacklisté) → ValueError à la 2e rotation."""
    refresh = create_refresh_token("user-reuse", "viewer")
    old_jti = _jwt.get_unverified_claims(refresh)["jti"]

    rotate_refresh_token(refresh, db_conn)

    with pytest.raises(ValueError, match="révoqué"):
        rotate_refresh_token(refresh, db_conn)

    # Cleanup
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM token_blacklist WHERE token_jti = %s", (old_jti,))


# ── Sécurité démarrage ────────────────────────────────────────────────────────


def test_secret_key_absent_raises_value_error(monkeypatch):
    """SECRET_KEY absent de l'ENV → ValueError au démarrage."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)

    import src.couche_a.auth.jwt_handler as mod

    with pytest.raises(ValueError, match="SECRET_KEY absent"):
        mod._secret_key()
