"""D-004 — bridge strict_uuid : clés DAO UUID canoniques uniquement."""

from __future__ import annotations

import inspect
import uuid
from typing import Any

import pytest

from src.services import m14_bridge
from src.services.m14_bridge import (
    BridgeResult,
    PipelineError,
    assert_scorable_bundles_have_at_least_one_canonical_key,
    matches_d004_excluded_scoring_pattern,
    resolve_strict_scoring_criterion_key,
)


def test_bridge_writes_only_canonical_dao_uuid_keys() -> None:
    """Toute clé résolue est un dao_criteria.id du workspace (UUID toute version)."""
    u_dao = str(uuid.uuid1())
    allowed = frozenset({u_dao})
    assert resolve_strict_scoring_criterion_key(u_dao, allowed) == u_dao
    u4 = str(uuid.uuid4())
    allowed2 = frozenset({u4})
    assert resolve_strict_scoring_criterion_key(u4.upper(), allowed2) == u4


def test_bridge_rejects_non_uuid_scoring_key() -> None:
    allowed = frozenset({str(uuid.uuid4())})
    assert resolve_strict_scoring_criterion_key("dgmp_mali_nif", allowed) is None
    assert resolve_strict_scoring_criterion_key("critère libellé", allowed) is None
    assert resolve_strict_scoring_criterion_key(str(uuid.uuid4()), allowed) is None


def test_bridge_preserves_dao_criterion_id_alignment() -> None:
    cid = str(uuid.uuid4())
    allowed = frozenset({cid})
    got = resolve_strict_scoring_criterion_key(cid, allowed)
    assert got == cid


def test_bridge_excludes_eligibility_and_compliance_keys() -> None:
    allowed = frozenset({str(uuid.uuid4())})
    assert resolve_strict_scoring_criterion_key("m14:eligibility:x", allowed) is None
    assert resolve_strict_scoring_criterion_key("m14:compliance:y", allowed) is None
    assert matches_d004_excluded_scoring_pattern("m14:eligibility:z") is True
    assert matches_d004_excluded_scoring_pattern("m14:compliance:w") is True


def test_pipeline_v5_path_calls_bridge_with_strict_uuid_true() -> None:
    from src.services import pipeline_v5_service

    src = inspect.getsource(pipeline_v5_service.run_pipeline_v5)
    assert "strict_uuid=True" in src
    assert "populate_assessments_from_m14" in src


def test_bridge_fails_fast_when_all_keys_rejected() -> None:
    b = str(uuid.uuid4())
    matrix = {
        b: {
            "slug-only": {"score": 1.0},
            "m14:eligibility:x": {"score": 0.0},
        },
    }
    with pytest.raises(PipelineError, match="bundle_fail_fast"):
        assert_scorable_bundles_have_at_least_one_canonical_key(
            matrix,
            matrix_allow=frozenset({b}),
            dao_crit_ids=frozenset({str(uuid.uuid4())}),
        )


def test_bridge_warning_with_counter_on_partial_rejection(monkeypatch: Any) -> None:
    dao1, dao2, dao3 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    bundle = str(uuid.uuid4())
    tenant = str(uuid.uuid4())
    wid = str(uuid.uuid4())
    eval_id = str(uuid.uuid4())

    monkeypatch.setattr(m14_bridge, "_delete_stale_scoring_rows", lambda *a, **k: 0)

    upserts: list[tuple[str, str]] = []

    def fake_upsert(
        _conn: Any,
        *,
        criterion_key: str,
        dao_criterion_id: str | None,
        **kw: Any,
    ) -> str:
        upserts.append((criterion_key, dao_criterion_id or ""))
        assert criterion_key == dao_criterion_id
        return "created"

    monkeypatch.setattr(m14_bridge, "_upsert_assessment", fake_upsert)

    scores_matrix: dict[str, Any] = {
        "matrix_participants": [{"bundle_id": bundle, "is_eligible": True}],
        bundle: {
            dao1: {"score": 1.0, "confidence": 0.8},
            dao2: {"score": 1.0, "confidence": 0.8},
            dao3: {"score": 1.0, "confidence": 0.8},
            "libelle-non-resolu": {"score": 0.0},
            "m14:eligibility:chk": {"score": 0.0},
        },
    }

    def fake_db_one(conn: Any, sql: str, params: dict | None = None) -> Any:
        if "process_workspaces" in sql and "tenant_id" in sql:
            return {"tenant_id": tenant}
        if "evaluation_documents" in sql and "ORDER BY version" in sql:
            return {"id": eval_id, "scores_matrix": scores_matrix}
        return None

    def fake_db_all(conn: Any, sql: str, params: dict | None = None) -> list[dict]:
        if "supplier_bundles" in sql:
            return [{"id": bundle}]
        if "dao_criteria" in sql:
            return [
                {"id": dao1, "critere_nom": "A", "m16_criterion_code": None},
                {"id": dao2, "critere_nom": "B", "m16_criterion_code": None},
                {"id": dao3, "critere_nom": "C", "m16_criterion_code": None},
            ]
        return []

    monkeypatch.setattr(m14_bridge, "db_execute_one", fake_db_one)
    monkeypatch.setattr(m14_bridge, "db_fetchall", fake_db_all)

    class DummyConn:
        pass

    result: BridgeResult = m14_bridge._run_bridge(
        DummyConn(),
        wid,
        strict_matrix_participants=True,
        strict_uuid=True,
    )
    assert result.rejected_noncanonical_keys == 2
    assert len(upserts) == 3
    assert {t[0] for t in upserts} == {dao1, dao2, dao3}
    assert any("2/5" in w and bundle in w for w in result.structured_warnings)
