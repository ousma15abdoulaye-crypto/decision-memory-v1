#!/usr/bin/env python3
"""Liste les supplier_bundles d'un workspace (analyse « N offres vs M bundles »).

Utile pour comprendre pourquoi le graphe Pass -1 produit plus de bundles que
de dossiers fournisseurs (heuristique ``resolve_bundle_vendor_key`` / ZIP).

Usage ::
  python scripts/probe_workspace_bundles.py <workspace_uuid>

Variables : ``DATABASE_URL`` (``.env.local`` puis ``.env``).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(_REPO / ".env")
        load_dotenv(_REPO / ".env.local", override=True)
    except ImportError:
        for name in (".env.local", ".env"):
            p = _REPO / name
            if not p.is_file():
                continue
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _normalize_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def main() -> int:
    _load_env()
    parser = argparse.ArgumentParser(
        description="Liste supplier_bundles + nombre de documents par bundle."
    )
    parser.add_argument("workspace_id", help="UUID workspace")
    args = parser.parse_args()

    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("DATABASE_URL manquant (.env.local / .env)", file=sys.stderr)
        return 2

    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as e:
        print(f"psycopg requis: {e}", file=sys.stderr)
        return 2

    conninfo = _normalize_url(url)
    wid = args.workspace_id

    with psycopg.connect(conninfo, row_factory=dict_row) as conn:
        conn.autocommit = True
        ws = conn.execute(
            "SELECT id::text, reference_code, title FROM process_workspaces "
            "WHERE id = %s::uuid",
            (wid,),
        ).fetchone()
        if not ws:
            print(json.dumps({"error": "workspace_not_found", "id": wid}, indent=2))
            return 1

        rows = conn.execute(
            """
            SELECT sb.id::text AS bundle_id,
                   sb.bundle_index,
                   sb.vendor_name_raw,
                   sb.completeness_score::float AS completeness_score,
                   sb.hitl_required IS TRUE AS hitl_required,
                   COUNT(bd.id)::int AS document_count
            FROM supplier_bundles sb
            LEFT JOIN bundle_documents bd ON bd.bundle_id = sb.id
            WHERE sb.workspace_id = %s::uuid
            GROUP BY sb.id, sb.bundle_index, sb.vendor_name_raw,
                     sb.completeness_score, sb.hitl_required
            ORDER BY sb.bundle_index NULLS LAST, sb.id
            """,
            (wid,),
        ).fetchall()

    bundles = [dict(r) for r in rows]
    out = {
        "workspace": dict(ws),
        "bundle_count": len(bundles),
        "bundles": bundles,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    print(
        f"\n--- {len(bundles)} bundle(s) — comparer à la vérité terrain ---",
        file=sys.stderr,
    )
    for b in bundles:
        v = (b.get("vendor_name_raw") or "")[:72]
        print(
            f"  idx={b.get('bundle_index')} docs={b.get('document_count')} "
            f"complete={b.get('completeness_score')} hitl={b.get('hitl_required')}\n"
            f"    {v!r}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
