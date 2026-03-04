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

# DATABASE_URL validé au premier appel get_connection()
# via core._get_or_init_db_url() — lazy init intentionnel
# Permet import sans DB en CI pure · voir TD-005 TECHNICAL_DEBT.md

__all__ = [
    "_get_raw_connection",
    "db_execute",
    "db_execute_one",
    "db_fetchall",
    "get_connection",
    "get_db_cursor",
    "init_db_schema",
]
