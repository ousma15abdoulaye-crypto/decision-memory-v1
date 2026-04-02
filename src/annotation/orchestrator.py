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
from datetime import UTC, datetime
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
from src.annotation.passes.pass_2a_regulatory_profile import (
    run_pass_2a_regulatory_profile,
)

logger = logging.getLogger(__name__)

ENV_USE_ORCHESTRATOR = "ANNOTATION_USE_PASS_ORCHESTRATOR"
ENV_USE_M12_SUBPASSES = "ANNOTATION_USE_M12_SUBPASSES"
ENV_USE_PASS_2A = "ANNOTATION_USE_PASS_2A"

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


def use_pass_2a() -> bool:
    """Feature flag: after Pass 1D, run M13 Pass 2A (regulatory profile)."""
    return os.environ.get(ENV_USE_PASS_2A, "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _m12_run_terminal(state: AnnotationPipelineState) -> bool:
    """Terminal pour une exécution M12 (1A–1D–[2A])."""
    if state == AnnotationPipelineState.PASS_2A_DONE:
        return True
    if state == AnnotationPipelineState.PASS_1D_DONE:
        return not use_pass_2a()
    return state in _TERMINAL_STATES


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
    PASS_2A_DONE = "pass_2a_done"
    LLM_PREANNOTATION_PENDING = "llm_preannotation_pending"
    LLM_PREANNOTATION_DONE = "llm_preannotation_done"
    VALIDATED = "validated"
    REVIEW_REQUIRED = "review_required"
    ANNOTATED_VALIDATED = "annotated_validated"
    REJECTED = "rejected"
    DEAD_LETTER = "dead_letter"


# States from which the pipeline cannot be resumed — idempotent skip is safe.
_TERMINAL_STATES: frozenset[AnnotationPipelineState] = frozenset(
    {
        AnnotationPipelineState.PASS_1D_DONE,
        AnnotationPipelineState.PASS_2A_DONE,
        AnnotationPipelineState.DEAD_LETTER,
        AnnotationPipelineState.REVIEW_REQUIRED,
        AnnotationPipelineState.REJECTED,
        AnnotationPipelineState.ROUTED,
        AnnotationPipelineState.LLM_PREANNOTATION_PENDING,
        AnnotationPipelineState.LLM_PREANNOTATION_DONE,
        AnnotationPipelineState.VALIDATED,
        AnnotationPipelineState.ANNOTATED_VALIDATED,
    }
)

# States that represent a partial M12 run that can be safely resumed.
_M12_RESUMABLE_STATES: frozenset[AnnotationPipelineState] = frozenset(
    {
        AnnotationPipelineState.QUALITY_ASSESSED,
        AnnotationPipelineState.PASS_1A_DONE,
        AnnotationPipelineState.PASS_1B_DONE,
        AnnotationPipelineState.PASS_1C_DONE,
    }
)

# Ordered M12 progression for checkpoint comparisons.
_M12_STATE_ORDER: list[AnnotationPipelineState] = [
    AnnotationPipelineState.QUALITY_ASSESSED,
    AnnotationPipelineState.PASS_1A_DONE,
    AnnotationPipelineState.PASS_1B_DONE,
    AnnotationPipelineState.PASS_1C_DONE,
    AnnotationPipelineState.PASS_1D_DONE,
    AnnotationPipelineState.PASS_2A_DONE,
]


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
        tmp = p.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(asdict(record), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, p)  # atomic on POSIX and Windows NTFS

    def _reconstruct_pass_output(
        self, record: PipelineRunRecord, pass_key: str
    ) -> AnnotationPassOutput | None:
        """Deserialize a stored pass output dict back to an AnnotationPassOutput.

        Returns None if the key is missing or the stored data is corrupt.
        """
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
    ) -> tuple[PipelineRunRecord, AnnotationPipelineState]:
        """
        Exécute jusqu'à ``routed`` (ou ``dead_letter`` / ``review_required``).

        If a persisted record already exists for *run_id*, execution is skipped
        and the existing record is returned unchanged.
        """
        existing = self.load_run(run_id)
        if existing is not None:
            existing_state = AnnotationPipelineState(existing.state)
            if existing_state in _TERMINAL_STATES:
                logger.info(
                    "annotation_orchestrator_idempotent_skip",
                    extra={"run_id": str(run_id), "state": existing.state},
                )
                return existing, existing_state
            if use_m12_subpasses() and existing_state in _M12_RESUMABLE_STATES:
                # Non-terminal M12 run — recover from last checkpoint.
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
            # Run is in an M12 resumable state but use_m12_subpasses() is OFF.
            # Silently skipping would leave the run permanently stuck.
            # Fail loudly so the operator can investigate.
            if existing_state in _M12_RESUMABLE_STATES:
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
            # Unknown non-terminal state — skip with warning.
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
                case_documents_1a=case_documents_1a,
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
        case_id: str | None = None,
    ) -> tuple[PipelineRunRecord, AnnotationPipelineState]:
        """
        Execute M12 sub-passes (1A -> 1B -> 1C -> 1D) after Pass 0.5 is done.

        Expects a pre-existing PipelineRunRecord at state >= QUALITY_ASSESSED.
        Supports checkpoint recovery: passes already completed in a previous
        (crashed) run are skipped and their outputs are restored from JSON.
        Each pass saves a checkpoint immediately upon successful completion.
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

        # Short-circuit if already terminal (e.g. called twice on a finished run).
        if _m12_run_terminal(current_state):
            return record, current_state

        def _state_rank(s: AnnotationPipelineState) -> int:
            try:
                return _M12_STATE_ORDER.index(s)
            except ValueError:
                return -1

        def _is_done(target: AnnotationPipelineState) -> bool:
            return _state_rank(current_state) >= _state_rank(target)

        # Helper: reset state + downstream outputs when a checkpoint is corrupt.
        # Ensures no pass uses a freshly-rerun upstream with stale downstream data.
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
            record.pass_outputs["pass_1a_core_recognition"] = _serialize_pass_output(
                p1a
            )
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
            self.save_run(record)  # checkpoint

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
            record.pass_outputs["pass_1b_document_validity"] = _serialize_pass_output(
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
            self.save_run(record)  # checkpoint

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
                _serialize_pass_output(p1c)
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
            self.save_run(record)  # checkpoint

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
            self.save_run(record)  # checkpoint

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
            record.pass_outputs["pass_2a_regulatory_profile"] = _serialize_pass_output(
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
        record.pass_outputs["pass_2a_regulatory_profile"] = _serialize_pass_output(p2a)
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
