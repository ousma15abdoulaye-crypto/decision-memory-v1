"""
Orchestrateur FSM — pipeline d'annotation multipasses.

Feature flag : ANNOTATION_USE_PASS_ORCHESTRATOR (défaut 0) — Phase 3 strangler.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
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
from src.annotation.passes.pass_2a_regulatory_profile import (
    run_pass_2a_regulatory_profile,
)

from .records import PipelineRunRecord, TransitionLogEntry, serialize_pass_output
from .state import (
    _DEFAULT_MAX_ATTEMPTS,
    M12_RESUMABLE_STATES,
    M12_STATE_ORDER,
    TERMINAL_STATES,
    AnnotationPipelineState,
    m12_run_terminal,
    use_m12_subpasses,
    use_pass_2a,
)

logger = logging.getLogger(__name__)


def default_pipeline_runs_dir() -> Path:
    root = Path(__file__).resolve().parents[3]
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
        tmp = p.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(asdict(record), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, p)

    def _reconstruct_pass_output(
        self, record: PipelineRunRecord, pass_key: str
    ) -> AnnotationPassOutput | None:
        """Deserialize a stored pass output dict back to an AnnotationPassOutput."""
        stored = record.pass_outputs.get(pass_key)
        if not stored:
            return None
        try:
            return AnnotationPassOutput.model_validate(stored)
        except Exception:
            logger.warning(
                "annotation_orchestrator_checkpoint_corrupt",
                extra={"run_id": record.run_id, "pass_key": pass_key},
            )
            return None

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
        case_documents_1a: list[dict[str, Any]] | None = None,
        case_id: str | None = None,
    ) -> tuple[PipelineRunRecord, AnnotationPipelineState]:
        """
        Exécute jusqu'à ``routed`` (ou ``dead_letter`` / ``review_required``).

        If a persisted record already exists for *run_id*, execution is skipped
        and the existing record is returned unchanged.
        """
        existing = self.load_run(run_id)
        if existing is not None:
            existing_state = AnnotationPipelineState(existing.state)
            if existing_state in TERMINAL_STATES:
                logger.info(
                    "annotation_orchestrator_idempotent_skip",
                    extra={"run_id": str(run_id), "state": existing.state},
                )
                return existing, existing_state
            if use_m12_subpasses() and existing_state in M12_RESUMABLE_STATES:
                logger.warning(
                    "annotation_orchestrator_recovery",
                    extra={
                        "run_id": str(run_id),
                        "state": existing.state,
                        "action": "resuming_from_checkpoint",
                    },
                )
                p0_out = (existing.pass_outputs.get("pass_0_ingestion") or {}).get(
                    "output_data"
                ) or {}
                p05_out = (
                    existing.pass_outputs.get("pass_0_5_quality_gate") or {}
                ).get("output_data") or {}
                normalized = p0_out.get("normalized_text") or raw_text
                qc = p05_out.get("quality_class") or "good"
                block_llm = bool(p05_out.get("block_llm"))
                return self.run_passes_1a_to_1d(
                    normalized,
                    document_id=document_id,
                    run_id=run_id,
                    quality_class=qc,
                    block_llm=block_llm,
                    case_documents_1a=case_documents_1a,
                )
            if existing_state in M12_RESUMABLE_STATES:
                logger.error(
                    "annotation_orchestrator_stuck_run_subpasses_disabled",
                    extra={
                        "run_id": str(run_id),
                        "state": existing.state,
                        "action": "manual_requeue_or_enable_m12_subpasses_required",
                    },
                )
                raise RuntimeError(
                    f"Run {run_id} est bloqué en état {existing.state!r} "
                    "mais use_m12_subpasses() est désactivé. "
                    "Réactivez M12_SUBPASSES ou requeuez manuellement."
                )
            logger.warning(
                "annotation_orchestrator_unknown_state_skip",
                extra={"run_id": str(run_id), "state": existing.state},
            )
            return existing, existing_state

        record = PipelineRunRecord(
            run_id=str(run_id),
            document_id=document_id,
            state=AnnotationPipelineState.INGESTED.value,
        )

        p0 = self._run_pass_with_retry(
            run_pass_0_ingestion,
            "pass_0_ingestion",
            raw_text=raw_text,
            document_id=document_id,
            run_id=run_id,
            file_metadata=file_metadata,
        )
        record.pass_outputs["pass_0_ingestion"] = serialize_pass_output(p0)
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

        p05 = self._run_pass_with_retry(
            run_pass_0_5_quality_gate,
            "pass_0_5_quality_gate",
            normalized_text=normalized,
            document_id=document_id,
            run_id=run_id,
            strict_block_llm_on_poor=self.strict_block_llm_on_poor,
        )
        record.pass_outputs["pass_0_5_quality_gate"] = serialize_pass_output(p05)
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

        if use_m12_subpasses():
            self.save_run(record)
            return self.run_passes_1a_to_1d(
                normalized,
                document_id=document_id,
                run_id=run_id,
                quality_class=qc or "good",
                block_llm=block_llm,
                case_documents_1a=case_documents_1a,
                case_id=case_id,
            )

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
        record.pass_outputs["pass_1_router"] = serialize_pass_output(p1)
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
        case_id: str | None = None,
    ) -> tuple[PipelineRunRecord, AnnotationPipelineState]:
        """
        Execute M12 sub-passes (1A -> 1B -> 1C -> 1D) after Pass 0.5 is done.
        Supports checkpoint recovery.
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

        current_state = AnnotationPipelineState(record.state)

        if m12_run_terminal(current_state):
            return record, current_state

        def _state_rank(s: AnnotationPipelineState) -> int:
            try:
                return M12_STATE_ORDER.index(s)
            except ValueError:
                return -1

        def _is_done(target: AnnotationPipelineState) -> bool:
            return _state_rank(current_state) >= _state_rank(target)

        def _reset_from(pass_name: str, new_state: AnnotationPipelineState) -> None:
            """Reset record state to new_state and clear all downstream pass outputs."""
            logger.warning(
                "annotation_orchestrator_checkpoint_corrupt_reset",
                extra={
                    "run_id": str(run_id),
                    "corrupt_pass": pass_name,
                    "reset_to_state": new_state.value,
                },
            )
            record.state = new_state.value
            downstream = {
                "pass_1a_core_recognition": [
                    "pass_1b_document_validity",
                    "pass_1c_conformity_and_handoffs",
                    "pass_1d_process_linking",
                    "pass_2a_regulatory_profile",
                ],
                "pass_1b_document_validity": [
                    "pass_1c_conformity_and_handoffs",
                    "pass_1d_process_linking",
                    "pass_2a_regulatory_profile",
                ],
                "pass_1c_conformity_and_handoffs": [
                    "pass_1d_process_linking",
                    "pass_2a_regulatory_profile",
                ],
                "pass_1d_process_linking": ["pass_2a_regulatory_profile"],
                "pass_2a_regulatory_profile": [],
            }
            for key in downstream.get(pass_name, []):
                record.pass_outputs.pop(key, None)

        # ── Pass 1A: Core Recognition ──
        p1a: AnnotationPassOutput | None = None
        if _is_done(AnnotationPipelineState.PASS_1A_DONE):
            p1a = self._reconstruct_pass_output(record, "pass_1a_core_recognition")
            if p1a is not None:
                logger.info(
                    "annotation_orchestrator_checkpoint_hit",
                    extra={"run_id": str(run_id), "pass": "1a"},
                )
            else:
                _reset_from(
                    "pass_1a_core_recognition",
                    AnnotationPipelineState.QUALITY_ASSESSED,
                )
        if p1a is None:
            p1a = self._run_pass_with_retry(
                run_pass_1a_core_recognition,
                "pass_1a_core_recognition",
                normalized_text=normalized_text,
                document_id=document_id,
                run_id=run_id,
                quality_class=quality_class,
                block_llm=block_llm,
            )
            record.pass_outputs["pass_1a_core_recognition"] = serialize_pass_output(p1a)
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
            self.save_run(record)

        m12_rec = (p1a.output_data or {}).get("m12_recognition", {})
        doc_kind = m12_rec.get("document_kind", {}).get("value", "unknown")

        # ── Pass 1B: Document Validity ──
        p1b: AnnotationPassOutput | None = None
        if _is_done(AnnotationPipelineState.PASS_1B_DONE):
            p1b = self._reconstruct_pass_output(record, "pass_1b_document_validity")
            if p1b is not None:
                logger.info(
                    "annotation_orchestrator_checkpoint_hit",
                    extra={"run_id": str(run_id), "pass": "1b"},
                )
            else:
                _reset_from(
                    "pass_1b_document_validity",
                    AnnotationPipelineState.PASS_1A_DONE,
                )
        if p1b is None:
            p1b = self._run_pass_with_retry(
                run_pass_1b_document_validity,
                "pass_1b_document_validity",
                normalized_text=normalized_text,
                document_id=document_id,
                run_id=run_id,
                document_kind=doc_kind,
                quality_class=quality_class,
            )
            record.pass_outputs["pass_1b_document_validity"] = serialize_pass_output(
                p1b
            )
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
            self.save_run(record)

        # ── Pass 1C: Conformity + Handoffs ──
        validity_dict = (p1b.output_data or {}).get("m12_validity", {})
        is_composite = m12_rec.get("is_composite", {}).get("value", "unknown")
        fw_str = m12_rec.get("framework_detected", {}).get("value", "unknown")
        fw_conf = m12_rec.get("framework_detected", {}).get("confidence", 0.0)
        fam_str = m12_rec.get("procurement_family", {}).get("value", "unknown")
        fam_sub_str = m12_rec.get("procurement_family_sub", {}).get("value", "generic")

        p1c: AnnotationPassOutput | None = None
        if _is_done(AnnotationPipelineState.PASS_1C_DONE):
            p1c = self._reconstruct_pass_output(
                record, "pass_1c_conformity_and_handoffs"
            )
            if p1c is not None:
                logger.info(
                    "annotation_orchestrator_checkpoint_hit",
                    extra={"run_id": str(run_id), "pass": "1c"},
                )
            else:
                _reset_from(
                    "pass_1c_conformity_and_handoffs",
                    AnnotationPipelineState.PASS_1B_DONE,
                )
        if p1c is None:
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
            record.pass_outputs["pass_1c_conformity_and_handoffs"] = (
                serialize_pass_output(p1c)
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
            self.save_run(record)

        # ── Pass 1D: Process Linking ──
        p1d: AnnotationPassOutput | None = None
        if _is_done(AnnotationPipelineState.PASS_1D_DONE):
            p1d = self._reconstruct_pass_output(record, "pass_1d_process_linking")
            if p1d is not None:
                logger.info(
                    "annotation_orchestrator_checkpoint_hit",
                    extra={"run_id": str(run_id), "pass": "1d"},
                )
            else:
                _reset_from(
                    "pass_1d_process_linking",
                    AnnotationPipelineState.PASS_1C_DONE,
                )
        if p1d is None:
            p1d = self._run_pass_with_retry(
                run_pass_1d_process_linking,
                "pass_1d_process_linking",
                normalized_text=normalized_text,
                document_id=document_id,
                run_id=run_id,
                pass_1a_output_data=p1a.output_data or {},
                case_documents_1a=case_documents_1a,
            )
            record.pass_outputs["pass_1d_process_linking"] = serialize_pass_output(p1d)
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

        if not use_pass_2a():
            return record, AnnotationPipelineState.PASS_1D_DONE

        if not case_id:
            logger.warning(
                "annotation_orchestrator_pass_2a_skipped_no_case_id",
                extra={"run_id": str(run_id), "document_id": document_id},
            )
            now = datetime.now(UTC)
            skip_2a = AnnotationPassOutput(
                pass_name="pass_2a_regulatory_profile",
                pass_version="1.0.0",
                document_id=document_id,
                run_id=run_id,
                started_at=now,
                completed_at=now,
                status=PassRunStatus.SKIPPED,
                output_data={
                    "m13_skip_reason": ("case_id_required_when_annotation_use_pass_2a"),
                },
                errors=[],
                metadata={"duration_ms": 0},
            )
            record.pass_outputs["pass_2a_regulatory_profile"] = serialize_pass_output(
                skip_2a
            )
            self.save_run(record)
            return record, AnnotationPipelineState.PASS_1D_DONE

        p2a = self._run_pass_with_retry(
            run_pass_2a_regulatory_profile,
            "pass_2a_regulatory_profile",
            case_id=case_id,
            document_id=document_id,
            run_id=run_id,
            pass_1a_output_data=p1a.output_data or {},
            pass_1b_output_data=p1b.output_data or {},
            pass_1c_output_data=p1c.output_data or {},
            pass_1d_output_data=p1d.output_data or {},
        )
        record.pass_outputs["pass_2a_regulatory_profile"] = serialize_pass_output(p2a)
        if p2a.status == PassRunStatus.FAILED:
            self._log_transition(
                record,
                from_state=record.state,
                to_state=AnnotationPipelineState.DEAD_LETTER.value,
                pass_name="pass_2a_regulatory_profile",
                out=p2a,
            )
            record.state = AnnotationPipelineState.DEAD_LETTER.value
            self.save_run(record)
            return record, AnnotationPipelineState.DEAD_LETTER
        self._log_transition(
            record,
            from_state=record.state,
            to_state=AnnotationPipelineState.PASS_2A_DONE.value,
            pass_name="pass_2a_regulatory_profile",
            out=p2a,
        )
        record.state = AnnotationPipelineState.PASS_2A_DONE.value
        self.save_run(record)
        return record, AnnotationPipelineState.PASS_2A_DONE
