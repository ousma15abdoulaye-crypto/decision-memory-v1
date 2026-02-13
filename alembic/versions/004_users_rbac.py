"""Add users, roles, permissions tables

Revision ID: 004_users_rbac
Revises: 003_add_procurement_extensions
Create Date: 2026-02-12 19:15:00
"""
from __future__ import annotations

from typing import Optional
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

try:
    from alembic import op
except ImportError:
    op = None

revision = '004_users_rbac'
down_revision = '003_add_procurement_extensions'  # ✅ dépend de M2‑Extended
branch_labels = None
depends_on = None


def _get_bind(engine: Optional[Engine] = None) -> Engine | Connection:
    """Retourne la connexion/engine approprié."""
    if engine is not None:
        return engine
    if op is not None:
        return op.get_bind()
    from src.db import engine as db_engine
    return db_engine


def _execute_sql(target, sql: str) -> None:
    """Exécute du SQL brut."""
    if isinstance(target, Engine):
        with target.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
    else:
        target.execute(text(sql))


def upgrade(engine: Optional[Engine] = None) -> None:
    """Crée tables users, roles, permissions + seed data."""
    bind = _get_bind(engine)
    timestamp = datetime.utcnow().isoformat()
    
    # --- Table roles ---
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            name VARCHAR(50) NOT NULL UNIQUE,
            description TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    # Seed roles (Manuel SCI)
    _execute_sql(bind, f"""
        INSERT INTO roles (name, description, created_at) VALUES
        ('admin', 'Full system access', '{timestamp}'),
        ('procurement_officer', 'Can create and manage own cases', '{timestamp}'),
        ('viewer', 'Read-only access', '{timestamp}')
        ON CONFLICT (name) DO NOTHING
    """)
    
    # --- Table users ---
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            email VARCHAR(320) NOT NULL UNIQUE,
            username VARCHAR(50) NOT NULL UNIQUE,
            hashed_password VARCHAR(255) NOT NULL,
            full_name TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            is_superuser BOOLEAN DEFAULT FALSE,
            role_id INTEGER NOT NULL REFERENCES roles(id),
            created_at TEXT NOT NULL,
            last_login TEXT
        )
    """)
    _execute_sql(bind, "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role_id)")
    
    # Seed admin user (username: admin, password: Admin123!)
    # Hash généré avec: passlib.hash.bcrypt.hash("Admin123!")
    # Note: Fixed hash to correctly match "Admin123!"
    _execute_sql(bind, f"""
        INSERT INTO users (email, username, hashed_password, full_name, is_active, is_superuser, role_id, created_at)
        VALUES ('admin@dms.local', 'admin', '$2b$12$DqT91f0yXWzN02n2IUs9BeHUVC5OYzFOf1viyOefO664E/5VnJElW', 'System Administrator', TRUE, TRUE, 1, '{timestamp}')
        ON CONFLICT (username) DO UPDATE SET hashed_password = EXCLUDED.hashed_password
    """)
    
    # --- Table permissions (optionnel, pour granularité fine) ---
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            name VARCHAR(100) NOT NULL UNIQUE,
            resource VARCHAR(100) NOT NULL,
            action VARCHAR(50) NOT NULL
        )
    """)
    
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
            PRIMARY KEY (role_id, permission_id)
        )
    """)
    
    # --- Ajout owner_id dans cases (pour ownership) ---
    _execute_sql(bind, """
        ALTER TABLE cases 
        ADD COLUMN IF NOT EXISTS owner_id INTEGER REFERENCES users(id)
    """)
    _execute_sql(bind, "CREATE INDEX IF NOT EXISTS idx_cases_owner ON cases(owner_id)")
    
    # --- Ajout created_by dans artifacts (traçabilité) ---
    _execute_sql(bind, """
        ALTER TABLE artifacts 
        ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id)
    """)
    
    # --- Ajout quota uploads dans cases (M4F) ---
    _execute_sql(bind, """
        ALTER TABLE cases 
        ADD COLUMN IF NOT EXISTS total_upload_size BIGINT DEFAULT 0
    """)


def downgrade(engine: Optional[Engine] = None) -> None:
    """Supprime les tables et colonnes ajoutées."""
    bind = _get_bind(engine)
    
    _execute_sql(bind, "ALTER TABLE cases DROP COLUMN IF EXISTS total_upload_size")
    _execute_sql(bind, "ALTER TABLE artifacts DROP COLUMN IF EXISTS created_by")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_cases_owner")
    _execute_sql(bind, "ALTER TABLE cases DROP COLUMN IF EXISTS owner_id")
    _execute_sql(bind, "DROP TABLE IF EXISTS role_permissions")
    _execute_sql(bind, "DROP TABLE IF EXISTS permissions")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_users_role")
    _execute_sql(bind, "DROP TABLE IF EXISTS users")
    _execute_sql(bind, "DROP TABLE IF EXISTS roles")