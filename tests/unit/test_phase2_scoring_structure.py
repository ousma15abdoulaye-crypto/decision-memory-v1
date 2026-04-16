"""Phase 2 — D-003 / D-004 : scoring_structure DAO + clés UUID scores_matrix."""

from __future__ import annotations

import uuid

import pytest

from src.procurement.m14_engine import EvaluationEngine
from src.procurement.m14_evaluation_models import (
    DAO_CRITERION_ID_UUID_RE,
    m14_h2_scoring_structure_dict_from_dao_criteria_rows,
    scoring_structure_detected_from_dao_criteria_rows,
)
from src.procurement.m14_evaluation_repository import (
    sanitize_scores_matrix_to_dao_criterion_keys,
)
from src.services.pipeline_v5_service import (
    PipelineConfigurationError,
    PipelineError,
    _ensure_m14_scoring_structure_for_scorable_offers,
    _require_dao_criteria_for_pipeline,
)


def _sample_dao_rows() -> list[dict]:
    u1, u2, u3 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    return [
        {
            "id": u1,
            "critere_nom": "Critère A",
            "ponderation": 40.0,
            "is_eliminatory": False,
            "famille": "technical",
        },
        {
            "id": u2,
            "critere_nom": "Critère B",
            "ponderation": 30.0,
            "is_eliminatory": True,
            "famille": "technical",
        },
        {
            "id": u3,
            "critere_nom": "Critère C",
            "ponderation": 30.0,
            "is_eliminatory": False,
            "famille": "price",
        },
    ]


def test_scoring_structure_built_from_dao_criteria() -> None:
    rows = _sample_dao_rows()
    ss = scoring_structure_detected_from_dao_criteria_rows(rows)
    assert len(ss.criteria) == 3
    for c in ss.criteria:
        assert DAO_CRITERION_ID_UUID_RE.match(c.criteria_name)
    assert abs(ss.total_weight - 100.0) <= 0.01
    assert ss.ponderation_coherence == "OK"


def test_scores_matrix_keys_are_uuids() -> None:
    good = str(uuid.uuid4())
    allowed = frozenset({good})
    matrix = {
        "bundle-1": {
            good: {"score": 1.0, "source": "m14"},
            "dgmp_foo": {"score": 0.0},
            "m14:technical:x": {"score": 1.0},
            "reg_only_y": {"score": 1.0},
        }
    }
    out = sanitize_scores_matrix_to_dao_criterion_keys(matrix, allowed)
    assert set(out["bundle-1"].keys()) == {good}
    for bid, cells in out.items():
        for k in cells:
            assert not str(k).startswith("dgmp_")
            assert not str(k).startswith("m14:")
            assert not str(k).startswith("reg_only_")


def test_pipeline_fails_loud_if_no_dao_criteria() -> None:
    wid = str(uuid.uuid4())
    with pytest.raises(PipelineConfigurationError, match="aucun dao_criteria"):
        _require_dao_criteria_for_pipeline(wid, [])


def test_scoring_structure_not_none_when_dao_criteria_present() -> None:
    rows = _sample_dao_rows()
    dct = m14_h2_scoring_structure_dict_from_dao_criteria_rows(rows)
    assert dct.get("criteria")
    assert dct["ponderation_coherence"] == "OK"
    assert abs(float(dct["total_weight"]) - 100.0) <= 0.01


def test_pipeline_fails_fast_when_scoring_structure_empty() -> None:
    offers = [{"document_id": str(uuid.uuid4())}]
    empty_ss: dict = {"criteria": [], "ponderation_coherence": "NOT_FOUND"}
    with pytest.raises(PipelineError, match="m14_scoring_structure_empty"):
        _ensure_m14_scoring_structure_for_scorable_offers(offers, empty_ss)


def test_compute_technical_score_receives_expected_structure() -> None:
    rows = _sample_dao_rows()
    ss_dict = m14_h2_scoring_structure_dict_from_dao_criteria_rows(rows)
    eng = EvaluationEngine(repository=None)
    tech = eng._compute_technical_score(
        {"document_id": "b1"},
        {"scoring_structure": ss_dict},
        {},
    )
    assert tech is not None
    assert len(tech.criteria_scores) == 3
    assert tech.ponderation_coherence == "OK"


def test_scoring_structure_preserves_uuid_dao_ids() -> None:
    rows = _sample_dao_rows()
    dct = m14_h2_scoring_structure_dict_from_dao_criteria_rows(rows)
    for c in dct["criteria"]:
        assert c["criterion_id"] == c["criteria_name"]
        assert DAO_CRITERION_ID_UUID_RE.match(c["criterion_id"])


def test_scoring_structure_skips_non_uuid_dao_ids() -> None:
    u1 = str(uuid.uuid4())
    rows = [
        {"id": "not-a-uuid", "critere_nom": "X", "ponderation": 50.0, "famille": "x"},
        {
            "id": u1,
            "critere_nom": "Seul valide",
            "ponderation": 100.0,
            "is_eliminatory": False,
            "famille": "technical",
        },
    ]
    ss = scoring_structure_detected_from_dao_criteria_rows(rows)
    assert len(ss.criteria) == 1
    assert ss.criteria[0].criteria_name == u1
