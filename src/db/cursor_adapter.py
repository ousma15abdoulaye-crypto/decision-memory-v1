"""PsycopgCursorAdapter — bridges psycopg v3 cursor to the _ConnectionProtocol.

Services in src/memory/ use ':name' SQL parameter style (SQLite/SQLAlchemy style).
psycopg v3 cursors expect '%(name)s' style for named dict params.
This adapter translates between the two so services work with real DB cursors.

Usage inside FastAPI routes or workers:
    with get_db_cursor() as cur:
        conn = PsycopgCursorAdapter(cur)
        svc = EventIndexService(lambda: conn)
        ...
"""

from __future__ import annotations

import re
from typing import Any

_NAMED_PARAM_RE = re.compile(r":([a-zA-Z_][a-zA-Z0-9_]*)")


def _convert_params(sql: str) -> str:
    """Convert ':name' placeholders to '%(name)s' for psycopg v3."""
    return _NAMED_PARAM_RE.sub(r"%(\1)s", sql)


class PsycopgCursorAdapter:
    """Wraps a psycopg v3 cursor to satisfy the _ConnectionProtocol.

    Translates ':name' → '%(name)s' SQL parameter style.
    fetchone() / fetchall() delegate directly to the underlying cursor.
    """

    __slots__ = ("_cur",)

    def __init__(self, cursor: Any) -> None:
        self._cur = cursor

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None:
        converted = _convert_params(sql) if params else sql
        self._cur.execute(converted, params)

    def fetchone(self) -> dict[str, Any] | None:
        row = self._cur.fetchone()
        if row is None:
            return None
        # psycopg dict_row returns a dict-like object; ensure plain dict
        return dict(row) if not isinstance(row, dict) else row

    def fetchall(self) -> list[dict[str, Any]]:
        rows = self._cur.fetchall()
        return [dict(r) if not isinstance(r, dict) else r for r in rows]
