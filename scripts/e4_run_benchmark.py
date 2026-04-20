#!/usr/bin/env python3
"""
P3.4 E4 — Benchmark post-merge (Option B : exécution humaine sur DB réelle).

Charge ``.env`` puis ``.env.local`` avant tout import ``src`` (pattern ``main.py``).
Résout ``process_workspaces`` via les mêmes critères que ``M14EvaluationRepository``
(``legacy_case_id`` exact, sinon ``id`` UUID).

Requêtes volumes dry-run : alignées sur les précontrôles de ``run_pipeline_v5``
(``src/services/pipeline_v5_service.py``) — source de vérité schéma côté code.

Usage::

    python scripts/e4_run_benchmark.py --workspace-reference CASE-28b05d85 --dry-run
    python scripts/e4_run_benchmark.py --workspace-id <uuid>
    python scripts/e4_run_benchmark.py --workspace-reference CASE-28b05d85 --runs 2
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.local", override=True)

from src.db import db_execute_one, get_connection
from src.db.tenant_context import reset_rls_request_context, set_rls_is_admin
from src.procurement.matrix_models import MatrixRow, MatrixSummary, RankStatus
from src.services.pipeline_v5_service import PipelineV5Result, run_pipeline_v5

OUTPUT_DIR = Path("rapports")

logger = logging.getLogger("e4_benchmark")


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
    )


def resolve_workspace_id(
    *,
    workspace_id: UUID | None,
    workspace_reference: str | None,
) -> str:
    """Résout ``process_workspaces.id`` (texte) depuis UUID ou référence métier."""
    if workspace_id is not None:
        wid = str(workspace_id)
        with get_connection() as conn:
            row = db_execute_one(
                conn,
                """
                SELECT id::text AS id
                FROM process_workspaces
                WHERE id = CAST(:wid AS uuid)
                LIMIT 1
                """,
                {"wid": wid},
            )
        if not row or not row.get("id"):
            raise SystemExit(f"ERREUR: workspace introuvable pour --workspace-id={wid}")
        logger.info("Workspace résolu depuis UUID: %s", row["id"])
        return row["id"]

    if workspace_reference is None or not workspace_reference.strip():
        raise SystemExit(
            "ERREUR: fournir --workspace-id ou --workspace-reference",
        )

    ref = workspace_reference.strip()
    try:
        parsed = UUID(ref)
    except ValueError:
        parsed = None

    if parsed is not None:
        return resolve_workspace_id(workspace_id=parsed, workspace_reference=None)

    with get_connection() as conn:
        row = db_execute_one(
            conn,
            """
            SELECT id::text AS id
            FROM process_workspaces
            WHERE legacy_case_id = :ref
            LIMIT 1
            """,
            {"ref": ref},
        )
    if row and row.get("id"):
        logger.info("Workspace résolu depuis legacy_case_id=%r → %s", ref, row["id"])
        return row["id"]

    raise SystemExit(
        f"ERREUR: aucun process_workspaces pour legacy_case_id={ref!r} "
        "(essayez --workspace-id avec l'UUID complet).",
    )


def collect_dry_run_metrics(workspace_id: str) -> dict[str, Any]:
    """Compteurs read-only alignés sur les préchecks pipeline V5."""
    wid = workspace_id
    with get_connection() as conn:
        ws = db_execute_one(
            conn,
            """
            SELECT w.id::text AS id, w.legacy_case_id::text AS legacy_case_id,
                   lower(t.code::text) AS tenant_code
            FROM process_workspaces w
            JOIN tenants t ON t.id = w.tenant_id
            WHERE w.id = CAST(:wid AS uuid)
            """,
            {"wid": wid},
        )
        ndocs = db_execute_one(
            conn,
            """
            SELECT COUNT(*)::int AS n
            FROM bundle_documents
            WHERE workspace_id = CAST(:wid AS uuid)
              AND raw_text IS NOT NULL
              AND trim(raw_text) <> ''
            """,
            {"wid": wid},
        )
        ndao = db_execute_one(
            conn,
            """
            SELECT COUNT(*)::int AS n
            FROM dao_criteria
            WHERE workspace_id = CAST(:wid AS uuid)
            """,
            {"wid": wid},
        )
        nbundles = db_execute_one(
            conn,
            """
            SELECT COUNT(DISTINCT bundle_id)::int AS n
            FROM bundle_documents
            WHERE workspace_id = CAST(:wid AS uuid)
            """,
            {"wid": wid},
        )
        neval = db_execute_one(
            conn,
            """
            SELECT COUNT(*)::int AS n
            FROM evaluation_documents
            WHERE workspace_id = CAST(:wid AS uuid)
            """,
            {"wid": wid},
        )
        nassess = db_execute_one(
            conn,
            """
            SELECT COUNT(*)::int AS n
            FROM criterion_assessments
            WHERE workspace_id = CAST(:wid AS uuid)
            """,
            {"wid": wid},
        )
    return {
        "workspace_row": ws,
        "bundle_documents_nonempty_text": ndocs.get("n") if ndocs else None,
        "dao_criteria": ndao.get("n") if ndao else None,
        "distinct_bundle_ids_bundle_documents": nbundles.get("n") if nbundles else None,
        "evaluation_documents": neval.get("n") if neval else None,
        "criterion_assessments": nassess.get("n") if nassess else None,
    }


def _stable_matrix_fingerprint(result: PipelineV5Result) -> list[dict[str, Any]]:
    """Empreinte stable pour comparaison idempotence (hors ``pipeline_run_id``)."""
    out: list[dict[str, Any]] = []
    for row in result.matrix_rows:
        d = row.model_dump(mode="json")
        d.pop("pipeline_run_id", None)
        d.pop("matrix_revision_id", None)
        out.append(
            {
                "bundle_id": d.get("bundle_id"),
                "vendor_id": d.get("vendor_id"),
                "rank_status": d.get("rank_status"),
                "rank": d.get("rank"),
                "eligibility_status": d.get("eligibility_status"),
                "total_score_system": d.get("total_score_system"),
            }
        )
    out.sort(key=lambda x: (x.get("bundle_id") or "", x.get("vendor_id") or ""))
    return out


def verify_invariants(result: PipelineV5Result) -> dict[str, Any]:
    """Contrôles V1–V6 pragmatiques sur ``PipelineV5Result`` (post-run)."""
    checks: dict[str, Any] = {}

    if not result.completed:
        checks["V_run_completed"] = {
            "ok": False,
            "detail": {"error": result.error, "stopped_at": result.stopped_at},
        }
        return checks

    checks["V_run_completed"] = {"ok": True, "detail": {}}

    rows = result.matrix_rows
    summary = result.matrix_summary

    if summary is None:
        checks["V2_matrix_summary_present"] = {"ok": False, "detail": "summary None"}
    else:
        checks["V2_matrix_summary_present"] = {"ok": True, "detail": {}}

    if not rows:
        checks["V2_rows_non_empty"] = {"ok": False, "detail": "0 matrix_rows"}
    else:
        checks["V2_rows_non_empty"] = {"ok": True, "detail": {"n": len(rows)}}
        for row in rows:
            MatrixRow.model_validate(row.model_dump())

    if summary is not None and rows:
        by_status = Counter(r.rank_status for r in rows)
        checks["V1_rank_status_counts_vs_rows"] = {
            "ok": sum(by_status.values()) == len(rows),
            "detail": dict(by_status),
        }
        checks["V1_summary_rank_buckets"] = {
            "ok": (
                summary.count_ranked == by_status.get(RankStatus.RANKED, 0)
                and summary.count_excluded == by_status.get(RankStatus.EXCLUDED, 0)
                and summary.count_pending_rank == by_status.get(RankStatus.PENDING, 0)
                and summary.count_not_comparable_rank
                == by_status.get(RankStatus.NOT_COMPARABLE, 0)
                and summary.count_incomplete_rank
                == by_status.get(RankStatus.INCOMPLETE, 0)
            ),
            "detail": {
                "summary": {
                    "count_ranked": summary.count_ranked,
                    "count_excluded": summary.count_excluded,
                    "count_pending_rank": summary.count_pending_rank,
                    "count_not_comparable_rank": summary.count_not_comparable_rank,
                    "count_incomplete_rank": summary.count_incomplete_rank,
                },
                "rows": dict(by_status),
            },
        }
        checks["V1_total_bundles_vs_rows"] = {
            "ok": summary.total_bundles == len(rows),
            "detail": {"total_bundles": summary.total_bundles, "n_rows": len(rows)},
        }

    checks["V6_summary_model"] = {"ok": False, "detail": "skipped"}
    if summary is not None:
        MatrixSummary.model_validate(summary.model_dump())
        checks["V6_summary_model"] = {"ok": True, "detail": {}}

    checks["V3_idempotence"] = {"ok": None, "detail": "voir second run"}
    checks["V4_explicability"] = {"ok": None, "detail": "non automatisé E4 script"}
    checks["V5_flags"] = {"ok": None, "detail": "non automatisé E4 script"}

    return checks


def serialize_artifacts(
    result: PipelineV5Result,
    workspace_id: str,
    *,
    tag: str,
) -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = str(workspace_id).replace("-", "")[:12]
    rows_path = OUTPUT_DIR / f"p34_case_{slug}_matrix_rows.json"
    summary_path = OUTPUT_DIR / f"p34_case_{slug}_matrix_summary.json"
    meta_path = OUTPUT_DIR / f"p34_case_{slug}_run_meta.json"

    rows_payload = [r.model_dump(mode="json") for r in result.matrix_rows]
    summary_payload = (
        result.matrix_summary.model_dump(mode="json")
        if result.matrix_summary
        else None
    )
    meta = {
        "tag": tag,
        "workspace_id": workspace_id,
        "completed": result.completed,
        "error": result.error,
        "stopped_at": result.stopped_at,
        "duration_seconds": result.duration_seconds,
        "captured_at": datetime.now(tz=UTC).isoformat(),
    }

    rows_path.write_text(json.dumps(rows_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    summary_path.write_text(
        json.dumps(summary_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "matrix_rows_path": str(rows_path),
        "matrix_summary_path": str(summary_path),
        "meta_path": str(meta_path),
    }


def _print_report_blocks(
    *,
    workspace_id: str,
    metrics: dict[str, Any] | None,
    result: PipelineV5Result | None,
    inv: dict[str, Any] | None,
    idem_ok: bool | None,
    artifacts: dict[str, Any] | None,
) -> None:
    """Huit blocs console structurés (synthèse CTO E4)."""
    blocks = [
        ("1_workspace", {"workspace_id": workspace_id}),
        ("2_precheck_metrics", metrics or {}),
        ("3_pipeline_status", (result.model_dump(mode="json") if result else {})),
        ("4_matrix_rows_count", {"n": len(result.matrix_rows) if result else 0}),
        (
            "5_rank_distribution",
            (
                {str(k): v for k, v in Counter(r.rank_status for r in result.matrix_rows).items()}
                if result and result.matrix_rows
                else {}
            ),
        ),
        ("6_invariants", inv or {}),
        ("7_idempotence_stable_fingerprint", {"ok": idem_ok}),
        ("8_artifact_paths", artifacts or {}),
    ]
    for name, payload in blocks:
        print(f"=== {name} ===", flush=True)
        print(json.dumps(payload, indent=2, default=str, ensure_ascii=False), flush=True)


def main() -> int:
    _configure_logging()
    parser = argparse.ArgumentParser(description="P3.4 E4 benchmark post-merge (Option B)")
    parser.add_argument("--workspace-reference", default=None, help="legacy_case_id exact")
    parser.add_argument("--workspace-id", type=UUID, default=None)
    parser.add_argument("--runs", type=int, default=2, help="runs pour idempotence (défaut 2)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Volumes + résolution workspace uniquement (pas de pipeline)",
    )
    args = parser.parse_args()

    if not args.workspace_reference and args.workspace_id is None:
        print("ERREUR: --workspace-reference ou --workspace-id requis", file=sys.stderr)
        return 2

    reset_rls_request_context()
    set_rls_is_admin(True)

    try:
        wid = resolve_workspace_id(
            workspace_id=args.workspace_id,
            workspace_reference=args.workspace_reference,
        )
        metrics = collect_dry_run_metrics(wid)
        logger.info("Métriques dry-run: %s", json.dumps(metrics, default=str))

        if args.dry_run:
            _print_report_blocks(
                workspace_id=wid,
                metrics=metrics,
                result=None,
                inv=None,
                idem_ok=None,
                artifacts=None,
            )
            return 0

        results: list[PipelineV5Result] = []
        for i in range(max(1, args.runs)):
            logger.info("Pipeline run %s/%s", i + 1, args.runs)
            results.append(run_pipeline_v5(wid, force_m14=False))

        last = results[-1]
        inv = verify_invariants(last)

        fingerprints = [_stable_matrix_fingerprint(r) for r in results]
        if len(fingerprints) >= 2:
            idem_ok = fingerprints[0] == fingerprints[1]
        else:
            idem_ok = None

        inv["V3_idempotence"] = {
            "ok": idem_ok,
            "detail": {"runs": len(fingerprints)},
        }

        artifacts = serialize_artifacts(last, wid, tag=f"run_{len(results)}")

        _print_report_blocks(
            workspace_id=wid,
            metrics=metrics,
            result=last,
            inv=inv,
            idem_ok=idem_ok,
            artifacts=artifacts,
        )

        inv_failed = any(
            isinstance(v, dict) and v.get("ok") is False
            for v in inv.values()
        )
        if not last.completed or inv_failed:
            return 1
        return 0
    finally:
        reset_rls_request_context()


if __name__ == "__main__":
    raise SystemExit(main())
