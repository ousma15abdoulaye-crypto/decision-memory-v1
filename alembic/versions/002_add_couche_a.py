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
    if engine is not None:
        return engine
    if op is not None:
        return op.get_bind()
    from src.db import engine as db_engine
    return db_engine


def _run_sql(bind, sql: str) -> None:
    """Execute SQL on bind (Connection or Engine)."""
    if op is not None:
        op.execute(text(sql))
    else:
        with bind.connect() as conn:
            conn.execute(text(sql))
            conn.commit()


def upgrade(engine: Optional[Engine] = None) -> None:
    """Create Couche B + Couche A tables (IF NOT EXISTS)."""
    bind = _get_bind(engine)

    # Couche B (src/db.py)
    _run_sql(bind, """
        CREATE TABLE IF NOT EXISTS cases (
            id TEXT PRIMARY KEY,
            case_type TEXT NOT NULL,
            title TEXT NOT NULL,
            lot TEXT,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)
    _run_sql(bind, """
        CREATE TABLE IF NOT EXISTS artifacts (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            filename TEXT NOT NULL,
            path TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            meta_json TEXT,
            FOREIGN KEY (case_id) REFERENCES cases(id)
        )
    """)
    _run_sql(bind, """
        CREATE TABLE IF NOT EXISTS memory_entries (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            entry_type TEXT NOT NULL,
            content_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (case_id) REFERENCES cases(id)
        )
    """)
    _run_sql(bind, """
        CREATE TABLE IF NOT EXISTS dao_criteria (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            categorie TEXT NOT NULL,
            critere_nom TEXT NOT NULL,
            description TEXT,
            ponderation REAL NOT NULL,
            type_reponse TEXT NOT NULL,
            seuil_elimination REAL,
            ordre_affichage INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (case_id) REFERENCES cases(id)
        )
    """)
    _run_sql(bind, """
        CREATE TABLE IF NOT EXISTS cba_template_schemas (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            template_name TEXT NOT NULL,
            structure_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            reused_count INTEGER DEFAULT 0,
            FOREIGN KEY (case_id) REFERENCES cases(id)
        )
    """)
    _run_sql(bind, """
        CREATE TABLE IF NOT EXISTS offer_extractions (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            artifact_id TEXT NOT NULL,
            supplier_name TEXT NOT NULL,
            extracted_data_json TEXT NOT NULL,
            missing_fields_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (case_id) REFERENCES cases(id),
            FOREIGN KEY (artifact_id) REFERENCES artifacts(id)
        )
    """)

    # Couche A (lots, offers, documents, extractions, analyses, audits)
    _run_sql(bind, """
        CREATE TABLE IF NOT EXISTS lots (
            id VARCHAR(20) PRIMARY KEY,
            case_id VARCHAR(20) NOT NULL REFERENCES cases(id),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)
    _run_sql(bind, """
        CREATE TABLE IF NOT EXISTS offers (
            id VARCHAR(20) PRIMARY KEY,
            case_id VARCHAR(20) NOT NULL REFERENCES cases(id),
            lot_id VARCHAR(20) NOT NULL REFERENCES lots(id),
            supplier_name VARCHAR(255) NOT NULL,
            offer_type VARCHAR(40) NOT NULL DEFAULT 'AUTRE',
            submitted_at TIMESTAMP WITH TIME ZONE,
            amount REAL,
            status VARCHAR(40) NOT NULL DEFAULT 'EN_ATTENTE',
            score REAL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)
    _run_sql(bind, """
        CREATE TABLE IF NOT EXISTS documents (
            id VARCHAR(20) PRIMARY KEY,
            case_id VARCHAR(20) NOT NULL REFERENCES cases(id),
            lot_id VARCHAR(20) NOT NULL REFERENCES lots(id),
            offer_id VARCHAR(20) NOT NULL REFERENCES offers(id),
            document_type VARCHAR(40) NOT NULL,
            filename VARCHAR(255) NOT NULL,
            storage_path TEXT NOT NULL,
            mime_type VARCHAR(120) NOT NULL,
            metadata_json TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)
    _run_sql(bind, """
        CREATE TABLE IF NOT EXISTS extractions (
            id VARCHAR(20) PRIMARY KEY,
            document_id VARCHAR(20) NOT NULL REFERENCES documents(id),
            offer_id VARCHAR(20) NOT NULL REFERENCES offers(id),
            extracted_json TEXT NOT NULL,
            missing_json TEXT NOT NULL,
            used_llm BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)
    _run_sql(bind, """
        CREATE TABLE IF NOT EXISTS analyses (
            id VARCHAR(20) PRIMARY KEY,
            offer_id VARCHAR(20) NOT NULL REFERENCES offers(id),
            essentials_score REAL,
            capacity_score REAL,
            sustainability_score REAL,
            commercial_score REAL,
            total_score REAL,
            status VARCHAR(40) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)
    _run_sql(bind, """
        CREATE TABLE IF NOT EXISTS audits (
            id VARCHAR(20) PRIMARY KEY,
            entity_type VARCHAR(40) NOT NULL,
            entity_id VARCHAR(20) NOT NULL,
            action VARCHAR(80) NOT NULL,
            actor VARCHAR(120),
            details_json TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """)


def downgrade(engine: Optional[Engine] = None) -> None:
    """Drop Couche A tables only (preserve cases et Couche B)."""
    bind = _get_bind(engine)
    tables_to_drop = ["analyses", "extractions", "documents", "offers", "lots", "audits"]

    if op is not None:
        for table in tables_to_drop:
            op.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
    else:
        with bind.connect() as conn:
            for table in tables_to_drop:
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
            conn.commit()
