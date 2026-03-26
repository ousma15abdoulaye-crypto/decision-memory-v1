"""
Pass 1 — Router / Procedure Recognizer (absorbe document_classifier).

Contrat : docs/contracts/annotation/PASS_1_ROUTER_CONTRACT.md
"""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Callable
from typing import Any

from src.annotation.document_classifier import (
    ClassificationResult,
    DocumentRole,
    TaxonomyCore,
    classify_document,
)
from src.annotation.pass_output import (
    AnnotationPassOutput,
    PassError,
    PassRunStatus,
)

logger = logging.getLogger(__name__)

PASS_NAME = "pass_1_router"
PASS_VERSION = "1.0.0"

# Confiance contractuelle (REGLE) : {0.6, 0.8, 1.0}
_ALLOWED_CONF = frozenset({0.6, 0.8, 1.0})

_FILENAME_RULES: list[tuple[re.Pattern[str], TaxonomyCore, DocumentRole, str]] = [
    (
        re.compile(r"dao|appel[_\s-]*offres?|dossier[_\s-]*appel", re.IGNORECASE),
        TaxonomyCore.DAO,
        DocumentRole.SOURCE_RULES,
        "filename_signal_dao",
    ),
    (
        re.compile(
            r"rfq|demande[_\s-]*cotation|request[_\s-]*for[_\s-]*quotation",
            re.IGNORECASE,
        ),
        TaxonomyCore.RFQ,
        DocumentRole.SOURCE_RULES,
        "filename_signal_rfq",
    ),
    (
        re.compile(r"tdr|termes[_\s-]*de[_\s-]*reference", re.IGNORECASE),
        TaxonomyCore.TDR_CONSULTANCE_AUDIT,
        DocumentRole.SOURCE_RULES,
        "filename_signal_tdr",
    ),
    (
        re.compile(r"offre[_\s-]*financ|proposition[_\s-]*financ", re.IGNORECASE),
        TaxonomyCore.OFFER_FINANCIAL,
        DocumentRole.FINANCIAL_OFFER,
        "filename_signal_financial",
    ),
    (
        re.compile(r"offre[_\s-]*tech|proposition[_\s-]*tech", re.IGNORECASE),
        TaxonomyCore.OFFER_TECHNICAL,
        DocumentRole.OFFER_TECHNICAL,
        "filename_signal_technical",
    ),
]


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _parse_llm_enums(proposal: dict) -> tuple[str | None, str | None, str | None]:
    """
    Retourne (document_role, taxonomy_core, erreur) — ``erreur`` si hors enums fermées.
    """
    raw_dr = proposal.get("document_role")
    raw_tc = proposal.get("taxonomy_core")
    dr_s = None if raw_dr is None else str(raw_dr).strip()
    tc_s = None if raw_tc is None else str(raw_tc).strip()
    valid_roles = {e.value for e in DocumentRole}
    valid_tax = {e.value for e in TaxonomyCore}
    if dr_s not in valid_roles or tc_s not in valid_tax:
        return (
            None,
            None,
            f"document_role and taxonomy_core must be enum values; got {dr_s!r}, {tc_s!r}",
        )
    return dr_s, tc_s, None


def _map_confidence(raw: float) -> float:
    if raw >= 0.99:
        return 1.0
    if raw >= 0.75:
        return 0.8
    return 0.6


def _classify_from_filename(filename: str | None) -> ClassificationResult | None:
    if not filename or not filename.strip():
        return None
    base = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    for rx, tax, role, rule in _FILENAME_RULES:
        if rx.search(base):
            return ClassificationResult(
                taxonomy_core=tax,
                document_role=role,
                confidence=0.8,
                matched_rule=rule,
                deterministic=True,
            )
    return None


def _routing_evidence(
    result: ClassificationResult,
    *,
    filename: str | None,
) -> list[str]:
    ev = [result.matched_rule]
    if filename:
        ev.append(f"filename={filename.rsplit('/', 1)[-1].rsplit(chr(92), 1)[-1]}")
    return ev


