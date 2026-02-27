"""Fixtures auth — tests isolés du nouveau moteur V4.1.0.

Isolation : chaque test = transaction rollback via db_transaction.
Zéro données persistantes entre tests.
Zéro appel API réel (RÈGLE-21).
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import psycopg
import psycopg.rows
import pytest
from dotenv import load_dotenv

load_dotenv()

# SECRET_KEY obligatoire pour les tests
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!!")


# ── Connexion DB ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        pytest.skip("DATABASE_URL non défini")
    return url.replace("postgresql+psycopg://", "postgresql://")


@pytest.fixture
def db_conn(db_url):
    """Connexion autocommit pour tests nécessitant la persistance (ex: blacklist)."""
    conn = psycopg.connect(db_url, autocommit=True)
    yield conn
    conn.close()


@pytest.fixture
def db_transaction(db_url):
    """Connexion avec rollback automatique pour isolation totale."""
    conn = psycopg.connect(db_url, row_factory=psycopg.rows.dict_row)
    conn.autocommit = False
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


# ── Factories utilisateurs ────────────────────────────────────────────────────


def _make_user(conn: psycopg.Connection, role: str) -> dict:
    """Insère un utilisateur minimal dans users et retourne ses données."""
    uid = uuid.uuid4().hex[:8]
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            """
            INSERT INTO users (email, username, hashed_password, full_name,
                               is_active, is_superuser, role_id,
                               created_at, role)
            VALUES (%s, %s, %s, %s, TRUE, FALSE,
                    (SELECT id FROM roles WHERE name = 'admin' LIMIT 1),
                    now()::text, %s)
            RETURNING id, email, username, role
            """,
            (
                f"{role}_{uid}@test.dms",
                f"{role}_{uid}",
                "$2b$12$placeholder_hash_not_used_in_m1",
                f"Test {role.capitalize()} {uid}",
                role,
            ),
        )
        return dict(cur.fetchone())


@pytest.fixture
def user_admin_factory(db_transaction):
    return _make_user(db_transaction, "admin")


@pytest.fixture
def user_viewer_factory(db_transaction):
    return _make_user(db_transaction, "viewer")


@pytest.fixture
def user_buyer_factory(db_transaction):
    return _make_user(db_transaction, "buyer")


@pytest.fixture
def user_auditor_factory(db_transaction):
    return _make_user(db_transaction, "auditor")


# ── Factories tokens ──────────────────────────────────────────────────────────


@pytest.fixture
def valid_access_token(user_admin_factory):
    from src.couche_a.auth.jwt_handler import create_access_token

    user = user_admin_factory
    return create_access_token(str(user["id"]), user["role"])


@pytest.fixture
def expired_access_token():
    """Token expiré : exp = now - 1s."""
    import uuid as _uuid
    from datetime import datetime

    from jose import jwt

    secret = os.environ["SECRET_KEY"]
    now = datetime.now(UTC)
    claims = {
        "sub": "test-user-id",
        "role": "viewer",
        "jti": str(_uuid.uuid4()),
        "iat": now - timedelta(seconds=62),
        "exp": now - timedelta(seconds=1),
        "type": "access",
    }
    return jwt.encode(claims, secret, algorithm="HS256")


@pytest.fixture
def blacklisted_token(db_conn):
    """Token valide dont le jti est inscrit dans token_blacklist."""
    from src.couche_a.auth.jwt_handler import create_access_token, revoke_token

    token = create_access_token("blacklisted-user", "viewer")

    from jose import jwt as _jwt

    payload = _jwt.get_unverified_claims(token)
    jti = payload["jti"]
    expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)

    revoke_token(jti, expires_at, db_conn)
    yield token

    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM token_blacklist WHERE token_jti = %s", (jti,))
