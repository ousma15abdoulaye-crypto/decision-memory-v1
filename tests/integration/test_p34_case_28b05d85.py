"""P3.4 E4 — intégration CASE-28b05d85 (skip si DB / UUID non fournis).

Variables d'environnement attendues pour une exécution réelle (Option B) :

- ``DATABASE_URL`` (ou chargée via ``.env`` / ``.env.local`` comme le reste du dépôt)
- ``P34_E4_WORKSPACE_ID`` : UUID ``process_workspaces.id`` du cas pilote

Aucun secret ni UUID métier ne doit être versionné dans ce fichier.
"""

from __future__ import annotations

import os
from collections import Counter
from uuid import UUID

import pytest
from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.local", override=True)

from src.db.tenant_context import reset_rls_request_context, set_rls_is_admin
from src.procurement.matrix_models import MatrixRow, MatrixSummary, RankStatus
from src.services.pipeline_v5_service import run_pipeline_v5

pytestmark = pytest.mark.integration


@pytest.fixture
def workspace_id() -> UUID:
    raw = os.environ.get("P34_E4_WORKSPACE_ID", "").strip()
    if not raw:
        pytest.skip("P34_E4_WORKSPACE_ID non défini — skip E4 integration test")
    return UUID(raw)


def _stable_fingerprint(result):
    out = []
    for row in result.matrix_rows:
        d = row.model_dump(mode="json")
        out.append(
            {
                "bundle_id": d.get("bundle_id"),
                "vendor_id": d.get("vendor_id"),
                "rank_status": d.get("rank_status"),
                "rank": d.get("rank"),
                "total_score_system": d.get("total_score_system"),
            }
        )
    out.sort(key=lambda x: (x.get("bundle_id") or "", x.get("vendor_id") or ""))
    return out


def test_p34_e4_pipeline_and_matrix_invariants(workspace_id: UUID) -> None:
    if not os.environ.get("DATABASE_URL", "").strip():
        pytest.skip("DATABASE_URL non défini — skip E4 integration test")

    reset_rls_request_context()
    set_rls_is_admin(True)
    try:
        wid = str(workspace_id)
        first = run_pipeline_v5(wid, force_m14=False)
        assert first.completed, (
            f"pipeline incomplet: error={first.error!r} stopped_at={first.stopped_at!r}"
        )
        assert first.matrix_summary is not None
        assert first.matrix_rows, "matrix_rows vide après run complet"

        for row in first.matrix_rows:
            MatrixRow.model_validate(row.model_dump())

        summary = first.matrix_summary
        MatrixSummary.model_validate(summary.model_dump())

        by_status = Counter(r.rank_status for r in first.matrix_rows)
        assert summary.count_ranked == by_status.get(RankStatus.RANKED, 0)
        assert summary.count_excluded == by_status.get(RankStatus.EXCLUDED, 0)
        assert summary.total_bundles == len(first.matrix_rows)

        second = run_pipeline_v5(wid, force_m14=False)
        assert second.completed
        assert _stable_fingerprint(first) == _stable_fingerprint(second)
    finally:
        reset_rls_request_context()
