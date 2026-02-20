# src/db/core.py
"""
DMS Database Layer — PostgreSQL ONLY (Constitution V2.1, ADR-0003 §3.1).
No ORM, no SQLAlchemy, no sessionmaker. psycopg only.
Helpers: get_connection, db_execute, db_fetchall, init_db_schema.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row

from src.db.connection import get_db_cursor

logger = logging.getLogger(__name__)

_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()


def _normalize_url(url: str) -> str:
    """Normalize postgres:// to postgresql:// for psycopg."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def _sql_to_psycopg_style(sql: str, params: dict[str, Any]) -> str:
    """Convert :name placeholders to %(name)s for psycopg."""
    for key in params:
        sql = sql.replace(":" + key, "%(" + key + ")s")
    return sql


class _ConnectionWrapper:
    """Thin wrapper over psycopg connection for get_connection() API.
    Exposes execute(sql, params), commit(), rollback(), close().
    """

    def __init__(self, conn: psycopg.Connection):
        self._conn = conn
        self._cur = conn.cursor(row_factory=dict_row)

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None:
        p = params or {}
        self._cur.execute(_sql_to_psycopg_style(sql, p), p)

    def fetchone(self) -> dict[str, Any] | None:
        row = self._cur.fetchone()
        return dict(row) if row else None

    def fetchall(self) -> list[dict[str, Any]]:
        rows = self._cur.fetchall()
        return [dict(r) for r in rows]

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._cur.close()
        self._conn.close()


def _get_raw_connection() -> psycopg.Connection:
    """Open a single psycopg connection (for use with resilience)."""
    if not _DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is required. DMS is online-only (Constitution V2.1)."
        )
    url = _normalize_url(_DATABASE_URL)
    url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    return psycopg.connect(url)


@contextmanager
def get_db_connection() -> Iterator[psycopg.Connection]:
    """
    Context manager — connexion psycopg synchrone.
    Commit automatique sur succès.
    Rollback automatique sur erreur.

    Usage :
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM cases WHERE id = %s",
                    (case_id,)
                )
    """
    conn = _get_raw_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def get_connection() -> Iterator[_ConnectionWrapper]:
    """
    Context manager for a database connection with resilience.
    Yields a wrapper that exposes execute(sql, params), commit(), rollback(), close().
    """
    from src.resilience import db_breaker, retry_db_operation

    @retry_db_operation
    def _connect():
        try:
            return db_breaker.call(_get_raw_connection)
        except Exception as e:
            logger.error("[DB] Échec connexion après retry: %s", e)
            raise

    conn = _connect()
    wrapper = _ConnectionWrapper(conn)
    try:
        yield wrapper
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        wrapper.close()


def db_execute(
    conn: _ConnectionWrapper, sql: str, params: dict[str, Any] | None = None
) -> None:
    """Execute a statement (INSERT/UPDATE/DELETE) with retry."""
    from src.resilience import retry_db_operation

    @retry_db_operation
    def _run():
        conn.execute(sql, params or {})

    _run()


def db_execute_one(conn_or_sql, sql_or_params=None, params=None):
    """Execute query and return first row. Supports (conn, sql, params) or (sql, params)."""
    if params is not None:
        conn, sql, p = conn_or_sql, sql_or_params, params or {}
        conn.execute(sql, p)
        return conn.fetchone()
    sql, p = conn_or_sql, sql_or_params or {}
    with get_db_cursor() as cur:
        cur.execute(_sql_to_psycopg_style(sql, p), p)
        row = cur.fetchone()
        return dict(row) if row else None


def db_fetchall(
    conn: _ConnectionWrapper, sql: str, params: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Execute and fetch all rows."""
    conn.execute(sql, params or {})
    return conn.fetchall()


def init_db_schema() -> None:
    """Create all tables if they do not exist (psycopg only)."""
    statements = [
        """
        CREATE TABLE IF NOT EXISTS cases (
            id TEXT PRIMARY KEY,
            case_type TEXT NOT NULL,
            title TEXT NOT NULL,
            lot TEXT,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL
        )
        """,
        """
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
        """,
        """
        CREATE TABLE IF NOT EXISTS memory_entries (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            entry_type TEXT NOT NULL,
            content_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (case_id) REFERENCES cases(id)
        )
        """,
        """
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
        """,
        """
        CREATE TABLE IF NOT EXISTS cba_template_schemas (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            template_name TEXT NOT NULL,
            structure_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            reused_count INTEGER DEFAULT 0,
            FOREIGN KEY (case_id) REFERENCES cases(id)
        )
        """,
        """
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
        """,
    ]
    with get_db_cursor() as cur:
        for stmt in statements:
            cur.execute(stmt.strip())
