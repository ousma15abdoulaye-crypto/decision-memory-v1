"""
T-L10 : Moteur analysis_summary — génération SummaryDocument v1.
11 tests — corps complets — RÈGLE-TEST-01 appliquée.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.couche_a.analysis_summary.engine.models import SummarySection
from src.couche_a.analysis_summary.engine.service import (
    _compute_result_hash,
    generate_summary,
)

# ── Test 1 ─────────────────────────────────────────────────


def test_generate_summary_produces_summary_document_v1(db_conn, pipeline_run_factory):
    """
    generate_summary() → SummaryDocument avec summary_version='v1'.
    INV-AS4 — INV-AS7.
    """
    run = pipeline_run_factory(status="partial_complete")
    result = generate_summary(
        case_id=run["case_id"],
        triggered_by="test_m12",
        conn=db_conn,
        pipeline_run_id=run["pipeline_run_id"],
    )

    assert (
        result.summary_version == "v1"
    ), f"Attendu 'v1', reçu '{result.summary_version}'"
    assert result.case_id == run["case_id"]
    assert result.summary_status in ("ready", "partial", "blocked", "failed")
    assert result.result_hash, "result_hash ne peut pas être vide"
    assert result.result_hash != "placeholder", "result_hash non calculé"


# ── Test 2 ─────────────────────────────────────────────────


def test_generate_summary_has_required_sections(db_conn, pipeline_run_factory):
    """
    SummaryDocument contient au minimum sections 'context' et 'readiness'.
    INV-AS2.
    """
    run = pipeline_run_factory(status="partial_complete")
    result = generate_summary(
        case_id=run["case_id"],
        triggered_by="test_m12",
        conn=db_conn,
    )

    section_types = [s.section_type for s in result.sections]

    assert (
        "context" in section_types
    ), f"Section 'context' absente. Sections : {section_types}"
    assert (
        "readiness" in section_types
    ), f"Section 'readiness' absente. Sections : {section_types}"
    valid_types = {
        "context",
        "offers",
        "criteria",
        "scoring",
        "data_quality",
        "readiness",
    }
    for st in section_types:
        assert st in valid_types, f"section_type invalide : '{st}'"


# ── Test 3 ─────────────────────────────────────────────────


def test_generate_summary_has_no_stc_fields(db_conn, pipeline_run_factory):
    """
    INV-AS1/AS6 : SummaryDocument ne contient aucun champ STC.
    Scan JSON du document complet.
    """
    run = pipeline_run_factory(status="partial_complete")
    result = generate_summary(
        case_id=run["case_id"],
        triggered_by="test_m12",
        conn=db_conn,
    )

    result_json = result.model_dump_json()
    forbidden_patterns = [
        "stc_",
        "ngo_",
        "grant_",
        "save_the_children",
        "winner",
        "recommended_supplier",
        "ranking",
    ]
    for pattern in forbidden_patterns:
        assert pattern not in result_json.lower(), (
            f"Champ interdit '{pattern}' détecté dans SummaryDocument. "
            f"INV-AS1/AS6 violé."
        )


# ── Test 4 ─────────────────────────────────────────────────


def test_summary_section_rejects_winner_in_content():
    """
    INV-AS10 : winner dans SummarySection.content → ValidationError Pydantic.
    L'app guide — validation avant tout INSERT.
    """
    with pytest.raises(ValidationError) as exc_info:
        SummarySection(
            section_type="scoring",
            title="Scoring",
            content={"winner": "Supplier Alpha", "score": 85.0},
        )
    error_msg = str(exc_info.value).lower()
    assert (
        "winner" in error_msg or "interdit" in error_msg
    ), f"Message ValidationError inattendu : {exc_info.value}"


def test_summary_section_rejects_rank_in_content():
    """INV-AS10 : rank dans content → ValidationError."""
    with pytest.raises(ValidationError):
        SummarySection(
            section_type="criteria",
            title="Critères",
            content={"rank": 1, "score": 90.0},
        )


def test_summary_section_rejects_best_offer_in_content():
    """INV-AS10 : best_offer dans content → ValidationError."""
    with pytest.raises(ValidationError):
        SummarySection(
            section_type="offers",
            title="Offres",
            content={"best_offer": "Alpha 1000 XOF"},
        )


# ── Test 5 ─────────────────────────────────────────────────


def test_generate_summary_result_hash_deterministic(db_conn, pipeline_run_factory):
    """
    INV-AS9 / MG-01 : _compute_result_hash() produit le même hash
    pour le même SummaryDocument.
    result_hash — convention unique (pas source_result_hash).
    """
    run = pipeline_run_factory(status="partial_complete")
    result = generate_summary(
        case_id=run["case_id"],
        triggered_by="test_m12",
        conn=db_conn,
        pipeline_run_id=run["pipeline_run_id"],
    )

    hash1 = result.result_hash
    hash2 = _compute_result_hash(result)

    assert (
        hash1 == hash2
    ), f"result_hash non déterministe : '{hash1}' != '{hash2}'. INV-AS9 violé."
    assert len(hash1) == 64, f"SHA-256 attendu 64 chars, reçu {len(hash1)}"


# ── Test 6 ─────────────────────────────────────────────────


def test_generate_summary_idempotent_same_cas_same_hash(db_conn, pipeline_run_factory):
    """
    INV-AS9b : deux appels avec le même CAS v1 → même result_hash →
    une seule ligne dans analysis_summaries.
    UNIQUE(result_hash) prouvé.
    """
    run = pipeline_run_factory(status="partial_complete")

    result1 = generate_summary(
        case_id=run["case_id"],
        triggered_by="test_m12",
        conn=db_conn,
        pipeline_run_id=run["pipeline_run_id"],
    )
    result2 = generate_summary(
        case_id=run["case_id"],
        triggered_by="test_m12",
        conn=db_conn,
        pipeline_run_id=run["pipeline_run_id"],
    )

    assert (
        result1.result_hash == result2.result_hash
    ), "Hash diverge entre deux appels identiques — INV-AS9 violé"

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM public.analysis_summaries "
            "WHERE result_hash = %s",
            (result1.result_hash,),
        )
        row = cur.fetchone()
        count = row["n"] if isinstance(row, dict) else row[0]

    assert count == 1, f"Attendu 1 ligne (idempotence), trouvé {count}. INV-AS9b violé."


# ── Test 7 ─────────────────────────────────────────────────


def test_generate_summary_no_pipeline_run_returns_blocked(db_conn, case_factory):
    """
    Aucun pipeline_run pour ce case → summary_status='blocked'.
    errors structurés list[dict] avec reason_code. MG-02.
    """
    case_id = case_factory("XOF")
    result = generate_summary(
        case_id=case_id,
        triggered_by="test_m12",
        conn=db_conn,
    )

    assert (
        result.summary_status == "blocked"
    ), f"Attendu 'blocked', reçu '{result.summary_status}'"
    assert len(result.errors) > 0, "errors doit être non-vide si blocked"
    first_error = result.errors[0]
    assert isinstance(first_error, dict), "error doit être un dict (MG-02)"
    assert (
        "reason_code" in first_error
    ), f"reason_code absent dans error : {first_error}"
    assert first_error["reason_code"] == "NO_PIPELINE_RUN"


# ── Test 8 ─────────────────────────────────────────────────


def test_generate_summary_status_mapping(db_conn, pipeline_run_factory):
    """
    Mapping pipeline_status → summary_status (Section 6 — gravé).
    4 cas couverts.
    """
    mapping = {
        "partial_complete": "ready",
        "incomplete": "partial",
        "blocked": "blocked",
        "failed": "failed",
    }

    for pipeline_status, expected_summary_status in mapping.items():
        run = pipeline_run_factory(status=pipeline_status)
        result = generate_summary(
            case_id=run["case_id"],
            triggered_by="test_m12",
            conn=db_conn,
            pipeline_run_id=run["pipeline_run_id"],
        )
        assert result.summary_status == expected_summary_status, (
            f"pipeline_status='{pipeline_status}' → "
            f"attendu '{expected_summary_status}', reçu '{result.summary_status}'"
        )


# ── Test 9 (INV-AS5) ──────────────────────────────────────


def test_generate_summary_persists_result_jsonb_complete(db_conn, pipeline_run_factory):
    """
    INV-AS5 : result_jsonb en DB contient SummaryDocument complet.
    DB probe post-insert — prouve la persistance réelle.
    """
    import json as _json

    run = pipeline_run_factory(status="partial_complete")
    result = generate_summary(
        case_id=run["case_id"],
        triggered_by="test_m12",
        conn=db_conn,
    )

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT result_jsonb FROM public.analysis_summaries "
            "WHERE summary_id = %s",
            (result.summary_id,),
        )
        row = cur.fetchone()

    assert row is not None, "Ligne non trouvée dans analysis_summaries"
    jsonb = row["result_jsonb"] if isinstance(row, dict) else row[0]
    if isinstance(jsonb, str):
        jsonb = _json.loads(jsonb)

    assert (
        jsonb.get("summary_version") == "v1"
    ), "summary_version absent de result_jsonb — INV-AS4 violé"
    assert "sections" in jsonb, "sections absent de result_jsonb — INV-AS5 violé"
    jsonb_str = str(jsonb)
    assert (
        "winner" not in jsonb_str
    ), "winner détecté dans result_jsonb DB — INV-AS10 violé"


# ── Test 10 (MG-03) ───────────────────────────────────────


def test_build_summary_rejects_malformed_cas():
    """
    MG-03 OPTION A : CAS dict sans clés requises → ValueError structuré.
    Version non supportée → ValueError avec mention cas_version.
    """
    from src.couche_a.analysis_summary.engine.builder import build_summary

    # Cas 1 : version non supportée
    with pytest.raises(ValueError) as exc_info:
        build_summary({"cas_version": "v0_old", "case_id": "x"})
    error_msg = str(exc_info.value).lower()
    assert (
        "cas_version" in error_msg or "non support" in error_msg
    ), f"Message inattendu : {exc_info.value}"

    # Cas 2 : clés manquantes
    with pytest.raises(ValueError) as exc_info:
        build_summary({"cas_version": "v1"})
    error_msg = str(exc_info.value).lower()
    assert (
        "manquantes" in error_msg or "missing" in error_msg
    ), f"Message inattendu : {exc_info.value}"


# ── Test 11 ────────────────────────────────────────────────


def test_generate_summary_engine_does_not_call_pipeline(db_conn, pipeline_run_factory):
    """
    INV-AS8 : generate_summary() ne déclenche aucun pipeline.
    Vérification comportementale : pipeline_runs ne gagne aucune ligne.
    """
    run = pipeline_run_factory(status="partial_complete")

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM public.pipeline_runs WHERE case_id = %s",
            (run["case_id"],),
        )
        count_before = cur.fetchone()
        count_before = (
            count_before["n"] if isinstance(count_before, dict) else count_before[0]
        )

    generate_summary(
        case_id=run["case_id"],
        triggered_by="test_m12",
        conn=db_conn,
    )

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM public.pipeline_runs WHERE case_id = %s",
            (run["case_id"],),
        )
        count_after = cur.fetchone()
        count_after = (
            count_after["n"] if isinstance(count_after, dict) else count_after[0]
        )

    assert count_before == count_after, (
        f"pipeline_runs a gagné {count_after - count_before} ligne(s) — "
        f"INV-AS8 violé (pipeline déclenché depuis moteur)"
    )
