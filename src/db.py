"""
DMS Database Layer — PostgreSQL ONLY (Constitution V2.1 ONLINE-ONLY)
No SQLite fallback. App refuses boot without DATABASE_URL.
"""

from __future__ import annotations

import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.base import Connection
from contextlib import contextmanager
from typing import Iterator, List, Any, Optional
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)

_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()


def _normalize_url(url: str) -> str:
    """Normalize postgres:// to postgresql:// for SQLAlchemy/psycopg compatibility."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def _get_engine() -> Engine:
    if not _DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is required. DMS is online-only (Constitution V2.1)."
        )
    url = _normalize_url(_DATABASE_URL)
    # Ensure psycopg driver for postgresql URL
    if url.startswith("postgresql://") and "postgresql+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(
        url,
        pool_pre_ping=True,
        echo=False,
    )


engine: Engine = _get_engine()


def _get_raw_connection() -> Connection:
    """Connexion brute sans protection (interne)."""
    return engine.connect()


@contextmanager
def get_connection() -> Iterator[Connection]:
    """
    Context manager for a database connection with resilience.

    Constitution V2.1 : Helpers synchrones uniquement.
    Tenacity : 3 tentatives avec backoff exponentiel.
    Circuit breaker : Protection contre échecs en cascade.
    """
    from src.resilience import retry_db_operation, db_breaker

    @retry_db_operation
    def get_conn():
        try:
            return db_breaker.call(_get_raw_connection)
        except Exception as e:
            logger.error(f"[DB] Échec connexion après retry: {e}")
            raise

    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def db_execute(conn: Connection, sql: str, params: Optional[dict] = None) -> None:
    """
    Execute a statement (INSERT/UPDATE/DELETE) with retry.

    Protège contre erreurs temporaires (network, lock timeout).
    """
    from src.resilience import retry_db_operation
    from psycopg import OperationalError, DatabaseError

    @retry_db_operation
    def _execute():
        try:
            return conn.execute(text(sql), params or {})
        except (OperationalError, DatabaseError) as e:
            logger.warning(f"[DB] Erreur temporaire: {e}")
            raise  # Tenacity va retry

    _execute()


def db_execute_one(conn_or_sql, sql_or_params=None, params=None):
    """Execute query and return first row. Supports (conn, sql, params) or (sql, params)."""
    if params is not None:
        conn, sql, p = conn_or_sql, sql_or_params, params or {}
        result = conn.execute(text(sql), p)
    else:
        sql, p = conn_or_sql, sql_or_params or {}
        with engine.connect() as conn:
            result = conn.execute(text(sql), p)
    row = result.fetchone()
    if row is None:
        return None
    return dict(row._mapping)


def db_fetchall(conn: Connection, sql: str, params: Optional[dict] = None) -> List[Any]:
    """Execute and fetch all rows."""
    result = conn.execute(text(sql), params or {})
    rows = result.fetchall()
    keys = result.keys()
    return [dict(zip(keys, row)) for row in rows]


def init_db_schema() -> None:
    """Create all tables if they do not exist."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                case_type TEXT NOT NULL,
                title TEXT NOT NULL,
                lot TEXT,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL
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


@contextmanager
def get_session() -> Iterator[Session]:
    """
    Context manager for a SQLAlchemy ORM session.

    Provides an ORM session for Couche B fuzzy resolution queries.
    Automatically commits on success, rolls back on error.
    """
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
