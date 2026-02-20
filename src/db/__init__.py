"""DMS DB package: re-export core API and connection helpers (ADR-0003: no ORM)."""

from src.db.connection import get_db_cursor
from src.db.core import (
    _get_database_url,
    _get_raw_connection,
    db_execute,
    db_execute_one,
    db_fetchall,
    get_connection,
    init_db_schema,
)

# Validate DATABASE_URL at package load (INV-4); reload(src.db) re-runs this.
_get_database_url()

__all__ = [
    "_get_raw_connection",
    "db_execute",
    "db_execute_one",
    "db_fetchall",
    "get_connection",
    "get_db_cursor",
    "init_db_schema",
]
