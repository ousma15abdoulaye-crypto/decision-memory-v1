"""P3.4 E4 — intégration CASE-28b05d85 (skip si DB / UUID non fournis).

Variables d'environnement attendues pour une exécution réelle (Option B) :

- ``DATABASE_URL`` (ou chargée via ``.env`` / ``.env.local`` comme le reste du dépôt)
- ``P34_E4_WORKSPACE_ID`` : UUID ``process_workspaces.id`` du cas pilote

Aucun secret ni UUID métier ne doit être versionné dans ce fichier.

Empreinte stable V3 : chargée depuis ``scripts/e4_run_benchmark.py`` (``importlib``) pour
une seule source de vérité avec ``_VOLATILE_FIELDS`` / ``_stable_matrix_fingerprint``.
"""

from __future__ import annotations

import importlib.util
import os
from collections import Counter
from pathlib import Path
from uuid import UUID

import pytest
from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.local", override=True)


def _load_e4_benchmark_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "e4_run_benchmark.py"
    spec = importlib.util.spec_from_file_location("e4_run_benchmark", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_e4m = _load_e4_benchmark_module()
_stable_matrix_fingerprint = _e4m._stable_matrix_fingerprint
_VOLATILE_FIELDS = _e4m._VOLATILE_FIELDS

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
        assert summary.count_ranked == by_status.get(RankStatus.RANKED, 0), (
            "V1 : count_ranked ne correspond pas aux lignes RANKED"
        )
        assert summary.count_excluded == by_status.get(RankStatus.EXCLUDED, 0), (
            "V1 : count_excluded ne correspond pas aux lignes EXCLUDED"
        )
        assert summary.total_bundles == len(first.matrix_rows), (
            "V1 : total_bundles != len(matrix_rows)"
        )

        second = run_pipeline_v5(wid, force_m14=False)
        assert second.completed, (
            f"V3 : second run incomplet error={second.error!r} stopped_at={second.stopped_at!r}"
        )

        fp_a = _stable_matrix_fingerprint(first)
        fp_b = _stable_matrix_fingerprint(second)
        assert fp_a == fp_b, (
            "V3 échouée : empreinte stable des matrix_rows divergente entre 2 runs "
            f"(champs exclus: {sorted(_VOLATILE_FIELDS)})"
        )
    finally:
        reset_rls_request_context()
