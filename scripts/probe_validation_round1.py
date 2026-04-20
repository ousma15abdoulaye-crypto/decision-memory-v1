#!/usr/bin/env python3
"""Validation Round 1 — R1.2 suppliers, R1.4 idempotence, M13, matrix, assessments."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import psycopg  # noqa: E402

WID = "f1a6edfb-ac50-4301-a1a9-7a80053c632a"
CASE_ID = "28b05d85-62f1-4101-aaec-96bac40905cd"
EVAL_DOC_ID_HINT = "aa49c56f-7485-495e-9ede-39f95c787898"
CUTOFF = "2026-04-14 16:00:00"


def dsn() -> str:
    return os.environ.get("DATABASE_URL") or os.environ["RAILWAY_DATABASE_URL"]


def main() -> int:
    conn = psycopg.connect(dsn())
    cur = conn.cursor()

    print("=== ÉTAPE 1 — OFFER EXTRACTIONS ===")
    cur.execute(
        """
        SELECT supplier_name,
               (extracted_data_json::jsonb)->>'extraction_ok' AS ok,
               (extracted_data_json::jsonb)->>'document_role' AS role,
               LEFT(extracted_data_json::text, 150) AS preview
        FROM offer_extractions
        WHERE workspace_id = %s
        ORDER BY created_at
        """,
        (WID,),
    )
    rows_oe = cur.fetchall()
    for r in rows_oe:
        print(r)

    print()
    print("=== ÉTAPE 1 — SUPPLIER BUNDLES ===")
    cur.execute(
        """
        SELECT id, vendor_name_raw AS supplier_name
        FROM supplier_bundles
        WHERE workspace_id = %s
        """,
        (WID,),
    )
    rows_sb = cur.fetchall()
    for r in rows_sb:
        print(r)

    conn.close()

    # Idempotence pipeline
    print()
    print("=== ÉTAPE 2 — PIPELINE force_m14=False ===")
    from src.services.pipeline_v5_service import run_pipeline_v5  # noqa: E402

    result = run_pipeline_v5(WID, force_m14=False)
    result_json = json.dumps(result.model_dump(), indent=2, default=str)
    print(result_json)

    conn = psycopg.connect(dsn())
    cur = conn.cursor()
    print()
    print("=== ÉTAPE 2 — EVAL DOCS COUNT ===")
    cur.execute(
        "SELECT COUNT(*) FROM evaluation_documents WHERE workspace_id = %s", (WID,)
    )
    eval_count = cur.fetchone()[0]
    print("eval_docs total:", eval_count)
    cur.execute(
        """
        SELECT id, created_at
        FROM evaluation_documents
        WHERE workspace_id = %s
        ORDER BY created_at DESC
        LIMIT 5
        """,
        (WID,),
    )
    eval_recent = cur.fetchall()
    for r in eval_recent:
        print(r)

    print()
    print("=== ÉTAPE 3 — M13 PROFILE ===")
    cur.execute(
        """
        SELECT payload
        FROM m13_regulatory_profile_versions
        WHERE case_id::text = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (CASE_ID,),
    )
    row_m13 = cur.fetchone()
    if not row_m13:
        print("(aucune ligne m13_regulatory_profile_versions pour ce case_id)")
        p = {}
    else:
        raw = row_m13[0]
        p = raw if isinstance(raw, dict) else json.loads(raw)
    print("=== PROFILE INDEX ===")
    print(json.dumps(p.get("profile_index", {}), indent=2))
    print()
    print("=== M13B HOOKS ===")
    m13b = p.get("m13b", {})
    if not isinstance(m13b, dict):
        print("m13b:", m13b)
    else:
        for k, v in m13b.items():
            print(f"{k}: {len(v) if isinstance(v, list) else v}")

    print()
    print("=== ÉTAPE 4 — SCORES MATRIX ===")
    sm: dict = {}
    matrix_id: str | None = None
    cur.execute(
        "SELECT id::text FROM evaluation_documents WHERE id = %s::uuid",
        (EVAL_DOC_ID_HINT,),
    )
    ed_row = cur.fetchone()
    matrix_id = EVAL_DOC_ID_HINT if ed_row else None
    if not matrix_id and eval_recent:
        matrix_id = str(eval_recent[0][0])
    if matrix_id:
        cur.execute(
            "SELECT scores_matrix FROM evaluation_documents WHERE id = %s::uuid",
            (matrix_id,),
        )
        sm_row = cur.fetchone()
        if sm_row:
            sm = sm_row[0] if isinstance(sm_row[0], dict) else json.loads(sm_row[0])
            print("(eval_document id utilisé:", matrix_id, ")")
            print("=== TOP-LEVEL KEYS ===")
            keys = list(sm.keys())[:20]
            print(keys)
            print()
            for k in list(sm.keys())[:3]:
                v = sm[k]
                if isinstance(v, dict):
                    print(f"=== {k} ===")
                    print(json.dumps(v, indent=2, default=str)[:500])
        else:
            print("scores_matrix introuvable pour", matrix_id)
    else:
        print("Aucun evaluation_document pour dériver matrix_id")

    print()
    print("=== ÉTAPE 5 — CRITERION ASSESSMENTS ===")
    cur.execute(
        """
        SELECT ca.criterion_key, ca.dao_criterion_id, sb.vendor_name_raw,
               ca.cell_json->>'score' AS score, ca.assessment_status, ca.confidence
        FROM criterion_assessments ca
        LEFT JOIN supplier_bundles sb ON sb.id = ca.bundle_id
        WHERE ca.workspace_id = %s
          AND ca.created_at > %s
        ORDER BY ca.criterion_key, sb.vendor_name_raw
        LIMIT 30
        """,
        (WID, CUTOFF),
    )
    sample = cur.fetchall()
    for r in sample:
        print(r)
    print()
    cur.execute(
        """
        SELECT COUNT(*) AS total,
               COUNT(DISTINCT criterion_key) AS criteria,
               COUNT(DISTINCT bundle_id) AS suppliers
        FROM criterion_assessments
        WHERE workspace_id = %s
          AND created_at > %s
        """,
        (WID, CUTOFF),
    )
    totals = cur.fetchone()
    print("Totals:", totals)

    conn.close()

    # --- Rapport synthèse ---
    oe_names = [r[0] for r in rows_oe if r[0]]
    sb_names = [r[1] for r in rows_sb if r[1]]
    conn_r = psycopg.connect(dsn())
    cur_r = conn_r.cursor()
    cur_r.execute(
        """
        SELECT oe.bundle_id::text, oe.supplier_name, sb.vendor_name_raw
        FROM offer_extractions oe
        JOIN supplier_bundles sb ON sb.id = oe.bundle_id
        WHERE oe.workspace_id = %s
        ORDER BY oe.created_at
        """,
        (WID,),
    )
    bundle_align = cur_r.fetchall()
    conn_r.close()
    gap = any(
        (a[1] or "").strip() != (a[2] or "").strip() for a in bundle_align
    ) or len(bundle_align) != len(rows_oe)

    pi = p.get("profile_index") or {}
    fw = pi.get("framework")
    proc = pi.get("procedure_type")
    rules_applied = pi.get("rules_applied")
    if rules_applied is None:
        rules_n = 0
    elif isinstance(rules_applied, list):
        rules_n = len(rules_applied)
    else:
        rules_n = 1

    m13b_filled = isinstance(m13b, dict) and any(
        (isinstance(v, list) and len(v) > 0) or (v not in (None, "", [], {}))
        for v in m13b.values()
    )

    top_keys = list(sm.keys())[:20] if sm else []
    key_kind = "mixte / vide"
    if top_keys:
        uuid_re = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.I,
        )
        if all(
            isinstance(k, str) and uuid_re.match(k) for k in top_keys if k != "m14_meta"
        ):
            key_kind = "principalement UUID (ancienne matrice par bundle)"
        elif "offer_evaluations" in sm:
            key_kind = "EvaluationReport (offer_evaluations, case_id, …)"
        else:
            key_kind = "texte / structure libre"

    ready = result.completed and eval_count >= 1 and (totals[0] or 0) > 0 and not gap

    print()
    print("=== RAPPORT VALIDATION ROUND 1 ===")
    print()
    print("R1.2 SUPPLIERS :")
    print(f"  offer_extractions.supplier_name : {oe_names}")
    print(f"  supplier_bundles.supplier_name : {sb_names}")
    print(f"  Écart : {'oui' if gap else 'non'}")
    print()
    print("R1.4 IDEMPOTENCE :")
    print("  Résultat avec force_m14=False (JSON) :")
    for line in result_json.splitlines():
        print("   ", line)
    print(f"  Nombre eval_docs total : {eval_count}")
    dup = eval_count > 1
    print(f"  Doublons : {'oui' if dup else 'non'} (plus d'un document d'évaluation)")
    print()
    print("M13 PROFILE :")
    print(f"  framework : {fw}")
    print(f"  procedure_type : {proc}")
    print(f"  rules_applied count : {rules_n}")
    print(f"  M13B hooks : {'remplis' if m13b_filled else 'vides ou partiels'}")
    print()
    print("SCORES MATRIX :")
    print(f"  Structure : {key_kind}")
    print(f"  Clés (extrait) : {top_keys}")
    print()
    print("ASSESSMENTS :")
    print(f"  Total créés (après cutoff) : {totals[0]}")
    print(f"  Critères distincts : {totals[1]}")
    print(f"  Fournisseurs distincts : {totals[2]}")
    print(f"  Échantillon : {sample[:5]}")
    print()
    print(
        f"PRÊT POUR ROUND 2 : {'oui' if ready else 'non'} — completed={result.completed}, gap={gap}"
    )
    print()
    print("=== FIN RAPPORT ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
