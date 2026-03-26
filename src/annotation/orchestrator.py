"""
Orchestrateur FSM — pipeline d’annotation multipasses.

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

from src.annotation.pass_output import AnnotationPassOutput, PassRunStatus
from src.annotation.passes.pass_0_5_quality_gate import run_pass_0_5_quality_gate
from src.annotation.passes.pass_0_ingestion import run_pass_0_ingestion
from src.annotation.passes.pass_1_router import run_pass_1_router

logger = logging.getLogger(__name__)

ENV_USE_ORCHESTRATOR = "ANNOTATION_USE_PASS_ORCHESTRATOR"


def use_pass_orchestrator() -> bool:
    return os.environ.get(ENV_USE_ORCHESTRATOR, "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


class AnnotationPipelineState(StrEnum):
    INGESTED = "ingested"
    PASS_0_DONE = "pass_0_done"
    QUALITY_ASSESSED = "quality_assessed"
    ROUTED = "routed"
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
    """

    def __init__(
        self,
        *,
        runs_dir: Path | None = None,
        strict_block_llm_on_poor: bool = True,
        llm_router: Callable[[str], dict[str, Any]] | None = None,
    ) -> None:
        self.runs_dir = runs_dir or default_pipeline_runs_dir()
        self.strict_block_llm_on_poor = strict_block_llm_on_poor
        self.llm_router = llm_router

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
                "run_id": getattr(entry, "run_id", None),
                "document_id": entry.document_id,
                "from_state": entry.from_state,
                "to_state": entry.to_state,
                "pass_name": entry.pass_name,
                "duration_ms": entry.duration_ms,
                "status": entry.status,
                "error_codes": entry.error_codes,
            },
        )

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
        Exécute jusqu’à ``routed`` (ou ``dead_letter`` / ``review_required`` selon garde-fous).
        """
        record = PipelineRunRecord(
            run_id=str(run_id),
            document_id=document_id,
            state=AnnotationPipelineState.INGESTED.value,
        )

        # Pass 0
        p0 = run_pass_0_ingestion(
            raw_text,
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

        # Pass 0.5
        p05 = run_pass_0_5_quality_gate(
            normalized,
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

        # Pass 1 (deterministe / LLM optionnel)
        p1 = run_pass_1_router(
            normalized,
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
            # Placeholder LLM pending — l’adapter LS branche l’appel réel.
            record.state = AnnotationPipelineState.LLM_PREANNOTATION_PENDING.value

        self.save_run(record)
        return record, AnnotationPipelineState(record.state)
