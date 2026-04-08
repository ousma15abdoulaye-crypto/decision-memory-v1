"""Helpers DB authentification — extraits de src/auth.py (legacy).

Déplacés ici lors de M2 UNIFY SYSTEM pour permettre la suppression
de src/auth.py sans perte de logique métier.

Contrat : zéro modification de la logique.
  - authenticate_user   : bcrypt + DB + last_login update
  - create_user         : INSERT users + user_tenants (role_id legacy, DETTE-M1-04)
  - get_user_by_username / get_user_by_id : SELECT users JOIN roles
  - verify_password / get_password_hash : helpers passlib/bcrypt

Note DETTE-M1-04 : create_user utilise role_id INTEGER (legacy).
  DROP COLUMN role_id reporté à M2B (schéma inchangé en M2).
"""

from datetime import datetime

import bcrypt as _bcrypt
from fastapi import HTTPException

from src.db import db_execute, db_execute_one, get_connection


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash — uses bcrypt directly (passlib-free)."""
    try:
        return _bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash password with bcrypt — uses bcrypt directly (passlib-free)."""
    return _bcrypt.hashpw(
        password.encode("utf-8"),
        _bcrypt.gensalt(rounds=12),
    ).decode("utf-8")


def get_user_by_username(username: str) -> dict | None:
    with get_connection() as conn:
        return db_execute_one(
            conn,
            """
            SELECT u.*, r.name as role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.username = :username
            """,
            {"username": username},
        )


def get_user_by_id(user_id: int) -> dict | None:
    with get_connection() as conn:
        return db_execute_one(
            conn,
            """
            SELECT u.*, r.name as role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = :id
            """,
            {"id": user_id},
        )


def authenticate_user(username: str, password: str) -> dict | None:
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    if not user["is_active"]:
        return None

    with get_connection() as conn:
        db_execute(
            conn,
            "UPDATE users SET last_login = :ts WHERE id = :id",
            {"ts": datetime.utcnow().isoformat(), "id": user["id"]},
        )

    return user


def create_user(
    email: str,
    username: str,
    password: str,
    role_id: int = 2,
    full_name: str = None,
    is_superuser: bool = False,
) -> dict:
    hashed_password = get_password_hash(password)
    timestamp = datetime.utcnow().isoformat()

    with get_connection() as conn:
        existing = db_execute_one(
            conn,
            "SELECT id FROM users WHERE email = :email OR username = :username",
            {"email": email, "username": username},
        )
        if existing:
            raise HTTPException(409, "Email or username already exists")

        conn.execute(
            """
            INSERT INTO users (email, username, hashed_password, full_name,
                               role_id, is_active, is_superuser, created_at)
            VALUES (:email, :username, :password, :name,
                    :role, TRUE, :is_superuser, :ts)
            RETURNING id
            """,
            {
                "email": email,
                "username": username,
                "password": hashed_password,
                "name": full_name,
                "role": role_id,
                "is_superuser": is_superuser,
                "ts": timestamp,
            },
        )
        row = conn.fetchone()
        if row is None:
            raise RuntimeError(f"create_user: INSERT vide pour {username}")
        user_id = row["id"] if isinstance(row, dict) else row[0]

        db_execute(
            conn,
            """
            INSERT INTO user_tenants (user_id, tenant_id)
            VALUES (:uid, :tid)
            ON CONFLICT (user_id) DO NOTHING
            """,
            {"uid": user_id, "tid": f"tenant-{user_id}"},
        )

        return db_execute_one(
            conn,
            """
            SELECT u.*, r.name as role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = :id
            """,
            {"id": user_id},
        )
