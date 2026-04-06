#!/usr/bin/env python3
"""Contrôles SQL read-only — seal / workspace (mandat hardening).

Usage (Railway DB) :
  python scripts/with_railway_env.py python scripts/hardening_product_sql_checks.py <workspace_id>
"""

from __future__ import annotations

import argparse
import os
import sys

from src.db.core import get_connection


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("workspace_id", help="UUID process_workspaces.id")
    args = p.parse_args()
    wid = args.workspace_id.strip()

    if not os.environ.get("DATABASE_URL"):
        print("DATABASE_URL manquant — utiliser with_railway_env.py", file=sys.stderr)
        return 1

    with get_connection() as conn:
        conn.execute(
            """
            SELECT cs.id, cs.session_status, cs.seal_hash, cs.sealed_at,
                   LENGTH(cs.seal_hash::text) AS hash_len,
                   cs.pv_snapshot IS NOT NULL AS has_snap,
                   pw.status AS ws_status
            FROM committee_sessions cs
            JOIN process_workspaces pw ON pw.id = cs.workspace_id
            WHERE cs.workspace_id = CAST(:w AS uuid)
            LIMIT 1
            """,
            {"w": wid},
        )
        row = conn.fetchone()
        if not row:
            print("ROUGE: aucune committee_sessions pour ce workspace")
            return 2
        h = row.get("seal_hash")
        ok = True
        if row.get("session_status") != "sealed":
            print(f"ROUGE: session_status={row.get('session_status')} (attendu sealed)")
            ok = False
        if not h or len(str(h)) != 64:
            print(
                f"ROUGE: seal_hash absent ou longueur != 64 (got {len(str(h)) if h else 0})"
            )
            ok = False
        if not row.get("has_snap"):
            print("ROUGE: pv_snapshot NULL")
            ok = False
        if not row.get("sealed_at"):
            print("ROUGE: sealed_at NULL")
            ok = False
        if str(row.get("ws_status") or "") != "sealed":
            print(
                f"ROUGE: process_workspaces.status={row.get('ws_status')} (attendu sealed)"
            )
            ok = False
        if ok:
            print(
                "VERT: committee_sessions + workspace alignés sealed + hash 64 + snapshot"
            )
        return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
