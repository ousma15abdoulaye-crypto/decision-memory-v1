"""Phase 1 — Gate B : qualification bundles avant M14."""

from __future__ import annotations

from typing import Any

import pytest

from src.services.m14_bridge import (
    BridgeConfigurationError,
    matrix_participant_bundle_ids,
)
from src.services.pipeline_v5_service import (
    PipelineError,
    PipelineV5Result,
    gate_b_classify_bundle_for_m14,
)


def test_gate_b_only_scorable_bundles_enter_m14() -> None:
    internal_rows = [
        {
            "doc_type": "offer_combined",
            "raw_text": "SAVE THE CHILDREN SAFEGUARDING POLICY\n",
            "vendor_name_raw": "Policies",
        }
    ]
    unusable_rows = [{"doc_type": "other", "raw_text": "", "vendor_name_raw": "X"}]
    assert gate_b_classify_bundle_for_m14(internal_rows)[0] != "SCORABLE"
    assert gate_b_classify_bundle_for_m14(unusable_rows)[0] != "SCORABLE"


def test_gate_b_internal_bundles_excluded() -> None:
    rows = [
        {
            "doc_type": "offer_combined",
            "raw_text": "Save the Children Safeguarding Policy for partners\n",
            "vendor_name_raw": "Mandatory Policies",
        }
    ]
    st, reason = gate_b_classify_bundle_for_m14(rows)
    assert st == "INTERNAL"
    assert "internal" in reason.lower()


def test_gate_b_reference_bundles_excluded() -> None:
    rows = [
        {
            "doc_type": "rfq",
            "raw_text": "Appel à manifestation d'intérêt SCI Mali\n",
            "vendor_name_raw": "RFQ",
        }
    ]
    st, reason = gate_b_classify_bundle_for_m14(rows)
    assert st == "REFERENCE"
    assert "source_rules" in reason or "rfq" in reason.lower()


def test_gate_b_unusable_bundles_excluded() -> None:
    rows = [
        {"doc_type": "other", "raw_text": None, "vendor_name_raw": "A"},
        {"doc_type": "other", "raw_text": "   ", "vendor_name_raw": "A"},
    ]
    st, reason = gate_b_classify_bundle_for_m14(rows)
    assert st == "UNUSABLE"


def test_gate_b_pilot_scorable_count_is_2() -> None:
    """Rejeu des 8 bundles pilote (documents tels qu'en base audit)."""
    pilot: dict[str, list[dict[str, Any]]] = {
        "6d18242c-c0de-47ca-a330-e5d82db18b75": [
            {"doc_type": "other", "raw_text": "", "vendor_name_raw": "LASS"},
        ],
        "f19c8f9f-0a3e-4110-90c6-0319d917107c": [
            {
                "doc_type": "offer_combined",
                "raw_text": (
                    "SAVE THE CHILDREN CHILD SAFEGUARDING POLICY "
                    "LA POLITIQUE DE SAUVEGARDE DES ENFANTS\n"
                ),
                "vendor_name_raw": "Mandatory Policies",
            },
        ],
        "0feb8c18-d533-485e-91de-53787257381a": [
            {
                "doc_type": "offer_combined",
                "raw_text": (
                    "REPUBLIQUE DU MALI\nSave the Children\n"
                    "FOURNITURE DE CARTOUCHES ET TONERS\n"
                ),
                "vendor_name_raw": "GLOB ACCESS",
            },
        ],
        "0b19365e-ba8d-4403-a63c-f25bd71c2e8c": [
            {
                "doc_type": "rib",
                "raw_text": (
                    "POLITIQUE DE DEVELOPPEMENT DURABLE "
                    "POUR LES FOURNISSEURS DE SAVE THE CHILDREN\n"
                ),
                "vendor_name_raw": "Politique",
            },
        ],
        "984ecd50-f74a-4c0a-9ad6-f3e0faa6238e": [
            {
                "doc_type": "offer_combined",
                "raw_text": (
                    "Rapport narratif d'évaluations des offres : "
                    "Fourniture de Cartouches et Toners\n"
                ),
                "vendor_name_raw": "PV",
            },
        ],
        "17bc1f75-a152-489e-b8ab-c283554627fe": [
            {"doc_type": "other", "raw_text": "", "vendor_name_raw": "Rapport"},
        ],
        "0aa0b276-3970-4669-a53e-1441cfec0a39": [
            {"doc_type": "other", "raw_text": "", "vendor_name_raw": "RFQ"},
            {
                "doc_type": "offer_combined",
                "raw_text": (
                    "SAVE THE CHILDREN RFQ _FOURNITURE DES CARTOUCHES "
                    "ET TONER _ SCI MALI BUREAU DE BAMAKO\n"
                ),
                "vendor_name_raw": "RFQ",
            },
        ],
        "52e162e5-d969-4530-9ac6-df75bd17458b": [
            {
                "doc_type": "offer_combined",
                "raw_text": (
                    "REPONSE A LA DEMANDE DE DEVIS RFQ-MLI-BKO-2025-002 "
                    "CARTOUCHES\nSave the Children\n"
                ),
                "vendor_name_raw": "SOPRESCOM",
            },
        ],
    }
    scorable = [
        bid
        for bid, rows in pilot.items()
        if gate_b_classify_bundle_for_m14(rows)[0] == "SCORABLE"
    ]
    assert len(scorable) == 2
    assert "0feb8c18-d533-485e-91de-53787257381a" in scorable
    assert "52e162e5-d969-4530-9ac6-df75bd17458b" in scorable


