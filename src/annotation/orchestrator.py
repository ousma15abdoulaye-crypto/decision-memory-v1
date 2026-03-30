"""
Orchestrateur FSM — pipeline d'annotation multipasses.

Spec : docs/contracts/annotation/ANNOTATION_ORCHESTRATOR_FSM.md
Feature flag : ANNOTATION_USE_PASS_ORCHESTRATOR (défaut 0) — Phase 3 strangler.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from src.annotation.pass_output import (
    AnnotationPassOutput,
    PassError,
    PassRunStatus,
)
from src.annotation.passes.pass_0_5_quality_gate import run_pass_0_5_quality_gate
from src.annotation.passes.pass_0_ingestion import run_pass_0_ingestion
from src.annotation.passes.pass_1_router import run_pass_1_router
from src.annotation.passes.pass_1a_core_recognition import (
    run_pass_1a_core_recognition,
)
from src.annotation.passes.pass_1b_document_validity import (
    run_pass_1b_document_validity,
)
from src.annotation.passes.pass_1c_conformity_and_handoffs import (
    run_pass_1c_conformity_and_handoffs,
)
from src.annotation.passes.pass_1d_process_linking import (
    run_pass_1d_process_linking,
)

logger = logging.getLogger(__name__)

ENV_USE_ORCHESTRATOR = "ANNOTATION_USE_PASS_ORCHESTRATOR"
ENV_USE_M12_SUBPASSES = "ANNOTATION_USE_M12_SUBPASSES"

_DEFAULT_MAX_ATTEMPTS = 2


def use_pass_orchestrator() -> bool:
    return os.environ.get(ENV_USE_ORCHESTRATOR, "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def use_m12_subpasses() -> bool:
    """Feature flag: when enabled, run_passes_0_to_1 chains 1A-1D instead of pass_1_router."""
    return os.environ.get(ENV_USE_M12_SUBPASSES, "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


class AnnotationPipelineState(StrEnum):
    INGESTED = "ingested"
    PASS_0_DONE = "pass_0_done"
    QUALITY_ASSESSED = "quality_assessed"
    ROUTED = "routed"
    # M12 sub-pass states
    PASS_1A_DONE = "pass_1a_done"
    PASS_1B_DONE = "pass_1b_done"
    PASS_1C_DONE = "pass_1c_done"
    PASS_1D_DONE = "pass_1d_done"
    LLM_PREANNOTATION_PENDING = "llm_preannotation_pending"
    LLM_PREANNOTATION_DONE = "llm_preannotation_done"
    VALIDATED = "validated"
    REVIEW_REQUIRED = "review_required"
    ANNOTATED_VALIDATED = "annotated_validated"
    REJECTED = "rejected"
    DEAD_LETTER = "dead_letter"


@dataclass
class TransitionLogEntry:
    run_id: str
    document_id: str
    from_state: str
    to_state: str
    pass_name: str
    duration_ms: int
    status: str
    error_codes: list[str] = field(default_factory=list)


@dataclass
class PipelineRunRecord:
    run_id: str
    document_id: str
    state: str
    pass_outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    transition_log: list[dict[str, Any]] = field(default_factory=list)


def _serialize_pass_output(out: AnnotationPassOutput) -> dict[str, Any]:
    return out.model_dump(mode="json")


def default_pipeline_runs_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    d = root / "data" / "annotation_pipeline_runs"
    return d


class AnnotationOrchestrator:
    """
    Enchaîne Pass 0 → 0.5 → 1 avec persistance JSON et journalisation des transitions.
    Each pass is attempted up to ``max_attempts`` times before declaring failure (FSM §3).
    """

    def __init__(
        self,
        *,
        runs_dir: Path | None = None,
        strict_block_llm_on_poor: bool = True,
        llm_router: Callable[[str], dict[str, Any]] | None = None,
        max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
    ) -> None:
        if max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")
        self.runs_dir = runs_dir or default_pipeline_runs_dir()
        self.strict_block_llm_on_poor = strict_block_llm_on_poor
        self.llm_router = llm_router
        self.max_attempts = max_attempts

    def _path(self, run_id: uuid.UUID) -> Path:
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        return self.runs_dir / f"{run_id}.json"

    def load_run(self, run_id: uuid.UUID) -> PipelineRunRecord | None:
        p = self._path(run_id)
        if not p.is_file():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        return PipelineRunRecord(
            run_id=data["run_id"],
            document_id=data["document_id"],
            state=data["state"],
            pass_outputs=data.get("pass_outputs", {}),
            transition_log=data.get("transition_log", []),
        )

    def save_run(self, record: PipelineRunRecord) -> None:
        p = self._path(uuid.UUID(record.run_id))
        p.write_text(
            json.dumps(asdict(record), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _log_transition(
        self,
        record: PipelineRunRecord,
        *,
        from_state: str,
        to_state: str,
        pass_name: str,
        out: AnnotationPassOutput,
    ) -> None:
        codes = [e.code for e in out.errors]
        if not codes:
            codes = []
        entry = TransitionLogEntry(
            run_id=record.run_id,
            document_id=record.document_id,
            from_state=from_state,
            to_state=to_state,
            pass_name=pass_name,
            duration_ms=int(out.metadata.get("duration_ms", 0)),
            status=str(out.status.value),
            error_codes=codes,
        )
        record.transition_log.append(asdict(entry))
        logger.info(
            "annotation_fsm_transition",
            extra={
                "run_id": entry.run_id,
                "document_id": entry.document_id,
                "from_state": entry.from_state,
                "to_state": entry.to_state,
                "pass_name": entry.pass_name,
                "duration_ms": entry.duration_ms,
                "status": entry.status,
                "error_codes": entry.error_codes,
            },
        )

    def _run_pass_with_retry(
        self,
        pass_fn: Callable[..., AnnotationPassOutput],
        pass_name: str,
        **kwargs: Any,
    ) -> AnnotationPassOutput:
        """Execute a pass up to ``self.max_attempts`` times; return on first non-FAILED result."""
        last_output: AnnotationPassOutput | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = pass_fn(**kwargs)
                if result.status != PassRunStatus.FAILED:
                    return result
                last_output = result
                if attempt < self.max_attempts:
                    logger.warning(
                        "annotation_pass_retry",
                        extra={
                            "pass_name": pass_name,
                            "attempt": attempt,
                            "max_attempts": self.max_attempts,
                            "status": result.status.value,
                        },
                    )
            except Exception as exc:
                logger.exception(
                    "annotation_pass_exception",
                    extra={"pass_name": pass_name, "attempt": attempt},
                )
                last_output = AnnotationPassOutput(
                    pass_name=pass_name,
                    pass_version="1.0.0",
                    document_id=kwargs.get("document_id", ""),
                    run_id=kwargs.get("run_id", uuid.uuid4()),
                    started_at=AnnotationPassOutput.utc_now(),
                    completed_at=AnnotationPassOutput.utc_now(),
                    status=PassRunStatus.FAILED,
                    output_data={},
                    errors=[
                        PassError(
                            code="PASS_EXCEPTION",
                            message=str(exc)[:500],
                            detail={"type": type(exc).__name__},
                        )
                    ],
                    metadata={"duration_ms": 0},
                )
        assert last_output is not None  # noqa: S101
        return last_output

    def run_passes_0_to_1(
        self,
        raw_text: str,
        *,
        document_id: str,
        run_id: uuid.UUID,
        file_metadata: dict[str, Any] | None = None,
        filename: str | None = None,
    ) -> tuple[PipelineRunRecord, AnnotationPipelineState]:
        """
        Exécute jusqu'à ``routed`` (ou ``dead_letter`` / ``review_required``).

        If a persisted record already exists for *run_id*, execution is skipped
        and the existing record is returned unchanged.
        """
        existing = self.load_run(run_id)
        if existing is not None:
            logger.info(
                "annotation_orchestrator_idempotent_skip",
                extra={"run_id": str(run_id), "state": existing.state},
            )
            return existing, AnnotationPipelineState(existing.state)

        record = PipelineRunRecord(
            run_id=str(run_id),
            document_id=document_id,
            state=AnnotationPipelineState.INGESTED.value,
        )

        # Pass 0 (with retry)
        p0 = self._run_pass_with_retry(
            run_pass_0_ingestion,
            "pass_0_ingestion",
            raw_text=raw_text,
            document_id=document_id,
            run_id=run_id,
            file_metadata=file_metadata,
        )
        record.pass_outputs["pass_0_ingestion"] = _serialize_pass_output(p0)
        if p0.status == PassRunStatus.FAILED:
            self._log_transition(
                record,
                from_state=AnnotationPipelineState.INGESTED.value,
                to_state=AnnotationPipelineState.DEAD_LETTER.value,
                pass_name="pass_0_ingestion",
                out=p0,
            )
            record.state = AnnotationPipelineState.DEAD_LETTER.value
            self.save_run(record)
            return record, AnnotationPipelineState.DEAD_LETTER

        self._log_transition(
            record,
            from_state=AnnotationPipelineState.INGESTED.value,
            to_state=AnnotationPipelineState.PASS_0_DONE.value,
            pass_name="pass_0_ingestion",
            out=p0,
        )

        normalized = (p0.output_data or {}).get("normalized_text") or ""
        record.state = AnnotationPipelineState.PASS_0_DONE.value

        # Pass 0.5 (with retry)
        p05 = self._run_pass_with_retry(
            run_pass_0_5_quality_gate,
            "pass_0_5_quality_gate",
            normalized_text=normalized,
            document_id=document_id,
            run_id=run_id,
            strict_block_llm_on_poor=self.strict_block_llm_on_poor,
        )
        record.pass_outputs["pass_0_5_quality_gate"] = _serialize_pass_output(p05)
        if p05.status == PassRunStatus.FAILED:
            self._log_transition(
                record,
                from_state=AnnotationPipelineState.PASS_0_DONE.value,
                to_state=AnnotationPipelineState.DEAD_LETTER.value,
                pass_name="pass_0_5_quality_gate",
                out=p05,
            )
            record.state = AnnotationPipelineState.DEAD_LETTER.value
            self.save_run(record)
            return record, AnnotationPipelineState.DEAD_LETTER

        self._log_transition(
            record,
            from_state=AnnotationPipelineState.PASS_0_DONE.value,
            to_state=AnnotationPipelineState.QUALITY_ASSESSED.value,
            pass_name="pass_0_5_quality_gate",
            out=p05,
        )

        record.state = AnnotationPipelineState.QUALITY_ASSESSED.value
        qc = (p05.output_data or {}).get("quality_class")
        block_llm = bool((p05.output_data or {}).get("block_llm"))

        if qc == "ocr_failed":
            record.state = AnnotationPipelineState.REVIEW_REQUIRED.value
            self.save_run(record)
            return record, AnnotationPipelineState.REVIEW_REQUIRED

        # Feature flag: M12 sub-passes (1A->1D) vs legacy pass_1_router
        if use_m12_subpasses():
            self.save_run(record)
            return self.run_passes_1a_to_1d(
                normalized,
                document_id=document_id,
                run_id=run_id,
                quality_class=qc or "good",
                block_llm=block_llm,
            )

        # Legacy path: Pass 1 — deterministe / LLM optionnel (with retry)
        p1_pass_name = (
            "pass_1_router_llm"
            if (not block_llm and self.llm_router is not None)
            else "pass_1_router"
        )
        p1 = self._run_pass_with_retry(
            run_pass_1_router,
            p1_pass_name,
            normalized_text=normalized,
            document_id=document_id,
            run_id=run_id,
            block_llm=block_llm,
            filename=filename,
            llm_router=self.llm_router,
        )
        record.pass_outputs["pass_1_router"] = _serialize_pass_output(p1)
        if p1.status == PassRunStatus.FAILED:
            self._log_transition(
                record,
                from_state=AnnotationPipelineState.QUALITY_ASSESSED.value,
                to_state=AnnotationPipelineState.DEAD_LETTER.value,
                pass_name="pass_1_router",
                out=p1,
            )
            record.state = AnnotationPipelineState.DEAD_LETTER.value
            self.save_run(record)
            return record, AnnotationPipelineState.DEAD_LETTER

        self._log_transition(
            record,
            from_state=AnnotationPipelineState.QUALITY_ASSESSED.value,
            to_state=AnnotationPipelineState.ROUTED.value,
            pass_name="pass_1_router",
            out=p1,
        )

        record.state = AnnotationPipelineState.ROUTED.value

        if not block_llm and p1.status in (
            PassRunStatus.SUCCESS,
            PassRunStatus.DEGRADED,
        ):
            record.state = AnnotationPipelineState.LLM_PREANNOTATION_PENDING.value

        self.save_run(record)
        return record, AnnotationPipelineState(record.state)

    def run_passes_1a_to_1d(
        self,
        normalized_text: str,
        *,
        document_id: str,
        run_id: uuid.UUID,
        quality_class: str = "good",
        block_llm: bool = False,
        case_documents_1a: list[dict[str, Any]] | None = None,
    ) -> tuple[PipelineRunRecord, AnnotationPipelineState]:
        """
        Execute M12 sub-passes (1A -> 1B -> 1C -> 1D) after Pass 0.5 is done.

        Expects a pre-existing PipelineRunRecord at state >= QUALITY_ASSESSED.
        """
        existing = self.load_run(run_id)
        if existing is None:
            record = PipelineRunRecord(
                run_id=str(run_id),
                document_id=document_id,
                state=AnnotationPipelineState.QUALITY_ASSESSED.value,
            )
        else:
            record = existing

        # ── Pass 1A: Core Recognition ──
        p1a = self._run_pass_with_retry(
            run_pass_1a_core_recognition,
            "pass_1a_core_recognition",
            normalized_text=normalized_text,
            document_id=document_id,
            run_id=run_id,
            quality_class=quality_class,
            block_llm=block_llm,
        )
        record.pass_outputs["pass_1a_core_recognition"] = _serialize_pass_output(p1a)
        if p1a.status == PassRunStatus.FAILED:
            self._log_transition(
                record,
                from_state=record.state,
                to_state=AnnotationPipelineState.DEAD_LETTER.value,
                pass_name="pass_1a_core_recognition",
                out=p1a,
            )
            record.state = AnnotationPipelineState.DEAD_LETTER.value
            self.save_run(record)
            return record, AnnotationPipelineState.DEAD_LETTER

        self._log_transition(
            record,
            from_state=record.state,
            to_state=AnnotationPipelineState.PASS_1A_DONE.value,
            pass_name="pass_1a_core_recognition",
            out=p1a,
        )
        record.state = AnnotationPipelineState.PASS_1A_DONE.value

        m12_rec = (p1a.output_data or {}).get("m12_recognition", {})
        doc_kind = m12_rec.get("document_kind", {}).get("value", "unknown")

        # ── Pass 1B: Document Validity ──
        p1b = self._run_pass_with_retry(
            run_pass_1b_document_validity,
            "pass_1b_document_validity",
            normalized_text=normalized_text,
            document_id=document_id,
            run_id=run_id,
            document_kind=doc_kind,
            quality_class=quality_class,
        )
        record.pass_outputs["pass_1b_document_validity"] = _serialize_pass_output(p1b)
        if p1b.status == PassRunStatus.FAILED:
            self._log_transition(
                record,
                from_state=record.state,
                to_state=AnnotationPipelineState.DEAD_LETTER.value,
                pass_name="pass_1b_document_validity",
                out=p1b,
            )
            record.state = AnnotationPipelineState.DEAD_LETTER.value
            self.save_run(record)
            return record, AnnotationPipelineState.DEAD_LETTER

        self._log_transition(
            record,
            from_state=record.state,
            to_state=AnnotationPipelineState.PASS_1B_DONE.value,
            pass_name="pass_1b_document_validity",
            out=p1b,
        )
        record.state = AnnotationPipelineState.PASS_1B_DONE.value

        # ── Pass 1C: Conformity + Handoffs ──
        validity_dict = (p1b.output_data or {}).get("m12_validity", {})
        is_composite = m12_rec.get("is_composite", {}).get("value", "unknown")
        fw_str = m12_rec.get("framework_detected", {}).get("value", "unknown")
        fw_conf = m12_rec.get("framework_detected", {}).get("confidence", 0.0)
        fam_str = m12_rec.get("procurement_family", {}).get("value", "unknown")
        fam_sub_str = m12_rec.get("procurement_family_sub", {}).get("value", "generic")

        p1c = self._run_pass_with_retry(
            run_pass_1c_conformity_and_handoffs,
            "pass_1c_conformity_and_handoffs",
            normalized_text=normalized_text,
            document_id=document_id,
            run_id=run_id,
            document_kind_str=doc_kind,
            is_composite=is_composite,
            validity_dict=validity_dict,
            framework_str=fw_str,
            framework_confidence=fw_conf,
            family_str=fam_str,
            family_sub_str=fam_sub_str,
        )
        record.pass_outputs["pass_1c_conformity_and_handoffs"] = _serialize_pass_output(
            p1c
        )
        if p1c.status == PassRunStatus.FAILED:
            self._log_transition(
                record,
                from_state=record.state,
                to_state=AnnotationPipelineState.DEAD_LETTER.value,
                pass_name="pass_1c_conformity_and_handoffs",
                out=p1c,
            )
            record.state = AnnotationPipelineState.DEAD_LETTER.value
            self.save_run(record)
            return record, AnnotationPipelineState.DEAD_LETTER

        self._log_transition(
            record,
            from_state=record.state,
            to_state=AnnotationPipelineState.PASS_1C_DONE.value,
            pass_name="pass_1c_conformity_and_handoffs",
            out=p1c,
        )
        record.state = AnnotationPipelineState.PASS_1C_DONE.value

        # ── Pass 1D: Process Linking ──
        p1d = self._run_pass_with_retry(
            run_pass_1d_process_linking,
            "pass_1d_process_linking",
            normalized_text=normalized_text,
            document_id=document_id,
            run_id=run_id,
            pass_1a_output_data=p1a.output_data or {},
            case_documents_1a=case_documents_1a,
        )
        record.pass_outputs["pass_1d_process_linking"] = _serialize_pass_output(p1d)
        if p1d.status == PassRunStatus.FAILED:
            self._log_transition(
                record,
                from_state=record.state,
                to_state=AnnotationPipelineState.DEAD_LETTER.value,
                pass_name="pass_1d_process_linking",
                out=p1d,
            )
            record.state = AnnotationPipelineState.DEAD_LETTER.value
            self.save_run(record)
            return record, AnnotationPipelineState.DEAD_LETTER

        self._log_transition(
            record,
            from_state=record.state,
            to_state=AnnotationPipelineState.PASS_1D_DONE.value,
            pass_name="pass_1d_process_linking",
            out=p1d,
        )
        record.state = AnnotationPipelineState.PASS_1D_DONE.value
        self.save_run(record)
        return record, AnnotationPipelineState.PASS_1D_DONE
