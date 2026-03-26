"""M12 — Passes 0, 0.5, 1 et orchestrateur FSM."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from src.annotation.orchestrator import (
    AnnotationOrchestrator,
    AnnotationPipelineState,
    use_pass_orchestrator,
)
from src.annotation.pass_output import PassRunStatus
from src.annotation.passes.pass_0_5_quality_gate import run_pass_0_5_quality_gate
from src.annotation.passes.pass_0_ingestion import run_pass_0_ingestion
from src.annotation.passes.pass_1_router import run_pass_1_router


def test_pass_0_normalizes_and_page_map():
    rid = uuid.uuid4()
    raw = "Hello  world\n\n" + "\f" + "Page deux"
    out = run_pass_0_ingestion(raw, document_id="d1", run_id=rid)
    assert out.status == PassRunStatus.SUCCESS
    assert "Hello world" in out.output_data["normalized_text"]
    pm = out.output_data["page_map"]
    assert len(pm) == 2
    assert out.output_data["features"]["char_count"] == len(
        out.output_data["normalized_text"]
    )


def test_pass_0_fails_empty():
    rid = uuid.uuid4()
    out = run_pass_0_ingestion("   \n\t  ", document_id="d1", run_id=rid)
    assert out.status == PassRunStatus.FAILED


def test_pass_0_5_ocr_failed_short():
    rid = uuid.uuid4()
    out = run_pass_0_5_quality_gate("x" * 50, document_id="d1", run_id=rid)
    assert out.status == PassRunStatus.SUCCESS
    assert out.output_data["quality_class"] == "ocr_failed"
    assert out.output_data["block_llm"] is True


def test_pass_0_5_good_long():
    rid = uuid.uuid4()
    text = "PROPOSITION TECHNIQUE\n" + ("word " * 300)
    out = run_pass_0_5_quality_gate(text, document_id="d1", run_id=rid)
    assert out.output_data["quality_class"] == "good"
    assert out.output_data["block_llm"] is False


def test_pass_1_deterministic_financial():
    rid = uuid.uuid4()
    text = "# PROPOSITION FINANCIÈRE\n" + "x" * 500
    out = run_pass_1_router(
        text,
        document_id="d1",
        run_id=rid,
        block_llm=False,
    )
    assert out.status == PassRunStatus.SUCCESS
    assert out.output_data["document_role"] == "financial_offer"
    assert out.output_data["routing_source"] == "deterministic_classifier"
    assert out.output_data["routing_confidence"] in (0.6, 0.8, 1.0)


def test_pass_1_filename_rfq():
    rid = uuid.uuid4()
    text = "Contenu sans titre structuré " * 50
    out = run_pass_1_router(
        text,
        document_id="d1",
        run_id=rid,
        block_llm=False,
        filename="demande_RFQ_2024.pdf",
    )
    assert out.output_data["taxonomy_core"] == "rfq"
    assert out.output_data["routing_source"] == "deterministic_classifier"


def test_pass_1_block_llm_unknown():
    rid = uuid.uuid4()
    text = "lorem ipsum " * 20
    out = run_pass_1_router(
        text,
        document_id="d1",
        run_id=rid,
        block_llm=True,
    )
    assert out.status == PassRunStatus.DEGRADED
    assert out.output_data["document_role"] == "unknown"
    assert out.output_data["routing_source"] == "human"


def test_pass_1_llm_invalid_enums_degraded():
    rid = uuid.uuid4()
    text = "lorem ipsum " * 20

    def bad_llm(_t: str) -> dict:
        return {
            "document_role": "not_a_real_role",
            "taxonomy_core": "offer_financial",
            "confidence": 1.0,
            "validated": True,
        }

    out = run_pass_1_router(
        text,
        document_id="d1",
        run_id=rid,
        block_llm=False,
        llm_router=bad_llm,
    )
    assert out.status == PassRunStatus.DEGRADED
    assert out.output_data["document_role"] == "unknown"
    assert any(e.code == "LLM_PROPOSAL_INVALID" for e in out.errors)


def test_pass_1_llm_router_injected():
    rid = uuid.uuid4()
    text = "lorem ipsum " * 20

    def fake_llm(_t: str) -> dict:
        return {
            "document_role": "financial_offer",
            "taxonomy_core": "offer_financial",
            "confidence": 1.0,
            "validated": True,
            "model_used": "stub",
        }

    out = run_pass_1_router(
        text,
        document_id="d1",
        run_id=rid,
        block_llm=False,
        llm_router=fake_llm,
    )
    assert out.status == PassRunStatus.SUCCESS
    assert out.output_data["routing_source"] == "llm_proposal_validated"


def test_orchestrator_happy_path(tmp_path: Path):
    orch = AnnotationOrchestrator(runs_dir=tmp_path, strict_block_llm_on_poor=True)
    rid = uuid.uuid4()
    text = "# OFFRE TECHNIQUE\n" + "detail " * 400
    rec, state = orch.run_passes_0_to_1(
        text,
        document_id="doc-x",
        run_id=rid,
    )
    assert state == AnnotationPipelineState.LLM_PREANNOTATION_PENDING
    assert rec.state == AnnotationPipelineState.LLM_PREANNOTATION_PENDING.value
    loaded = orch.load_run(rid)
    assert loaded is not None
    assert "pass_0_ingestion" in loaded.pass_outputs


def test_orchestrator_pass0_failed_logs_dead_letter(tmp_path: Path):
    orch = AnnotationOrchestrator(runs_dir=tmp_path)
    rid = uuid.uuid4()
    rec, state = orch.run_passes_0_to_1("   \n\t  ", document_id="d", run_id=rid)
    assert state == AnnotationPipelineState.DEAD_LETTER
    assert rec.transition_log
    assert rec.transition_log[-1]["to_state"] == "dead_letter"
    assert rec.transition_log[-1]["pass_name"] == "pass_0_ingestion"


def test_orchestrator_ocr_failed_review(tmp_path: Path):
    orch = AnnotationOrchestrator(runs_dir=tmp_path)
    rid = uuid.uuid4()
    rec, state = orch.run_passes_0_to_1("tiny", document_id="d", run_id=rid)
    assert state == AnnotationPipelineState.REVIEW_REQUIRED
    assert "pass_1_router" not in rec.pass_outputs


def test_use_pass_orchestrator_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("ANNOTATION_USE_PASS_ORCHESTRATOR", raising=False)
    assert use_pass_orchestrator() is False
    monkeypatch.setenv("ANNOTATION_USE_PASS_ORCHESTRATOR", "1")
    assert use_pass_orchestrator() is True


# ── Edge-case tests ─────────────────────────────────────────────────────────


def test_pass_0_unicode_nfkc():
    rid = uuid.uuid4()
    raw = "\ufb01nancière\r\ntest\r"
    out = run_pass_0_ingestion(raw, document_id="d1", run_id=rid)
    assert out.status == PassRunStatus.SUCCESS
    assert "fi" in out.output_data["normalized_text"]
    assert "\r" not in out.output_data["normalized_text"]


def test_pass_0_5_high_replacement_chars():
    rid = uuid.uuid4()
    text = "a" * 500 + "\ufffd" * 55
    out = run_pass_0_5_quality_gate(text, document_id="d1", run_id=rid)
    assert out.output_data["quality_class"] == "ocr_failed"
    assert out.output_data["block_llm"] is True


def test_pass_0_5_degraded_range():
    rid = uuid.uuid4()
    text = "a" * 500
    out = run_pass_0_5_quality_gate(text, document_id="d1", run_id=rid)
    assert out.output_data["quality_class"] == "degraded"


def test_pass_0_5_poor_short():
    rid = uuid.uuid4()
    text = "a" * 150
    out = run_pass_0_5_quality_gate(text, document_id="d1", run_id=rid)
    assert out.output_data["quality_class"] == "poor"
    assert out.output_data["block_llm"] is True


def test_pass_1_routing_failure_reason_present():
    rid = uuid.uuid4()
    text = "lorem ipsum " * 20
    out = run_pass_1_router(text, document_id="d1", run_id=rid, block_llm=True)
    assert "routing_failure_reason" in out.output_data
    assert out.output_data["routing_failure_reason"] is not None


def test_pass_1_deterministic_no_failure_reason():
    rid = uuid.uuid4()
    text = "# OFFRE TECHNIQUE\n" + "x" * 500
    out = run_pass_1_router(text, document_id="d1", run_id=rid, block_llm=False)
    assert out.output_data["routing_failure_reason"] is None


def test_pass_1_dao_uses_generic_taxonomy():
    rid = uuid.uuid4()
    text = "DOSSIER D'APPEL D'OFFRES\n" + "x" * 500
    out = run_pass_1_router(text, document_id="d1", run_id=rid, block_llm=False)
    assert out.output_data["taxonomy_core"] == "dao"


def test_pass_1_llm_router_exception():
    rid = uuid.uuid4()
    text = "lorem ipsum " * 20

    def exploding_llm(_t: str) -> dict:
        raise RuntimeError("API down")

    out = run_pass_1_router(
        text,
        document_id="d1",
        run_id=rid,
        block_llm=False,
        llm_router=exploding_llm,
    )
    assert out.status == PassRunStatus.FAILED
    assert any(e.code == "LLM_ROUTER_ERROR" for e in out.errors)


def test_classifier_confidence_never_zero():
    from src.annotation.document_classifier import classify_document

    result = classify_document("lorem ipsum dolor sit amet")
    assert result.confidence >= 0.6


def test_orchestrator_idempotent(tmp_path: Path):
    orch = AnnotationOrchestrator(runs_dir=tmp_path)
    rid = uuid.uuid4()
    text = "# OFFRE TECHNIQUE\n" + "detail " * 400
    rec1, state1 = orch.run_passes_0_to_1(text, document_id="d", run_id=rid)
    rec2, state2 = orch.run_passes_0_to_1(text, document_id="d", run_id=rid)
    assert state1 == state2
    assert rec2.run_id == rec1.run_id


def test_orchestrator_retry_on_pass_exception(tmp_path: Path):
    call_count = 0

    original_p0 = run_pass_0_ingestion

    def flaky_p0(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("transient failure")
        return original_p0(*args, **kwargs)

    import src.annotation.orchestrator as orch_mod

    saved = orch_mod.run_pass_0_ingestion
    orch_mod.run_pass_0_ingestion = flaky_p0
    try:
        orch = AnnotationOrchestrator(runs_dir=tmp_path, max_retries=2)
        rid = uuid.uuid4()
        rec, state = orch.run_passes_0_to_1(
            "# OFFRE TECHNIQUE\n" + "detail " * 400,
            document_id="d",
            run_id=rid,
        )
        assert state != AnnotationPipelineState.DEAD_LETTER
        assert call_count == 2
    finally:
        orch_mod.run_pass_0_ingestion = saved
