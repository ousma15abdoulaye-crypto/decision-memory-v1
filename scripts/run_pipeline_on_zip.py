#!/usr/bin/env python3
"""Exécute Pass -1 (ZIP → bundles) puis ``run_pipeline_v5`` (synchrone, sans ARQ).

Usage::
    export DATABASE_URL=...   # ou TEST_DATABASE_URL via tests/conftest
    python scripts/run_pipeline_on_zip.py --zip data/test_zip/test_offers.zip

Prérequis : migrations Alembic appliquées, ``langgraph`` installé, utilisateur
``admin`` en base (seed migration 004).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _cleanup(
    conn,
    *,
    workspace_id: str,
    case_id: str,
    committee_id: str,
) -> None:
    """Nettoyage sans toucher ``committee_events`` (append-only, DELETE interdit)."""
    with conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        cur.execute(
            "DELETE FROM committee_members WHERE committee_id = %s::uuid",
            (committee_id,),
        )
        cur.execute(
            "DELETE FROM committees WHERE committee_id = %s::uuid",
            (committee_id,),
        )
        cur.execute(
            "DELETE FROM criterion_assessments WHERE workspace_id = %s::uuid",
            (workspace_id,),
        )
        cur.execute(
            "DELETE FROM evaluation_documents WHERE workspace_id = %s::uuid",
            (workspace_id,),
        )
        cur.execute(
            "DELETE FROM offer_extractions WHERE workspace_id = %s::uuid",
            (workspace_id,),
        )
        cur.execute(
            "DELETE FROM bundle_documents WHERE workspace_id = %s::uuid",
            (workspace_id,),
        )
        cur.execute(
            "DELETE FROM supplier_bundles WHERE workspace_id = %s::uuid",
            (workspace_id,),
        )
        cur.execute(
            "DELETE FROM dao_criteria WHERE workspace_id = %s::uuid",
            (workspace_id,),
        )
        cur.execute(
            "DELETE FROM process_workspaces WHERE id = %s::uuid", (workspace_id,)
        )
        cur.execute("DELETE FROM cases WHERE id = %s", (case_id,))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--zip",
        type=Path,
        default=ROOT / "data" / "test_zip" / "test_offers.zip",
        help="Chemin du ZIP fournisseurs",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Conserver workspace / case / comité en base",
    )
    args = parser.parse_args()
    zpath = args.zip.resolve()
    if not zpath.is_file():
        raise SystemExit(f"ZIP introuvable : {zpath}")

    import psycopg
    from psycopg.rows import dict_row

    url = os.environ.get("DATABASE_URL", "").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    if not url:
        raise SystemExit("DATABASE_URL requis")

    from src.db.tenant_context import reset_rls_request_context, set_rls_is_admin
    from src.services.pipeline_v5_service import run_pipeline_v5
    from src.workers.arq_tasks import run_pass_minus_1

    case_id = str(uuid.uuid4())
    ws_id = str(uuid.uuid4())
    committee_id = str(uuid.uuid4())
    tenant_id: str
    owner_id: int

    conn = psycopg.connect(url, row_factory=dict_row, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.is_admin', 'true', true)")
            cur.execute("SELECT id FROM tenants WHERE code = %s LIMIT 1", ("sci_mali",))
            tr = cur.fetchone()
            if tr:
                tenant_id = str(tr["id"])
            else:
                tenant_id = str(uuid.uuid4())
                cur.execute(
                    "INSERT INTO tenants (id, code, name) VALUES (%s, %s, %s)",
                    (tenant_id, "sci_mali", "SCI Mali"),
                )
            cur.execute("SELECT id FROM users WHERE username = %s LIMIT 1", ("admin",))
            ur = cur.fetchone()
            if not ur:
                raise SystemExit(
                    "Utilisateur admin absent — appliquer les migrations (seed 004)."
                )
            owner_id = int(ur["id"])

            cur.execute(
                """
                INSERT INTO public.cases
                    (id, case_type, title, created_at, currency, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    case_id,
                    "test",
                    f"zip-run-{case_id[:8]}",
                    datetime.now(UTC).isoformat(),
                    "XOF",
                    "draft",
                ),
            )
            cur.execute(
                """
                INSERT INTO process_workspaces
                    (id, tenant_id, created_by, reference_code, title, process_type,
                     status, legacy_case_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    ws_id,
                    tenant_id,
                    owner_id,
                    f"ZIPRUN-{ws_id[:8]}",
                    f"ZIP run {ws_id[:8]}",
                    "devis_simple",
                    "draft",
                    case_id,
                ),
            )
            cur.execute(
                """
                INSERT INTO public.committees
                    (committee_id, case_id, org_id, committee_type, created_by, status)
                VALUES (%s::uuid, %s, %s, %s, %s, %s)
                """,
                (committee_id, case_id, "org-test", "achat", "script", "draft"),
            )
            for i in range(2):
                cid = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO public.dao_criteria
                        (id, workspace_id, categorie, critere_nom, description,
                         ponderation, type_reponse, seuil_elimination,
                         ordre_affichage, created_at, m16_criterion_code)
                    VALUES (%s, %s::uuid, %s, %s, %s, %s, %s, NULL, %s, NOW()::text, %s)
                    """,
                    (
                        cid,
                        ws_id,
                        "commercial",
                        f"Critère script {i}",
                        "desc",
                        0.5,
                        "quantitatif",
                        i,
                        f"SCRIPT_CRIT_{i}",
                    ),
                )
    finally:
        conn.close()

    print("Workspace ID:", ws_id)
    print("Case ID:", case_id)
    print("ZIP:", zpath)

    t_all = time.perf_counter()
    out_pass = asyncio.run(
        run_pass_minus_1(
            {},
            workspace_id=ws_id,
            tenant_id=tenant_id,
            zip_path=str(zpath),
        )
    )
    if out_pass.get("error"):
        if not args.no_cleanup:
            conn = psycopg.connect(url, row_factory=dict_row, autocommit=True)
            try:
                _cleanup(
                    conn, workspace_id=ws_id, case_id=case_id, committee_id=committee_id
                )
            finally:
                conn.close()
        raise SystemExit(f"Pass -1 échoué : {out_pass}")

    set_rls_is_admin(True)
    try:
        t0 = time.perf_counter()
        result = run_pipeline_v5(ws_id, force_m14=True)
        elapsed = time.perf_counter() - t0
    finally:
        reset_rls_request_context()

    total = time.perf_counter() - t_all

    conn = psycopg.connect(url, row_factory=dict_row, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.is_admin', 'true', true)")
            cur.execute(
                """
                SELECT COUNT(*)::int AS n FROM criterion_assessments
                WHERE workspace_id = %s::uuid
                """,
                (ws_id,),
            )
            n_assess = int(cur.fetchone()["n"])
    finally:
        conn.close()

    print(f"Pass-1 bundles: {len(out_pass.get('bundle_ids') or [])}")
    print(f"Pipeline V5 completed in {elapsed:.1f} seconds (run_pipeline_v5 only)")
    print(f"Total wall time (pass-1 + pipeline): {total:.1f} seconds")
    print("Pipeline completed:", result.completed)
    print("Assessments created (created+updated):", result.step_5_assessments_created)
    print("Criterion assessments rows:", n_assess)
    if result.error:
        print("Pipeline error:", result.error, "at", result.stopped_at)

    if not args.no_cleanup:
        conn = psycopg.connect(url, row_factory=dict_row, autocommit=True)
        try:
            _cleanup(
                conn, workspace_id=ws_id, case_id=case_id, committee_id=committee_id
            )
            print("Cleanup: workspace et artefacts supprimés.")
        finally:
            conn.close()


if __name__ == "__main__":
    main()
