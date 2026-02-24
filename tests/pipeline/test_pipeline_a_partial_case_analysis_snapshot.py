# tests/pipeline/test_pipeline_a_partial_case_analysis_snapshot.py
"""
L11 — CaseAnalysisSnapshot v1 (CAS).

Prouve :
  cas_version == 'v1'
  export_ready == False toujours
  Pydantic rejette winner, rank, recommendation, best_offer
  CAS.to_jsonb() renvoie JSON valide
  CASReadiness(export_ready=True) rejeté par Literal[False]
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.couche_a.pipeline.models import (
    CASCaseContext,
    CaseAnalysisSnapshot,
    CASReadiness,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cas(**overrides) -> CaseAnalysisSnapshot:
    """Construit un CAS v1 minimal valide."""
    defaults = dict(
        cas_version="v1",
        case_context=CASCaseContext(
            case_id="test-001",
            title="Test CAS",
            currency="XOF",
            status="draft",
            case_type="appel_offres",
        ),
        generated_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return CaseAnalysisSnapshot(**defaults)


# ---------------------------------------------------------------------------
# cas_version == 'v1'
# ---------------------------------------------------------------------------


def test_cas_version_is_v1():
    """cas_version est toujours 'v1'."""
    cas = _make_cas()
    assert cas.cas_version == "v1"


# ---------------------------------------------------------------------------
# export_ready == False toujours
# ---------------------------------------------------------------------------


def test_cas_export_ready_is_always_false():
    """export_ready == False (Literal[False] — INV-P8)."""
    cas = _make_cas()
    assert cas.readiness.export_ready is False


def test_cas_readiness_export_ready_true_rejected():
    """CASReadiness(export_ready=True) doit être rejeté par Pydantic (Literal[False])."""
    with pytest.raises(ValidationError) as exc_info:
        CASReadiness(export_ready=True)  # type: ignore[arg-type]

    assert (
        "export_ready" in str(exc_info.value).lower()
        or "false" in str(exc_info.value).lower()
    ), f"Validation error ne mentionne pas export_ready : {exc_info.value}"


# ---------------------------------------------------------------------------
# Pydantic rejette winner, rank, recommendation, best_offer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "forbidden_field", ["winner", "rank", "recommendation", "best_offer"]
)
def test_cas_rejects_forbidden_field(forbidden_field: str):
    """CaseAnalysisSnapshot rejette les champs interdits (INV-P7 / ADR-0012)."""
    with pytest.raises(ValidationError) as exc_info:
        CaseAnalysisSnapshot(
            cas_version="v1",
            case_context=CASCaseContext(
                case_id="test-001",
                title="Test",
                currency="XOF",
                status="draft",
                case_type="appel_offres",
            ),
            generated_at=datetime.now(UTC),
            **{forbidden_field: "valeur_interdite"},
        )

    error_text = str(exc_info.value)
    assert forbidden_field in error_text or "interdit" in error_text.lower(), (
        f"ValidationError doit mentionner {forbidden_field!r} "
        f"ou 'interdit' : {error_text}"
    )


# ---------------------------------------------------------------------------
# CAS.to_jsonb() renvoie JSON valide
# ---------------------------------------------------------------------------


def test_cas_to_jsonb_returns_valid_json():
    """CAS.to_jsonb() retourne une chaîne JSON parseable sans erreur."""
    cas = _make_cas()
    jsonb_str = cas.to_jsonb()

    assert isinstance(jsonb_str, str), "to_jsonb() doit retourner une str"

    parsed = json.loads(jsonb_str)
    assert isinstance(parsed, dict), "JSON parsé doit être un dict"
    assert parsed.get("cas_version") == "v1"


# ---------------------------------------------------------------------------
# cas_version 'v1' est fermé (autre valeur rejetée)
# ---------------------------------------------------------------------------


def test_cas_version_other_than_v1_rejected():
    """cas_version != 'v1' doit être rejeté par Pydantic (Literal['v1'])."""
    with pytest.raises(ValidationError):
        CaseAnalysisSnapshot(
            cas_version="v2",  # type: ignore[arg-type]
            case_context=CASCaseContext(
                case_id="test-001",
                title="Test",
                currency="XOF",
                status="draft",
                case_type="appel_offres",
            ),
            generated_at=datetime.now(UTC),
        )
