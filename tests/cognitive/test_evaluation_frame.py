"""Tests BLOC5 — evaluation frame (critères, zones, pertinence sans DB pour la plupart)."""

from __future__ import annotations

from datetime import UTC, datetime

from src.cognitive.evaluation_frame import (
    SURFACE_RELEVANCE_MIN,
    build_zones_of_clarification,
    enrich_criteria_with_dao,
    extract_criteria_from_scores_matrix,
    process_market_signals_for_frame,
    scores_matrix_is_m14_bundle_nested,
)


def test_scores_matrix_is_m14_bundle_nested_detects_shape() -> None:
    sm = {
        "bundle-a": {"c1": {"score": 0.5, "confidence": 0.8}},
    }
    assert scores_matrix_is_m14_bundle_nested(sm) is True
    assert scores_matrix_is_m14_bundle_nested({"k": 1}) is False


def test_extract_criteria_m14_union_second_level_keys() -> None:
    sm = {
        "bundle-1": {
            "crit-a": {"score": 0.5, "confidence": 0.8},
            "crit-b": {"signal": "ok", "confidence": 1.0},
        },
        "bundle-2": {"crit-a": {"score": 0.3, "confidence": 0.8}},
    }
    crit = extract_criteria_from_scores_matrix(sm)
    keys = {c["criterion_key"] for c in crit}
    assert keys == {"crit-a", "crit-b"}
    assert "bundle-1" not in keys


def test_enrich_criteria_with_dao_merges_names() -> None:
    crit = [{"criterion_key": "c1", "present": True, "value_type": "m14_nested"}]
    dao = [
        {
            "id": "c1",
            "critere_nom": "Prix",
            "ponderation": 0.55,
            "is_eliminatory": False,
        }
    ]
    out = enrich_criteria_with_dao(crit, dao)
    assert out[0]["critere_nom"] == "Prix"
    assert float(out[0]["ponderation"]) == 0.55
    assert out[0]["is_eliminatory"] is False


def test_extract_criteria_excludes_forbidden_keys() -> None:
    sm = {
        "price_competitiveness": 0.8,
        "winner": "x",
        "rank": 1,
        "nested": {"a": 1},
    }
    crit = extract_criteria_from_scores_matrix(sm)
    keys = {c["criterion_key"] for c in crit}
    assert "price_competitiveness" in keys
    assert "nested" in keys
    assert "winner" not in keys
    assert "rank" not in keys


def test_build_zones_merges_dissents_and_low_conf() -> None:
    dissents = [
        {
            "id": "d1",
            "occurred_at": "2026-01-01",
            "payload": {"summary": "Écart sur critère technique"},
        }
    ]
    low = [{"id": "bd1", "bundle_id": "b1", "system_confidence": 0.3}]
    zones = build_zones_of_clarification(dissents, low)
    assert len(zones) == 2
    assert zones[0]["kind"] == "dissent"
    assert zones[1]["kind"] == "low_confidence_bundle"


class _FakeConn:
    """Connexion minimale — INSERT ignoré (pas de DB en test unitaire)."""

    def execute(self, *args: object, **kwargs: object) -> None:
        return None

    def fetchone(self) -> None:
        return None


def test_process_market_signals_filters_by_relevance_threshold() -> None:
    past = datetime(2025, 1, 1, tzinfo=UTC)
    raw = [
        {
            "id": "a1111111-1111-1111-1111-111111111111",
            "signal_type": "price_anchor_update",
            "payload": {
                "context_match": 0.99,
                "data_points": 10.0,
                "threshold_min": 3.0,
            },
            "generated_at": past,
        },
        {
            "id": "b2222222-2222-2222-2222-222222222222",
            "signal_type": "compliance_flag",
            "payload": {"context_match": 0.1, "data_points": 0.0, "threshold_min": 3.0},
            "generated_at": past,
        },
    ]
    out = process_market_signals_for_frame(
        _FakeConn(),
        tenant_id="00000000-0000-0000-0000-000000000001",
        workspace_id="00000000-0000-0000-0000-000000000002",
        raw_signals=raw,
    )
    assert all(float(x["relevance_score"]) >= SURFACE_RELEVANCE_MIN for x in out)
    assert len(out) <= 3
    types = {x["signal_type"] for x in out}
    assert "price_anchor_update" in types
    assert "compliance_flag" not in types
