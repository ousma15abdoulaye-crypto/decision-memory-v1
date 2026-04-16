"""D-005 — MergedCriterion vue additive (sans substitution des UUID DAO)."""

from __future__ import annotations

import copy
import uuid
from datetime import UTC, datetime

import pytest

from src.procurement.m14_evaluation_models import (
    m14_h2_scoring_structure_dict_from_dao_criteria_rows,
    scoring_structure_detected_from_dao_criteria_rows,
)
from src.procurement.merged_criteria import (
    MergedCriteriaBuildResult,
    build_merged_criteria,
    build_merged_criteria_result,
)
from src.services.m14_bridge import resolve_strict_scoring_criterion_key


def _uuid() -> str:
    return str(uuid.uuid4())


def test_build_merged_criteria_groups_by_famille_and_name() -> None:
    a, b = _uuid(), _uuid()
    rows = [
        {
            "id": a,
            "critere_nom": "  Capacité X  ",
            "ponderation": 30.0,
            "is_eliminatory": False,
            "famille": "technical",
        },
        {
            "id": b,
            "critere_nom": "capacité x",
            "ponderation": 20.0,
            "is_eliminatory": False,
            "famille": "technical",
        },
    ]
    r = build_merged_criteria(rows)
    assert len(r.merged) == 1
    m0 = r.merged[0]
    assert set(m0.source_ids) == {a, b}
    assert m0.weight_aggregated == pytest.approx(50.0)


def test_canonical_id_selection_is_deterministic() -> None:
    old_id, young_id = _uuid(), _uuid()
    t_old = datetime(2020, 1, 1, tzinfo=UTC)
    t_young = datetime(2024, 1, 1, tzinfo=UTC)
    rows = [
        {
            "id": young_id,
            "critere_nom": "Critère Z",
            "ponderation": 10.0,
            "is_eliminatory": False,
            "famille": "technical",
            "created_at": t_young.isoformat(),
        },
        {
            "id": old_id,
            "critere_nom": "critère z",
            "ponderation": 15.0,
            "is_eliminatory": False,
            "famille": "technical",
            "created_at": t_old.isoformat(),
        },
    ]
    r = build_merged_criteria(rows)
    assert len(r.merged) == 1
    assert r.merged[0].canonical_id == old_id


def test_canonical_id_lexicographic_when_no_created_at() -> None:
    u1, u2 = str(uuid.uuid4()), str(uuid.uuid4())
    u_lo, u_hi = min(u1, u2), max(u1, u2)
    rows = [
        {
            "id": u_hi,
            "critere_nom": "Same",
            "ponderation": 1.0,
            "is_eliminatory": False,
            "famille": "technical",
        },
        {
            "id": u_lo,
            "critere_nom": "same",
            "ponderation": 2.0,
            "is_eliminatory": False,
            "famille": "technical",
        },
    ]
    r = build_merged_criteria(rows)
    assert len(r.merged) == 1
    assert r.merged[0].canonical_id == u_lo


def test_is_eliminatory_true_if_any_source_is() -> None:
    a, b = _uuid(), _uuid()
    rows = [
        {
            "id": a,
            "critere_nom": "Dup",
            "ponderation": 10.0,
            "is_eliminatory": False,
            "famille": "technical",
        },
        {
            "id": b,
            "critere_nom": "dup",
            "ponderation": 10.0,
            "is_eliminatory": True,
            "famille": "technical",
        },
    ]
    r = build_merged_criteria(rows)
    assert r.merged[0].is_eliminatory is True


def test_weight_aggregated_single_source() -> None:
    a = _uuid()
    rows = [
        {
            "id": a,
            "critere_nom": "Solo",
            "ponderation": 42.5,
            "is_eliminatory": False,
            "famille": "general",
        },
    ]
    r = build_merged_criteria(rows)
    assert len(r.merged) == 1
    assert r.merged[0].weight_aggregated == pytest.approx(42.5)