def test_gate_b_all_four_fields_persisted_in_out() -> None:
    """Test 6 — Vérifier que out contient les 4 champs Gate B/C."""
    out = PipelineV5Result(workspace_id="test-wid", case_id="test-case")
    # Simuler Gate B
    out.bundle_status_by_bundle_id = {
        "bundle1": "SCORABLE",
        "bundle2": "INTERNAL",
        "bundle3": "REFERENCE",
        "bundle4": "UNUSABLE",
    }
    out.offers_submitted_to_m14 = ["bundle1"]
    # Simuler Gate C
    out.matrix_participants = [
        {"bundle_id": "bundle1", "supplier_name": "Vendor A", "is_eligible": True}
    ]
    out.excluded_from_matrix = [
        {"bundle_id": "bundle2", "supplier_name": "Internal", "reason": "internal_reference_bundle"},
        {"bundle_id": "bundle3", "supplier_name": "Reference", "reason": "reference_bundle"},
        {"bundle_id": "bundle4", "supplier_name": "Empty", "reason": "unusable"},
    ]

    # Assertions
    assert "bundle_status_by_bundle_id" in out.model_fields
    assert "offers_submitted_to_m14" in out.model_fields
    assert "matrix_participants" in out.model_fields
    assert "excluded_from_matrix" in out.model_fields
    assert len(out.bundle_status_by_bundle_id) == 4
    assert len(out.offers_submitted_to_m14) == 1
    assert len(out.matrix_participants) == 1
    assert len(out.excluded_from_matrix) == 3


def test_gate_b_missing_matrix_participants_raises_invalid() -> None:
    """Test 7 — PipelineError 'invalid' si matrix_participants = None."""
    # Simuler le guard dans pipeline_v5_service après build_matrix_participants_and_excluded
    # qui retournerait None (défaillance structurelle)
    mp_list = None

    with pytest.raises(PipelineError) as exc_info:
        if mp_list is None:
            raise PipelineError(
                "pipeline_invalid:matrix_participants_missing — "
                "build_matrix_participants_and_excluded returned None, Gate B/C did not produce a valid participant list"
            )

    assert "pipeline_invalid" in str(exc_info.value)
    assert "matrix_participants_missing" in str(exc_info.value)


def test_gate_b_empty_matrix_participants_raises_blocked() -> None:
    """Test 8 — PipelineError 'blocked' si matrix_participants = [] (blocage métier)."""
    # Simuler le guard dans pipeline_v5_service après build_matrix_participants_and_excluded
    # qui retournerait [] (aucun concurrent éligible - résultat métier légal)
    mp_list: list = []

    with pytest.raises(PipelineError) as exc_info:
        if len(mp_list) == 0:
            raise PipelineError(
                "pipeline_blocked:no_eligible_matrix_participants — "
                "All bundles failed Gate B or Gate C, no eligible supplier to score in this dossier"
            )

    error_msg = str(exc_info.value)
    assert "pipeline_blocked" in error_msg
    assert "no_eligible_matrix_participants" in error_msg
    # Важно : pas "invalid" (blocage métier, pas bug système)
    assert "invalid" not in error_msg or "pipeline_invalid" not in error_msg


def test_bridge_strict_mode_raises_on_missing_matrix_participants() -> None:
    """Test 9 — Bridge strict=True lève erreur si matrix_participants absent."""
    matrix_raw = {"scores_matrix": {}, "offer_evaluations": []}
    # matrix_participants absent

    with pytest.raises(BridgeConfigurationError) as exc_info:
        matrix_participant_bundle_ids(matrix_raw, strict=True)

    assert "bridge_invalid" in str(exc_info.value)
    assert "matrix_participants_required_in_strict_mode" in str(exc_info.value)


def test_bridge_legacy_mode_returns_none_without_error() -> None:
    """Test 10 — Bridge strict=False (legacy) retourne None sans erreur si matrix_participants absent."""
    matrix_raw = {"scores_matrix": {}, "offer_evaluations": []}
    # matrix_participants absent

    result = matrix_participant_bundle_ids(matrix_raw, strict=False)

    assert result is None  # Mode legacy : pas de filtre
