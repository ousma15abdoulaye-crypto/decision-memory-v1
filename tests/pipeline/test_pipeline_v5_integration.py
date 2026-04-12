"""Intégration pipeline V5 — DB, ZIP embarqué, performance, pré-requis CI.

- Migrations Alembic : fixture session (ce module uniquement).
- ``TEST_DATABASE_URL`` peut remplacer ``DATABASE_URL`` (voir ``tests/conftest.py``).
- Placé sous ``tests/pipeline/`` pour réutiliser ``conftest.py`` sans ``pytest_plugins``
  (évite double enregistrement avec la collecte globale).
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PERF_REPORT_PATH = REPO_ROOT / "performance_report.json"

from src.couche_a.extraction_models import (  # noqa: E402
    ExtractionField,
    TDRExtractionResult,
    Tier,
)
from src.db.tenant_context import (  # noqa: E402
    reset_rls_request_context,
    set_rls_is_admin,
)


@pytest.fixture(scope="session", autouse=True)
def _alembic_upgrade_pipeline_v5_session() -> None:
    """Applique ``alembic upgrade head`` une fois pour ce fichier de tests."""
    if os.environ.get("DMS_SKIP_SESSION_ALEMBIC", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        yield
        return
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        check=False,
    )
    if proc.returncode != 0:
        pytest.fail(
            "alembic upgrade head a échoué — impossible d'exécuter les tests pipeline V5.\n"
            f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
        )
    yield


def _cleanup_v5_artifacts(db_conn, *, ws_id: str, committee_id: str) -> None:
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        cur.execute(
            "DELETE FROM criterion_assessments WHERE workspace_id = %s::uuid",
            (ws_id,),
        )
        cur.execute(
            "DELETE FROM evaluation_documents WHERE workspace_id = %s::uuid",
            (ws_id,),
        )
        cur.execute(
            "DELETE FROM offer_extractions WHERE workspace_id = %s::uuid",
            (ws_id,),
        )
        cur.execute(
            "DELETE FROM bundle_documents WHERE workspace_id = %s::uuid",
            (ws_id,),
        )
        cur.execute(
            "DELETE FROM supplier_bundles WHERE workspace_id = %s::uuid",
            (ws_id,),
        )
        cur.execute(
            "DELETE FROM committee_members WHERE committee_id = %s::uuid",
            (committee_id,),
        )
        cur.execute(
            "DELETE FROM committees WHERE committee_id = %s::uuid",
            (committee_id,),
        )


@pytest.mark.integration
def test_resolve_criterion_id_async(db_conn, pipeline_case_with_dao_and_offers) -> None:
    """``resolve_criterion_id`` retrouve ``dao_criteria.id`` via ``m16_criterion_code``."""
    from src.db import get_connection
    from src.services.m16_backfill import resolve_criterion_id

    case_id = pipeline_case_with_dao_and_offers
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT dc.id::text AS cid, pw.id::text AS ws
            FROM dao_criteria dc
            JOIN process_workspaces pw ON dc.workspace_id = pw.id
            WHERE pw.legacy_case_id = %s
            LIMIT 1
            """,
            (case_id,),
        )
        row = cur.fetchone()
        assert row is not None
        crit_id = row["cid"]
        ws_id = row["ws"]
        cur.execute(
            "UPDATE dao_criteria SET m16_criterion_code = %s WHERE id = %s",
            ("INT_TEST_CODE_X", crit_id),
        )

    set_rls_is_admin(True)
    try:

        async def _run() -> str | None:
            with get_connection() as conn:
                return await resolve_criterion_id(ws_id, "INT_TEST_CODE_X", conn)

        assert asyncio.run(_run()) == crit_id
    finally:
        reset_rls_request_context()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extract_offer_async_non_tier4_mocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Avec tier != T4 et backend mocké, au moins un champ a confidence > 0.5."""
    from src.couche_a.extraction import offer_pipeline as op

    class _Router:
        timeout = 30

        def select_tier(self) -> Tier:
            return Tier.T2

    async def _fake_backend(
        document_id: str, text: str, document_role: str
    ) -> TDRExtractionResult:
        return TDRExtractionResult(
            document_id=document_id,
            document_role=document_role,
            family_main="TEST",
            family_sub="TEST",
            taxonomy_core="TEST",
            fields=[
                ExtractionField(
                    field_name="total_price",
                    value=12345.0,
                    confidence=0.8,
                    evidence="p.1 — 12 345",
                    tier_used=Tier.T2,
                )
            ],
            tier_used=Tier.T2,
        )

    monkeypatch.setattr(op, "_get_router", lambda: _Router())
    monkeypatch.setattr(op, "call_annotation_backend", _fake_backend)

    result = await op.extract_offer_content_async(
        document_id="doc-integ-1",
        text="Montant total 12 345 XOF",
        document_role="financial_offer",
    )
    assert result.fields, "champs extraits attendus"
    assert max(f.confidence for f in result.fields) > 0.5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_v5_zip_end_to_end(
    db_conn,
    pipeline_case_with_dao_and_offers,
) -> None:
    """Pass -1 sur ``data/test_zip/test_offers.zip`` puis ``run_pipeline_v5`` — assessments > 0."""
    zip_path = REPO_ROOT / "data" / "test_zip" / "test_offers.zip"
    if not zip_path.is_file():
        pytest.skip("ZIP manquant — exécuter : python scripts/build_test_offers_zip.py")

    from src.assembler.graph import build_pass_minus_one_graph
    from src.services.pipeline_v5_service import run_pipeline_v5
    from src.workers.arq_tasks import run_pass_minus_1

    if build_pass_minus_one_graph() is None:
        pytest.skip("langgraph requis pour Pass -1")

    case_id = pipeline_case_with_dao_and_offers
    committee_id = str(uuid.uuid4())
    ws_id: str
    tenant_id: str

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        cur.execute(
            """
            SELECT pw.id::text AS ws, pw.tenant_id::text AS tid
            FROM process_workspaces pw
            WHERE pw.legacy_case_id = %s
            """,
            (case_id,),
        )
        row = cur.fetchone()
        assert row is not None
        ws_id = row["ws"]
        tenant_id = row["tid"]
        cur.execute(
            """
            INSERT INTO committees
                (committee_id, case_id, org_id, committee_type, created_by, status)
            VALUES (%s::uuid, %s, %s, %s, %s, %s)
            """,
            (committee_id, case_id, "org-test", "achat", "pytest", "draft"),
        )

    try:
        out = await run_pass_minus_1(
            {},
            workspace_id=ws_id,
            tenant_id=tenant_id,
            zip_path=str(zip_path),
        )
        assert not out.get("error"), out
        assert len(out.get("bundle_ids") or []) >= 1

        set_rls_is_admin(True)
        try:
            result = run_pipeline_v5(ws_id, force_m14=True)
            assert result.completed, result
            assert result.step_5_assessments_created > 0
        finally:
            reset_rls_request_context()

        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.is_admin', 'true', true)")
            cur.execute(
                """
                SELECT COUNT(*)::int AS n FROM criterion_assessments
                WHERE workspace_id = %s::uuid
                """,
                (ws_id,),
            )
            n_rows = int(cur.fetchone()["n"])
        assert n_rows > 0
    finally:
        _cleanup_v5_artifacts(db_conn, ws_id=ws_id, committee_id=committee_id)


@pytest.mark.performance
def test_pipeline_v5_performance_avg_under_120s(
    db_conn,
    pipeline_case_with_dao_and_offers,
) -> None:
    """Trois exécutions ``run_pipeline_v5`` après Pass -1 ; moyenne < 120 s."""
    zip_path = REPO_ROOT / "data" / "test_zip" / "test_offers.zip"
    if not zip_path.is_file():
        pytest.skip("ZIP manquant — python scripts/build_test_offers_zip.py")

    from src.assembler.graph import build_pass_minus_one_graph
    from src.services.pipeline_v5_service import run_pipeline_v5
    from src.workers.arq_tasks import run_pass_minus_1

    if build_pass_minus_one_graph() is None:
        pytest.skip("langgraph requis")

    case_id = pipeline_case_with_dao_and_offers
    committee_id = str(uuid.uuid4())

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        cur.execute(
            """
            SELECT pw.id::text AS ws, pw.tenant_id::text AS tid
            FROM process_workspaces pw WHERE pw.legacy_case_id = %s
            """,
            (case_id,),
        )
        row = cur.fetchone()
        assert row
        ws_id = row["ws"]
        tenant_id = row["tid"]
        cur.execute(
            """
            INSERT INTO committees
                (committee_id, case_id, org_id, committee_type, created_by, status)
            VALUES (%s::uuid, %s, %s, %s, %s, %s)
            """,
            (committee_id, case_id, "org-test", "achat", "pytest-perf", "draft"),
        )

    durations: list[float] = []
    try:
        asyncio.run(
            run_pass_minus_1(
                {},
                workspace_id=ws_id,
                tenant_id=tenant_id,
                zip_path=str(zip_path),
            )
        )
        set_rls_is_admin(True)
        try:
            for i in range(3):
                t0 = time.perf_counter()
                r = run_pipeline_v5(ws_id, force_m14=(i == 0))
                durations.append(time.perf_counter() - t0)
                assert r.completed, r
                assert r.step_5_assessments_created > 0, r
        finally:
            reset_rls_request_context()
    finally:
        _cleanup_v5_artifacts(db_conn, ws_id=ws_id, committee_id=committee_id)

    avg = sum(durations) / len(durations)
    PERF_REPORT_PATH.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "runs_seconds": durations,
                "average_seconds": round(avg, 3),
                "threshold_seconds": 120,
                "passed": avg < 120.0,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    assert avg < 120.0, (
        f"Performance: moyenne {avg:.1f}s >= 120s — runs={durations!r}. "
        f"Rapport : {PERF_REPORT_PATH}"
    )