def run_pass_1_router(
    normalized_text: str,
    *,
    document_id: str,
    run_id: uuid.UUID,
    block_llm: bool,
    filename: str | None = None,
    llm_router: Callable[[str], dict[str, Any]] | None = None,
) -> AnnotationPassOutput:
    """
    Si le classifieur texte est indéterministe et ``block_llm`` est faux,
    appelle ``llm_router`` (injectable, tests) pour une proposition LLM.
    """
    started = AnnotationPassOutput.utc_now()
    text = normalized_text or ""

    if not text.strip():
        completed = AnnotationPassOutput.utc_now()
        return AnnotationPassOutput(
            pass_name=PASS_NAME,
            pass_version=PASS_VERSION,
            document_id=document_id,
            run_id=run_id,
            started_at=started,
            completed_at=completed,
            status=PassRunStatus.FAILED,
            output_data={},
            errors=[
                PassError(
                    code="EMPTY_TEXT",
                    message="Pass 1 requires non-empty normalized text",
                )
            ],
            metadata={"duration_ms": int((completed - started).total_seconds() * 1000)},
        )

    result: ClassificationResult | None = _classify_from_filename(filename)
    if result is None:
        result = classify_document(text)

    routing_confidence = _map_confidence(result.confidence)
    if routing_confidence not in _ALLOWED_CONF:
        routing_confidence = 0.6

    routing_source: str
    output_data: dict[str, Any]
    model_used: str | None = None

    if result.deterministic:
        routing_source = "deterministic_classifier"
        pass_status = PassRunStatus.SUCCESS
        output_data = {
            "document_role": result.document_role.value,
            "taxonomy_core": result.taxonomy_core.value,
            "routing_confidence": routing_confidence,
            "routing_source": routing_source,
            "matched_rule": result.matched_rule,
            "deterministic": True,
            "routing_evidence": _routing_evidence(result, filename=filename),
            "routing_failure_reason": None,
        }
    elif block_llm:
        routing_source = "human"
        pass_status = PassRunStatus.DEGRADED
        output_data = {
            "document_role": DocumentRole.UNKNOWN.value,
            "taxonomy_core": TaxonomyCore.UNKNOWN.value,
            "routing_confidence": 0.6,
            "routing_source": routing_source,
            "matched_rule": result.matched_rule,
            "deterministic": False,
            "routing_evidence": _routing_evidence(result, filename=filename)
            + ["block_llm_true_no_llm"],
            "routing_failure_reason": "block_llm=true, deterministic=false, requires human review",
        }
    elif llm_router is not None:
        try:
            proposal = llm_router(text)
        except Exception as e:
            completed = AnnotationPassOutput.utc_now()
            return AnnotationPassOutput(
                pass_name=PASS_NAME,
                pass_version=PASS_VERSION,
                document_id=document_id,
                run_id=run_id,
                started_at=started,
                completed_at=completed,
                status=PassRunStatus.FAILED,
                output_data={},
                errors=[
                    PassError(
                        code="LLM_ROUTER_ERROR",
                        message=str(e)[:500],
                        detail={"type": type(e).__name__},
                    )
                ],
                metadata={
                    "duration_ms": int((completed - started).total_seconds() * 1000)
                },
            )
        if not isinstance(proposal, dict):
            completed = AnnotationPassOutput.utc_now()
            return AnnotationPassOutput(
                pass_name=PASS_NAME,
                pass_version=PASS_VERSION,
                document_id=document_id,
                run_id=run_id,
                started_at=started,
                completed_at=completed,
                status=PassRunStatus.DEGRADED,
                output_data={
                    "document_role": DocumentRole.UNKNOWN.value,
                    "taxonomy_core": TaxonomyCore.UNKNOWN.value,
                    "routing_confidence": 0.6,
                    "routing_source": "llm_proposal_unresolved",
                    "matched_rule": result.matched_rule,
                    "deterministic": False,
                    "routing_evidence": _routing_evidence(result, filename=filename)
                    + ["llm_proposal_invalid_type"],
                    "routing_failure_reason": "llm_router returned non-dict",
                },
                errors=[
                    PassError(
                        code="LLM_PROPOSAL_INVALID",
                        message="llm_router must return a dict",
                    )
                ],
                metadata={
                    "duration_ms": int((completed - started).total_seconds() * 1000)
                },
            )
        dr_parsed, tc_parsed, enum_err = _parse_llm_enums(proposal)
        if enum_err is not None:
            completed = AnnotationPassOutput.utc_now()
            return AnnotationPassOutput(
                pass_name=PASS_NAME,
                pass_version=PASS_VERSION,
                document_id=document_id,
                run_id=run_id,
                started_at=started,
                completed_at=completed,
                status=PassRunStatus.DEGRADED,
                output_data={
                    "document_role": DocumentRole.UNKNOWN.value,
                    "taxonomy_core": TaxonomyCore.UNKNOWN.value,
                    "routing_confidence": 0.6,
                    "routing_source": "llm_proposal_unresolved",
                    "matched_rule": result.matched_rule,
                    "deterministic": False,
                    "routing_evidence": _routing_evidence(result, filename=filename)
                    + ["llm_proposal_enum_mismatch"],
                    "routing_failure_reason": enum_err[:500],
                },
                errors=[
                    PassError(
                        code="LLM_PROPOSAL_INVALID",
                        message=enum_err[:500],
                    )
                ],
                metadata={
                    "duration_ms": int((completed - started).total_seconds() * 1000)
                },
            )
        dr = dr_parsed
        tc = tc_parsed
        validated = bool(proposal.get("validated", False))
        routing_source = (
            "llm_proposal_validated" if validated else "llm_proposal_unresolved"
        )
        routing_confidence = _map_confidence(
            _safe_float(proposal.get("confidence"), 0.0)
        )
        model_used = proposal.get("model_used")
        if isinstance(model_used, str):
            model_used = model_used[:256]
        else:
            model_used = None
        pass_status = PassRunStatus.SUCCESS if validated else PassRunStatus.DEGRADED
        failure_reason = None if validated else "llm_proposal_not_validated"
        output_data = {
            "document_role": dr,
            "taxonomy_core": tc,
            "routing_confidence": routing_confidence,
            "routing_source": routing_source,
            "matched_rule": result.matched_rule,
            "deterministic": False,
            "routing_evidence": _routing_evidence(result, filename=filename)
            + ["llm_proposal"],
            "routing_failure_reason": failure_reason,
        }
    else:
        routing_source = "llm_proposal_unresolved"
        pass_status = PassRunStatus.DEGRADED
        output_data = {
            "document_role": DocumentRole.UNKNOWN.value,
            "taxonomy_core": TaxonomyCore.UNKNOWN.value,
            "routing_confidence": 0.6,
            "routing_source": routing_source,
            "matched_rule": result.matched_rule,
            "deterministic": False,
            "routing_evidence": _routing_evidence(result, filename=filename)
            + ["no_llm_router_configured"],
            "routing_failure_reason": "no_llm_router_configured, deterministic=false",
        }

    completed = AnnotationPassOutput.utc_now()
    duration_ms = int((completed - started).total_seconds() * 1000)
    meta: dict[str, Any] = {"duration_ms": duration_ms}
    if model_used:
        meta["model_used"] = model_used

    logger.info(
        "pass_1_router_done",
        extra={
            "document_id": document_id,
            "run_id": str(run_id),
            "document_role": output_data.get("document_role"),
            "taxonomy_core": output_data.get("taxonomy_core"),
            "routing_source": output_data.get("routing_source"),
            "routing_confidence": output_data.get("routing_confidence"),
            "deterministic": output_data.get("deterministic"),
            "status": pass_status.value,
            "duration_ms": duration_ms,
        },
    )

    return AnnotationPassOutput(
        pass_name=PASS_NAME,
        pass_version=PASS_VERSION,
        document_id=document_id,
        run_id=run_id,
        started_at=started,
        completed_at=completed,
        status=pass_status,
        output_data=output_data,
        errors=[],
        metadata=meta,
    )
