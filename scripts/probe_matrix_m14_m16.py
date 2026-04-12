#!/usr/bin/env python3
"""Sonde lecture seule — matrice dashboard (M14 JSON) vs lignes M16 relationnelles.

Compare la forme de ``evaluation_documents.scores_matrix`` aux tables
``supplier_bundles``, ``dao_criteria``, ``criterion_assessments``.

Usage ::
  python scripts/probe_matrix_m14_m16.py <workspace_uuid>
  python scripts/probe_matrix_m14_m16.py --list 10

Variables : ``DATABASE_URL`` (fichiers ``.env.local`` puis ``.env``, override local).

Sortie : JSON sur stdout (détails) + lignes résumé lisibles sur stderr.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

_FORBIDDEN = frozenset(
    {
        "winner",
        "rank",
        "recommendation",
        "be" + "st_offer",
        "selected_vendor",
    }
)


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


def _relevant_items(sm: dict[str, Any]) -> list[tuple[str, Any]]:
    return [
        (k, v)
        for k, v in sm.items()
        if isinstance(k, str) and k not in _FORBIDDEN and not k.startswith("_")
    ]


def detect_m14_nested(sm: dict[str, Any] | None) -> bool:
    """True si { bundle: { criterion: { score|signal|confidence }}}."""
    if not sm or not isinstance(sm, dict):
        return False
    items = _relevant_items(sm)
    if not items:
        return False
    for _, v in items:
        if not isinstance(v, dict):
            return False
    for _, v in items:
        for iv in v.values():
            if isinstance(iv, dict) and any(
                x in iv for x in ("score", "signal", "confidence")
            ):
                return True
    return False


def analyze_scores_matrix(sm: Any) -> dict[str, Any]:
    if not isinstance(sm, dict):
        return {
            "error": "scores_matrix_missing_or_not_object",
            "raw_type": type(sm).__name__,
        }
    items = _relevant_items(sm)
    bundle_keys = [k for k, _ in items]
    m14 = detect_m14_nested(sm)
    crit_ids: set[str] = set()
    cells = 0
    if m14:
        for _, row in items:
            if not isinstance(row, dict):
                continue
            for ck, cell in row.items():
                if not isinstance(ck, str) or ck in _FORBIDDEN:
                    continue
                if isinstance(cell, dict) and any(
                    x in cell for x in ("score", "signal", "confidence")
                ):
                    crit_ids.add(ck)
                    cells += 1
    return {
        "shape_guess": "m14_bundle_x_criterion" if m14 else "legacy_or_other",
        "top_level_key_count": len(bundle_keys),
        "bundle_key_sample": bundle_keys[:8],
        "criterion_key_count": len(crit_ids),
        "criterion_key_sample": sorted(crit_ids)[:12],
        "m14_like_cells_count": cells,
    }


def main() -> int:
    _load_env()
    parser = argparse.ArgumentParser(description="Probe M14 JSON vs M16 DB rows.")
    parser.add_argument("workspace_id", nargs="?", help="UUID workspace")
    parser.add_argument(
        "--list",
        type=int,
        metavar="N",
        help="Lister les N derniers workspaces (pas d’UUID requis)",
    )
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
    out: dict[str, Any] = {"database_url_host": conninfo.split("@")[-1][:80]}

    with psycopg.connect(conninfo, row_factory=dict_row) as conn:
        conn.autocommit = True
        if args.list:
            rows = conn.execute(
                """
                SELECT id::text AS id, reference_code, title, status,
                       created_at::text AS created_at
                FROM process_workspaces
                ORDER BY created_at DESC NULLS LAST
                LIMIT %s
                """,
                (args.list,),
            ).fetchall()
            out["workspaces_recent"] = [dict(r) for r in rows]
            print(json.dumps(out, indent=2, ensure_ascii=False))
            print("\n--- Choisis un id et relance : ---", file=sys.stderr)
            for r in rows:
                print(f"  {r['id']}  {r.get('reference_code')!r}", file=sys.stderr)
            return 0

        wid = args.workspace_id
        if not wid:
            print("Indique workspace_uuid ou --list N", file=sys.stderr)
            return 2

        ws = conn.execute(
            "SELECT id::text, reference_code, title, status, tenant_id::text AS tenant_id "
            "FROM process_workspaces WHERE id = %s::uuid",
            (wid,),
        ).fetchone()
        if not ws:
            out["error"] = "workspace_not_found"
            print(json.dumps(out, indent=2, ensure_ascii=False))
            return 1
        out["workspace"] = dict(ws)

        ed = conn.execute(
            """
            SELECT id::text, created_at::text AS created_at, version, status,
                   scores_matrix
            FROM evaluation_documents
            WHERE workspace_id = %s::uuid
            ORDER BY created_at DESC NULLS LAST
            LIMIT 1
            """,
            (wid,),
        ).fetchone()

        sm = (ed or {}).get("scores_matrix")
        if isinstance(sm, str):
            try:
                sm = json.loads(sm)
            except json.JSONDecodeError:
                sm = None

        matrix_analysis = analyze_scores_matrix(sm)
        out["evaluation_document"] = (
            {
                "id": ed.get("id"),
                "created_at": ed.get("created_at"),
                "version": ed.get("version"),
                "status": ed.get("status"),
            }
            if ed
            else None
        )
        out["scores_matrix_analysis"] = matrix_analysis

        bundles = conn.execute(
            """
            SELECT id::text AS id, vendor_name_raw, bundle_index
            FROM supplier_bundles
            WHERE workspace_id = %s::uuid
            ORDER BY bundle_index NULLS LAST, id
            """,
            (wid,),
        ).fetchall()
        bundle_ids = {str(r["id"]) for r in bundles}
        out["supplier_bundles"] = {"count": len(bundles), "ids": sorted(bundle_ids)}

        dc = conn.execute(
            """
            SELECT id::text AS id, critere_nom, ponderation,
                   is_eliminatory IS TRUE AS is_eliminatory
            FROM dao_criteria
            WHERE workspace_id = %s::uuid
            ORDER BY created_at NULLS LAST, id
            """,
            (wid,),
        ).fetchall()
        crit_ids_db = {str(r["id"]) for r in dc}
        out["dao_criteria"] = {"count": len(dc), "ids_sample": sorted(crit_ids_db)[:15]}

        ca = conn.execute(
            """
            SELECT COUNT(*)::int AS n,
                   COUNT(DISTINCT bundle_id)::int AS bundles,
                   COUNT(DISTINCT criterion_key)::int AS criterion_keys
            FROM criterion_assessments
            WHERE workspace_id = %s::uuid
            """,
            (wid,),
        ).fetchone()
        out["criterion_assessments_m16"] = dict(ca) if ca else {}

        # Comparaisons clés
        sm_dict = sm if isinstance(sm, dict) else {}
        matrix_bundle_ids = {k for k, _ in _relevant_items(sm_dict)}
        matrix_crit_ids: set[str] = set()
        if matrix_analysis.get("shape_guess") == "m14_bundle_x_criterion":
            for _, row in _relevant_items(sm_dict):
                if not isinstance(row, dict):
                    continue
                for ck, cell in row.items():
                    if (
                        isinstance(ck, str)
                        and isinstance(cell, dict)
                        and any(x in cell for x in ("score", "signal", "confidence"))
                    ):
                        matrix_crit_ids.add(ck)

        only_in_matrix_b = (
            matrix_bundle_ids - bundle_ids if matrix_bundle_ids else set()
        )
        only_in_db_b = bundle_ids - matrix_bundle_ids if matrix_bundle_ids else set()
        is_m14 = matrix_analysis.get("shape_guess") == "m14_bundle_x_criterion"
        if is_m14:
            only_in_matrix_c = matrix_crit_ids - crit_ids_db
            only_in_db_c = crit_ids_db - matrix_crit_ids
            crit_mismatch = len(only_in_matrix_c) + len(only_in_db_c)
        else:
            only_in_matrix_c = set()
            only_in_db_c = set()
            crit_mismatch = 0

        out["alignment"] = {
            "matrix_looks_m14_nested": is_m14,
            "bundles_only_in_scores_matrix": sorted(only_in_matrix_b)[:20],
            "bundles_only_in_db": sorted(only_in_db_b)[:20],
            "criteria_only_in_scores_matrix": sorted(only_in_matrix_c)[:20],
            "criteria_only_in_dao_criteria": sorted(only_in_db_c)[:20],
            "bundles_mismatch_count": len(only_in_matrix_b) + len(only_in_db_b),
            "criteria_mismatch_count": crit_mismatch,
            "criteria_comparison_note": (
                None
                if is_m14
                else "ignorée (scores_matrix non M14 imbriqué — clés critère indéterminées)"
            ),
        }

        # Échantillon M16 (bundle, criterion_key) pour œil humain
        sample_rows = conn.execute(
            """
            SELECT bundle_id::text AS bundle_id, criterion_key,
                   assessment_status,
                   cell_json->>'score' AS score_txt,
                   confidence::text AS confidence
            FROM criterion_assessments
            WHERE workspace_id = %s::uuid
            ORDER BY bundle_id, criterion_key
            LIMIT 24
            """,
            (wid,),
        ).fetchall()
        out["m16_sample_rows"] = [dict(r) for r in sample_rows]

    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))

    print("\n=== Résumé ===", file=sys.stderr)
    print(
        f"Forme scores_matrix : {matrix_analysis.get('shape_guess')}",
        file=sys.stderr,
    )
    print(
        f"Bundles DB={len(bundle_ids)} | "
        f"Critères dao_criteria={len(crit_ids_db)} | "
        f"Lignes M16={out['criterion_assessments_m16'].get('n', 0)}",
        file=sys.stderr,
    )
    al = out["alignment"]
    if al.get("matrix_looks_m14_nested"):
        print(
            f"Décalages clés : bundles {al['bundles_mismatch_count']} | "
            f"critères {al['criteria_mismatch_count']}",
            file=sys.stderr,
        )
        if al["criteria_mismatch_count"] or al["bundles_mismatch_count"]:
            print(
                "→ Corriger : aligner IDs matrix / supplier_bundles / dao_criteria, "
                "ou resynchroniser M14 / initialize-from-m14 + m14_bridge.",
                file=sys.stderr,
            )
    else:
        print(
            "Matrice non détectée comme M14 imbriquée — la grille dashboard peut "
            "mal interpréter les lignes/colonnes (voir docs/ops/MATRICE_…).",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
