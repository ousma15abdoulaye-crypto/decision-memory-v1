"""
DMS Database Layer — Unified (async backend + sync PostgreSQL)

Provides both:
  - Async ORM layer (Base, async engine, session factory) via backend.system.db
  - Sync connection helpers for scripts/CI (get_connection, db_execute, etc.)
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.base import Connection

# Re-export async ORM layer from backend
from backend.system.db import (  # noqa: F401
    Base,
    engine as async_engine,
    async_session_factory,
    get_db,
    init_db,
)

__all__ = [
    "Base", "async_engine", "async_session_factory", "get_db", "init_db",
    "engine", "get_connection", "db_execute", "db_execute_one", "db_fetchall",
    "init_db_schema",
]

# ---------------------------------------------------------------------------
# Sync engine for scripts and CI (matches main branch src/db.py API)
# ---------------------------------------------------------------------------

_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()


def _normalize_url(url: str) -> str:
    """Normalize postgres:// to postgresql:// for SQLAlchemy/psycopg compatibility."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def _get_sync_engine() -> Optional[Engine]:
    """Return a sync engine if DATABASE_URL is set, else None."""
    if not _DATABASE_URL:
        return None
    url = _normalize_url(_DATABASE_URL)
    # Strip async drivers for sync engine
    url = url.replace("+asyncpg", "").replace("+aiosqlite", "")
    # Ensure psycopg driver for postgresql URL if psycopg is available
    if url.startswith("postgresql://") and "+psycopg" not in url:
        try:
            import psycopg  # noqa: F401
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        except ImportError:
            pass  # Use default driver
    return create_engine(url, pool_pre_ping=True, echo=False)


# Lazy sync engine — only created if DATABASE_URL is set
_sync_engine: Optional[Engine] = None


def _ensure_sync_engine() -> Engine:
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = _get_sync_engine()
    if _sync_engine is None:
        raise RuntimeError(
            "DATABASE_URL is required. DMS is online-only (Constitution V2.1)."
        )
    return _sync_engine


# Module-level engine accessor (created lazily)
class _EngineProxy:
    """Lazy proxy so importing src.db doesn't fail without DATABASE_URL."""
    def __getattr__(self, name: str) -> Any:
        return getattr(_ensure_sync_engine(), name)

    def __repr__(self) -> str:
        try:
            return repr(_ensure_sync_engine())
        except RuntimeError:
            return "<EngineProxy(not configured)>"


engine = _EngineProxy()


@contextmanager
def get_connection() -> Iterator[Connection]:
    """Context manager for a sync database connection. Commits on success."""
    eng = _ensure_sync_engine()
    conn = eng.connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def db_execute(conn: Connection, sql: str, params: Optional[dict] = None) -> None:
    """Execute a statement (INSERT/UPDATE/DELETE)."""
    conn.execute(text(sql), params or {})


def db_execute_one(
    conn: Connection, sql: str, params: Optional[dict] = None
) -> Optional[dict]:
    """Execute and fetch one row as dict, or None."""
    result = conn.execute(text(sql), params or {})
    row = result.fetchone()
    if row is None:
        return None
    return dict(row._mapping)


def db_fetchall(
    conn: Connection, sql: str, params: Optional[dict] = None
) -> List[Any]:
    """Execute and fetch all rows."""
    result = conn.execute(text(sql), params or {})
    rows = result.fetchall()
    keys = result.keys()
    return [dict(zip(keys, row)) for row in rows]


def init_db_schema() -> None:
    """Create all tables if they do not exist (sync, for legacy scripts)."""
    eng = _ensure_sync_engine()
    with eng.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                case_type TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                lot TEXT,
                created_at TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open'
            )
        """))
        conn.execute(text("""
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
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS memory_entries (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                content_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (case_id) REFERENCES cases(id)
            )
        """))
        conn.execute(text("""
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
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cba_template_schemas (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                template_name TEXT NOT NULL,
                structure_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                reused_count INTEGER DEFAULT 0,
                FOREIGN KEY (case_id) REFERENCES cases(id)
            )
        """))
        conn.execute(text("""
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
        """))
        conn.commit()
