"""Helpers DB authentification — extraits de src/auth.py (legacy).

Déplacés ici lors de M2 UNIFY SYSTEM pour permettre la suppression
de src/auth.py sans perte de logique métier.

Contrat : logique auth inchangée pour les appels existants ; extensions V2 ci-dessous.
  - authenticate_user   : bcrypt + DB + last_login (login = email ou username)
  - create_user         : users + user_tenants (UUID tenant réel) + user_tenant_roles (RBAC)
  - get_tenant_id_for_user : lit ``user_tenants.tenant_id`` (exposition client / JWT legacy)
  - resolve_tenant_uuid_for_jwt : JWT tenant aligné sur ``public.tenants`` (jointure)
  - get_user_by_username / get_user_by_login / get_user_by_id : SELECT users JOIN roles
  - verify_password / get_password_hash : bcrypt direct

Note DETTE-M1-04 : create_user utilise role_id INTEGER (legacy).
  DROP COLUMN role_id reporté à M2B (schéma inchangé en M2).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

import bcrypt as _bcrypt
from fastapi import HTTPException

from src.db import db_execute, db_execute_one, get_connection

logger = logging.getLogger(__name__)


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
    """Résolution stricte par nom d'utilisateur (compat appels existants)."""
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


def get_user_by_login(login: str) -> dict | None:
    """Résout un utilisateur par email **ou** username (champ unique formulaire login)."""
    login = (login or "").strip()
    if not login:
        return None
    with get_connection() as conn:
        return db_execute_one(
            conn,
            """
            SELECT u.*, r.name as role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.username = :login OR u.email = :login
            """,
            {"login": login},
        )


def get_tenant_id_for_user(user_id: int) -> str | None:
    """Lit tenant_id métier (user_tenants) pour exposer au client / JWT."""
    with get_connection() as conn:
        row = db_execute_one(
            conn,
            "SELECT tenant_id FROM user_tenants WHERE user_id = :id",
            {"id": user_id},
        )
    return row["tenant_id"] if row else None


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
    user = get_user_by_login(username)
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


def _default_tenant_id_text(conn) -> str:
    """UUID texte à écrire dans ``user_tenants.tenant_id`` pour un nouvel utilisateur.

    Priorité :
      1. Tenant actif dont ``code`` = ``DEFAULT_TENANT_CODE`` (défaut ``sci_mali``).
      2. Tenant actif dont ``id::text`` = ``DEFAULT_TENANT_CODE`` (si la variable
         contient déjà un UUID).
      3. Premier tenant actif par ``created_at`` (fallback mono-tenant).

    Si aucun tenant actif : ``RuntimeError`` (pas de fallback silencieux).
    """
    raw = (os.environ.get("DEFAULT_TENANT_CODE") or "sci_mali").strip() or "sci_mali"
    row = db_execute_one(
        conn,
        """
        SELECT id::text AS id FROM tenants
        WHERE code = :code AND is_active = TRUE
        LIMIT 1
        """,
        {"code": raw},
    )
    if row:
        return str(row["id"])
    row = db_execute_one(
        conn,
        """
        SELECT id::text AS id FROM tenants
        WHERE id::text = :tid AND is_active = TRUE
        LIMIT 1
        """,
        {"tid": raw},
    )
    if row:
        return str(row["id"])
    row = db_execute_one(
        conn,
        """
        SELECT id::text AS id FROM tenants
        WHERE is_active = TRUE
        ORDER BY created_at
        LIMIT 1
        """,
        {},
    )
    if not row:
        raise RuntimeError(
            "Aucun tenant actif dans public.tenants — "
            "migrations 068+ requises ou créer un tenant."
        )
    return str(row["id"])


def _rbac_code_for_legacy_user(is_superuser: bool, legacy_role_name: str) -> str:
    """Codes alignés sur ``alembic/versions/075_rbac_permissions_roles.py`` (_ROLES).

    Vérifier en prod : ``SELECT code FROM rbac_roles ORDER BY code;`` — si un code
    diverge, l'INSERT ``user_tenant_roles`` est ignoré (voir warning ci-dessous).
    """
    if is_superuser:
        return "supply_chain_admin"
    name = (legacy_role_name or "").lower()
    if name == "admin":
        return "supply_chain_admin"
    if name == "procurement_officer":
        return "procurement_officer"
    return "market_analyst"


def _ensure_user_tenant_rbac(
    conn,
    user_id: int,
    tenant_id_text: str,
    is_superuser: bool,
    legacy_role_name: str,
) -> None:
    meta = db_execute_one(
        conn,
        """
        SELECT 1 AS ok FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'rbac_roles'
        LIMIT 1
        """,
        {},
    )
    if not meta:
        return
    rbac_code = _rbac_code_for_legacy_user(is_superuser, legacy_role_name)
    rrow = db_execute_one(
        conn,
        "SELECT id::text AS id FROM rbac_roles WHERE code = :code LIMIT 1",
        {"code": rbac_code},
    )
    if not rrow:
        logger.warning(
            "rbac_roles sans code %r — pas d'INSERT user_tenant_roles pour cet utilisateur. "
            "Vérifier la migration 075 et SELECT code FROM rbac_roles.",
            rbac_code,
        )
        return
    db_execute(
        conn,
        """
        INSERT INTO user_tenant_roles (user_id, tenant_id, role_id)
        VALUES (
            :uid,
            CAST(:tid AS uuid),
            CAST(:rid AS uuid)
        )
        ON CONFLICT (user_id, tenant_id, role_id) DO NOTHING
        """,
        {"uid": user_id, "tid": tenant_id_text, "rid": str(rrow["id"])},
    )


def resolve_tenant_uuid_for_jwt(user_id: int) -> str:
    """UUID texte pour le claim JWT : jointure ``user_tenants`` ↔ ``tenants``.

    Couvre ``tenant_id`` stocké comme ``tenants.id::text`` ou comme ``tenants.code``.
    Si aucune ligne ne matche : repli ``tenant-{user_id}`` (legacy ; migration 091
    corrige les lignes placeholder côté base).
    """
    with get_connection() as conn:
        trow = db_execute_one(
            conn,
            """
            SELECT t.id::text AS tenant_uuid
            FROM user_tenants ut
            JOIN tenants t ON (t.id::text = ut.tenant_id OR t.code = ut.tenant_id)
            WHERE ut.user_id = :uid
            LIMIT 1
            """,
            {"uid": user_id},
        )
    return str(trow["tenant_uuid"]) if trow else f"tenant-{user_id}"


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

        tenant_id_text = _default_tenant_id_text(conn)

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
            ON CONFLICT (user_id) DO UPDATE SET tenant_id = EXCLUDED.tenant_id
            """,
            {"uid": user_id, "tid": tenant_id_text},
        )

        role_row = db_execute_one(
            conn,
            "SELECT name FROM roles WHERE id = :rid LIMIT 1",
            {"rid": role_id},
        )
        legacy_role_name = str(role_row["name"]) if role_row else "viewer"

        _ensure_user_tenant_rbac(
            conn,
            user_id,
            tenant_id_text,
            is_superuser,
            legacy_role_name,
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