def test_singleton_criterion_preserved_with_warning() -> None:
    a, b = _uuid(), _uuid()
    rows = [
        {
            "id": a,
            "critere_nom": "Prix offre",
            "ponderation": 10.0,
            "is_eliminatory": False,
            "famille": "commercial",
            "tax_basis": "HT",
        },
        {
            "id": b,
            "critere_nom": "Prix offre",
            "ponderation": 10.0,
            "is_eliminatory": False,
            "famille": "commercial",
            "tax_basis": "TTC",
        },
    ]
    r = build_merged_criteria(rows)
    assert len(r.merged) == 2
    assert any("d005_commercial_ht_ttc_same_label" in w for w in r.warnings)


def test_source_ids_contains_all_dao_uuids() -> None:
    a, b = _uuid(), _uuid()
    rows = [
        {
            "id": a,
            "critere_nom": "T1",
            "ponderation": 5.0,
            "is_eliminatory": False,
            "famille": "technical",
        },
        {
            "id": b,
            "critere_nom": "t1",
            "ponderation": 5.0,
            "is_eliminatory": False,
            "famille": "technical",
        },
    ]
    r = build_merged_criteria(rows)
    assert set(r.merged[0].source_ids) == {a, b}


def test_d003_scoring_structure_still_built_after_merge() -> None:
    rows = [
        {
            "id": _uuid(),
            "critere_nom": "A",
            "ponderation": 50.0,
            "is_eliminatory": False,
            "famille": "technical",
        },
        {
            "id": _uuid(),
            "critere_nom": "B",
            "ponderation": 50.0,
            "is_eliminatory": False,
            "famille": "technical",
        },
    ]
    snap = m14_h2_scoring_structure_dict_from_dao_criteria_rows(rows)
    rows_copy = copy.deepcopy(rows)
    build_merged_criteria_result(rows)
    assert rows == rows_copy
    assert m14_h2_scoring_structure_dict_from_dao_criteria_rows(rows) == snap
    assert scoring_structure_detected_from_dao_criteria_rows(
        rows
    ).total_weight == pytest.approx(100.0)


def test_d004_strict_uuid_resolves_against_source_ids() -> None:
    a, b = _uuid(), _uuid()
    rows = [
        {
            "id": a,
            "critere_nom": "X",
            "ponderation": 10.0,
            "is_eliminatory": False,
            "famille": "technical",
        },
        {
            "id": b,
            "critere_nom": "x",
            "ponderation": 10.0,
            "is_eliminatory": False,
            "famille": "technical",
        },
    ]
    r = build_merged_criteria(rows)
    allowed = frozenset(r.merged[0].source_ids)
    assert resolve_strict_scoring_criterion_key(a, allowed) == a
    assert resolve_strict_scoring_criterion_key(b.upper(), allowed) == b


def test_commercial_ht_and_ttc_do_not_merge() -> None:
    a, b = _uuid(), _uuid()
    rows = [
        {
            "id": a,
            "critere_nom": "Montant",
            "ponderation": 10.0,
            "is_eliminatory": False,
            "famille": "commercial",
            "tax_basis": "HT",
            "amount_scope": "UNIT",
        },
        {
            "id": b,
            "critere_nom": "Montant",
            "ponderation": 10.0,
            "is_eliminatory": False,
            "famille": "commercial",
            "tax_basis": "TTC",
            "amount_scope": "UNIT",
        },
    ]
    r = build_merged_criteria(rows)
    assert len(r.merged) == 2


def test_unit_price_and_total_price_do_not_merge() -> None:
    a, b = _uuid(), _uuid()
    rows = [
        {
            "id": a,
            "critere_nom": "Prix",
            "ponderation": 10.0,
            "is_eliminatory": False,
            "famille": "commercial",
            "tax_basis": "HT",
            "amount_scope": "UNIT",
        },
        {
            "id": b,
            "critere_nom": "Prix",
            "ponderation": 10.0,
            "is_eliminatory": False,
            "famille": "commercial",
            "tax_basis": "HT",
            "amount_scope": "LINE_TOTAL",
        },
    ]
    r = build_merged_criteria(rows)
    assert len(r.merged) == 2


def test_build_merged_criteria_result_defensive_copy() -> None:
    a = _uuid()
    rows = [{"id": a, "critere_nom": "One", "ponderation": 1.0, "famille": "general"}]
    r: MergedCriteriaBuildResult = build_merged_criteria_result(rows)
    rows[0]["critere_nom"] = "mutated"
    assert r.merged[0].canonical_name != "mutated"
