"""Add Couche B + Couche A tables — migration autonome (down_revision=None).

Tables Couche B : cases, artifacts, memory_entries, dao_criteria, cba_template_schemas, offer_extractions.
Tables Couche A : lots, offers, documents, extractions, analyses, audits.
Source : src/db.py (Couche B), schéma Couche A (lots, offers, etc.).
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

try:
    from alembic import op
except ImportError:
    op = None

revision = "002_add_couche_a"
down_revision = None
branch_labels = None
depends_on = None


def _get_bind(engine: Optional[Engine] = None) -> Connection | Engine:
    """Retourne la connexion/engine approprié."""
    if engine is not None:
        return engine
    if op is not None:
        return op.get_bind()
    from src.db import engine as db_engine
    return db_engine


def _execute_sql(bind, sql: str):
    """Exécute du SQL brut sur le bind fourni, gère les transactions."""
    if op is not None and bind is op.get_bind():
        # Contexte Alembic – op.execute gère la transaction
        op.execute(sql)
    else:
        # Contexte test ou direct – on utilise une connexion
        with bind.connect() as conn:
            conn.execute(text(sql))
            conn.commit()


def upgrade(engine: Optional[Engine] = None) -> None:
    """Crée toutes les tables avec IF NOT EXISTS (Couche B + Couche A)."""
    bind = _get_bind(engine)

    # ----- Tables Couche B (src.db) -----
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS cases (
            id TEXT PRIMARY KEY,
            case_type TEXT NOT NULL,
            title TEXT NOT NULL,
            lot TEXT,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft'
        )
    """)
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS artifacts (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            kind TEXT NOT NULL,
            filename TEXT NOT NULL,
            path TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            meta_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS memory_entries (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            entry_type TEXT NOT NULL,
            content_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS dao_criteria (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            categorie TEXT NOT NULL,
            critere_nom TEXT NOT NULL,
            description TEXT,
            ponderation REAL NOT NULL,
            type_reponse TEXT NOT NULL,
            seuil_elimination REAL,
            ordre_affichage INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS cba_template_schemas (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            template_name TEXT NOT NULL,
            structure_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            reused_count INTEGER DEFAULT 0
        )
    """)
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS offer_extractions (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
            supplier_name TEXT NOT NULL,
            extracted_data_json TEXT NOT NULL,
            missing_fields_json TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # ----- Tables Couche A (spécifiques) -----
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS lots (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            lot_number TEXT NOT NULL,
            description TEXT,
            estimated_value REAL,
            created_at TEXT NOT NULL
        )
    """)
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS offers (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            supplier_name TEXT NOT NULL,
            offer_type TEXT NOT NULL,
            file_hash TEXT,
            submitted_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            offer_id TEXT REFERENCES offers(id) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            path TEXT NOT NULL,
            uploaded_at TEXT NOT NULL
        )
    """)
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS extractions (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            artifact_id TEXT NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
            extraction_type TEXT NOT NULL,
            data_json TEXT NOT NULL,
            confidence REAL,
            created_at TEXT NOT NULL
        )
    """)
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            analysis_type TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS audits (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            user_id TEXT,
            action TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            created_at TEXT NOT NULL
        )
    """)


def downgrade(engine: Optional[Engine] = None) -> None:
    """Supprime UNIQUEMENT les tables Couche A (préserve cases et Couche B)."""
    bind = _get_bind(engine)
    tables_to_drop = ["analyses", "extractions", "documents", "offers", "lots", "audits"]

    for table in tables_to_drop:
        if op is not None:
            op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        else:
            with bind.connect() as conn:
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                conn.commit()