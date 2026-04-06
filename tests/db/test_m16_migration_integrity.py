"""F2 — intégrité migrations M16 (index 085)."""

from __future__ import annotations

import pytest


@pytest.mark.db_integrity
def test_m16_indexes_exist(db_conn) -> None:
    """Index créés par 085 présents."""
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT indexname FROM pg_indexes
            WHERE schemaname = 'public'
              AND indexname IN (
                  'idx_ca_workspace_bundle',
                  'idx_plbv_workspace_bundle'
              )
            """)
        names = {r["indexname"] for r in cur.fetchall()}
    assert "idx_ca_workspace_bundle" in names
    assert "idx_plbv_workspace_bundle" in names
