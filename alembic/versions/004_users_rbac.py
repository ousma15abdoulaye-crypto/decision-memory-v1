"""Add users, roles, permissions tables

Revision ID: 004_users_rbac
Revises: 002_add_couche_a
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
down_revision = '002_add_couche_a'
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
    """Crée les tables users, roles, permissions."""
    bind = _get_bind(engine)
    timestamp = datetime.utcnow().isoformat()
    
    # --- Table roles ---
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            CONSTRAINT uq_role_name UNIQUE (name)
        )
    """)
    
    # Seed roles (Manuel SCI)
    _execute_sql(bind, f"""
        INSERT INTO roles (id, name, description, created_at) 
        SELECT 1, 'admin', 'Full system access', '{timestamp}'
        WHERE NOT EXISTS (SELECT 1 FROM roles WHERE id = 1);
        
        INSERT INTO roles (id, name, description, created_at) 
        SELECT 2, 'procurement_officer', 'Can create and manage own cases', '{timestamp}'
        WHERE NOT EXISTS (SELECT 1 FROM roles WHERE id = 2);
        
        INSERT INTO roles (id, name, description, created_at) 
        SELECT 3, 'viewer', 'Read-only access', '{timestamp}'
        WHERE NOT EXISTS (SELECT 1 FROM roles WHERE id = 3);
    """)
    
    # --- Table users ---
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT NOT NULL,
            username TEXT NOT NULL,
            hashed_password TEXT NOT NULL,
            full_name TEXT,
            is_active INTEGER DEFAULT 1,
            is_superuser INTEGER DEFAULT 0,
            role_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            last_login TEXT,
            CONSTRAINT uq_user_email UNIQUE (email),
            CONSTRAINT uq_user_username UNIQUE (username),
            FOREIGN KEY (role_id) REFERENCES roles(id)
        )
    """)
    
    _execute_sql(bind, """
        CREATE INDEX IF NOT EXISTS idx_users_role ON users(role_id)
    """)
    
    # Seed admin user (username: admin, password: Admin123!)
    # Hash généré avec: passlib.hash.bcrypt.hash("Admin123!")
    _execute_sql(bind, f"""
        INSERT INTO users (id, email, username, hashed_password, full_name, is_active, is_superuser, role_id, created_at)
        SELECT 1, 'admin@dms.local', 'admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lWZy.KU7T.Zm', 'System Administrator', 1, 1, 1, '{timestamp}'
        WHERE NOT EXISTS (SELECT 1 FROM users WHERE id = 1);
    """)
    
    # --- Table permissions (optionnel, pour granularité fine) ---
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            resource TEXT NOT NULL,
            action TEXT NOT NULL,
            CONSTRAINT uq_permission_name UNIQUE (name)
        )
    """)
    
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id INTEGER NOT NULL,
            permission_id INTEGER NOT NULL,
            PRIMARY KEY (role_id, permission_id),
            FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
            FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
        )
    """)
    
    # --- Ajout owner_id dans cases (pour ownership) ---
    _execute_sql(bind, """
        ALTER TABLE cases ADD COLUMN IF NOT EXISTS owner_id INTEGER REFERENCES users(id)
    """)
    
    _execute_sql(bind, """
        CREATE INDEX IF NOT EXISTS idx_cases_owner ON cases(owner_id)
    """)
    
    # --- Ajout created_by dans artifacts (traçabilité) ---
    _execute_sql(bind, """
        ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id)
    """)
    
    # --- Ajout quota uploads dans cases (M4F) ---
    _execute_sql(bind, """
        ALTER TABLE cases ADD COLUMN IF NOT EXISTS total_upload_size INTEGER DEFAULT 0
    """)


def downgrade(engine: Optional[Engine] = None) -> None:
    """Supprime les colonnes et tables ajoutées."""
    bind = _get_bind(engine)
    
    # PostgreSQL doesn't support IF EXISTS in ALTER TABLE DROP COLUMN before version 12
    # We'll use a conditional approach
    _execute_sql(bind, """
        ALTER TABLE cases DROP COLUMN IF EXISTS total_upload_size
    """)
    
    _execute_sql(bind, """
        ALTER TABLE artifacts DROP COLUMN IF EXISTS created_by
    """)
    
    _execute_sql(bind, """
        DROP INDEX IF EXISTS idx_cases_owner
    """)
    
    _execute_sql(bind, """
        ALTER TABLE cases DROP COLUMN IF EXISTS owner_id
    """)
    
    _execute_sql(bind, """
        DROP TABLE IF EXISTS role_permissions CASCADE
    """)
    
    _execute_sql(bind, """
        DROP TABLE IF EXISTS permissions CASCADE
    """)
    
    _execute_sql(bind, """
        DROP INDEX IF EXISTS idx_users_role
    """)
    
    _execute_sql(bind, """
        DROP TABLE IF EXISTS users CASCADE
    """)
    
    _execute_sql(bind, """
        DROP TABLE IF EXISTS roles CASCADE
    """)
