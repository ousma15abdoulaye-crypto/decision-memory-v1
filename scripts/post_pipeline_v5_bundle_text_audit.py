#!/usr/bin/env python3
"""Audit bundle_documents.raw_text par workspace (diagnostic post-pipeline V5).

Usage (avec DATABASE_URL + contexte RLS si requis)::

  python scripts/post_pipeline_v5_bundle_text_audit.py <workspace_uuid>

Sortie : tableau bundle_id, vendor, nb docs, nb raw_text NULL, file_types.
"""

from __future__ import annotations

import argparse
import sys

from src.db import db_fetchall, get_connection


def run_audit(workspace_id: str) -> None:
    with get_connection() as conn:
        rows = db_fetchall(
            conn,
            """
            SELECT b.id::text AS bundle_id,
                   b.vendor_name_raw AS vendor,
                   COUNT(d.id)::int AS doc_count,
                   SUM(CASE
                       WHEN d.raw_text IS NULL OR trim(d.raw_text) = '' THEN 1
                       ELSE 0
                   END)::int AS empty_text_count,
                   array_agg(DISTINCT d.file_type) AS file_types
            FROM supplier_bundles b
            LEFT JOIN bundle_documents d ON d.bundle_id = b.id
            WHERE b.workspace_id = CAST(:wid AS uuid)
            GROUP BY b.id, b.vendor_name_raw
            ORDER BY b.bundle_index
            """,
            {"wid": workspace_id},
        )

    if not rows:
        print("Aucun bundle pour ce workspace.")
        return

    print(f"Workspace {workspace_id} — {len(rows)} bundle(s)\n")
    for r in rows:
        v = (r.get("vendor") or "")[:60]
        print(
            f"  bundle={r['bundle_id'][:8]}… vendor={v!r} "
            f"docs={r['doc_count']} sans_texte={r['empty_text_count']} "
            f"types={r['file_types']}"
        )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace_id", help="UUID process_workspaces.id")
    args = p.parse_args()
    try:
        run_audit(args.workspace_id.strip())
    except Exception as exc:
        print(f"ERREUR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
