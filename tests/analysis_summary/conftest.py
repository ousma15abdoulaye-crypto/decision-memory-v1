"""
tests/analysis_summary/conftest.py

Fixtures spécifiques analysis_summary.
Réutilise db_conn et case_factory depuis tests/conftest.py.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import pytest


@pytest.fixture
def pipeline_run_factory(db_conn, case_factory):
    """
    Crée un pipeline_run avec CAS v1 minimal valide dans result_jsonb.
    Retourne {pipeline_run_id: str, case_id: str}.

    Structure CAS v1 conforme ADR-0012.
    """

    def _factory(status: str = "partial_complete") -> dict:
        case_id = case_factory("XOF")
        run_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        cas_v1 = {
            "cas_version": "v1",
            "case_id": case_id,
            "pipeline_run_id": run_id,
            "generated_at": now,
            "pipeline": {
                "name": "A",
                "mode": "partial",
                "status": status,
            },
            "readiness": {
                "analysis_ready": status == "partial_complete",
                "export_ready": False,
                "cba_ready": False,
                "pv_ready": False,
                "blockers": (
                    [] if status == "partial_complete" else ["SCORING_NO_CRITERIA"]
                ),
                "warnings": [],
            },
            "case_context": {
                "id": case_id,
                "currency": "XOF",
                "title": "Dossier test M12",
                "case_type": "appel_offre",
            },
            "documents": {
                "dao_present": True,
                "offers_count": 2,
                "class_a_compatible": True,
            },
            "criteria": {
                "count_total": 3,
                "count_eliminatory": 1,
                "categories": {
                    "commercial": 2,
                    "capacity": 1,
                    "sustainability": 0,
                    "essentials": 0,
                },
            },
            "normalization": {
                "status": "ok",
                "coverage_ratio": 0.95,
                "human_flags_count": 0,
            },
            "scoring": {
                "status": "ok",
                "score_run_id": str(uuid.uuid4()),
                "scoring_version": "V3.3.2",
            },
            "exports": {
                "cba": {"status": "not_implemented_yet"},
                "pv": {"status": "not_implemented_yet"},
            },
        }

        with db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.pipeline_runs (
                    pipeline_run_id, case_id, pipeline_type, mode, status,
                    started_at, finished_at, duration_ms, triggered_by,
                    result_jsonb, error_jsonb, created_at
                ) VALUES (
                    %s, %s, 'A', 'partial', %s,
                    NOW(), NOW(), 100, 'test_m12_factory',
                    %s::jsonb, '[]'::jsonb, NOW()
                )
                """,
                (run_id, case_id, status, json.dumps(cas_v1)),
            )

        return {"pipeline_run_id": run_id, "case_id": case_id}

    yield _factory
