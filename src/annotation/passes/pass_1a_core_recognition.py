"""
Pass 1A — Core Recognition (L1 + L2 + L3).

Replaces / extends the old pass_1_router. Produces full ProcedureRecognition payload.
Backward-compatible: old output_data keys are also emitted for the orchestrator.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from src.annotation.pass_output import (
    AnnotationPassOutput,
    PassError,
    PassRunStatus,
)
from src.procurement.document_ontology import (
    DOCUMENT_KIND_TO_LAYER,
    DOCUMENT_KIND_TO_STAGE,
    DocumentKindParent,
    DocumentLayer,
    DocumentStage,
    ProcedureType,
    ProcurementFamily,
)
from src.procurement.document_type_recognizer import recognize_document_type
from src.procurement.family_detector import FamilyDetector
from src.procurement.framework_signal_bank import FrameworkSignalBank
from src.procurement.procedure_models import (
    ProcedureRecognition,
    TracedField,
    discretize_confidence,
)
from src.procurement.procedure_rules_dgmp_mali import determine_dgmp_procedure_tier

logger = logging.getLogger(__name__)

_PASS_NAME = "pass_1a_core_recognition"
_PASS_VERSION = "1.0.0"

_DEADLINE_PATTERN = re.compile(
    r"(?:date\s+limite|deadline|closing\s+date)[:\s]+([^\n]{5,40})",
    re.IGNORECASE,
)
_REFERENCE_PATTERN = re.compile(
    r"(?:r[eé]f[eé]rence|n[°o]|ref)\s*[:\.]?\s*([A-Z0-9][-A-Z0-9/_.]{3,})",
    re.IGNORECASE,
)
_PROJECT_PATTERN = re.compile(
    r"(?:projet|programme|project)[:\s]+([^\n]{3,80})",
    re.IGNORECASE,
)
_ENTITY_PATTERN = re.compile(
    r"(?:émis\s+par|issued\s+by|autorité\s+contractante)[:\s]+([^\n]{3,60})",
    re.IGNORECASE,
)
_VALUE_PATTERN = re.compile(
    r"(?:montant|valeur|budget|estimated)\s*[:\s]+\s*([\d\s.,]+)\s*(FCFA|XOF|USD|EUR)?",
    re.IGNORECASE,
)
_ZONE_PATTERN = re.compile(
    r"\b(Bamako|Mopti|Ségou|Sikasso|Koulikoro|Kayes|Gao|Tombouctou"
    r"|Kidal|Ménaka|Taoudénit|Niamey|Dakar)\b",
    re.IGNORECASE,
)
_CURRENCY_PATTERN = re.compile(r"\b(FCFA|XOF|USD|EUR|CFA)\b", re.IGNORECASE)

_fw_bank: FrameworkSignalBank | None = None
_fam_detector: FamilyDetector | None = None


def _get_fw_bank() -> FrameworkSignalBank:
    global _fw_bank
    if _fw_bank is None:
        _fw_bank = FrameworkSignalBank()
    return _fw_bank


def _get_fam_detector() -> FamilyDetector:
    global _fam_detector
    if _fam_detector is None:
        _fam_detector = FamilyDetector()
    return _fam_detector


def _dgmp_threshold_family_key(family: ProcurementFamily) -> str:
    """Aligné sur ``RegimeResolver`` : travaux → YAML ``works``, sinon ``goods``."""
    return "works" if family == ProcurementFamily.WORKS else "goods"


def _resolve_procedure_type(
    framework: object,
    estimated_value: float | None,
    currency: str | None,
    cap_fn,
    procurement_family: ProcurementFamily,
) -> TracedField:
    """Determine procedure_type via DGMP thresholds si applicable."""
    fw_s = str(framework).lower() if framework is not None else ""
    if fw_s and "dgmp" in fw_s:
        fk = _dgmp_threshold_family_key(procurement_family)
        dgmp = determine_dgmp_procedure_tier(estimated_value, currency, family_key=fk)
        if dgmp.procedure_tier != "unknown":
            return TracedField(
                value=dgmp.procedure_tier,
                confidence=cap_fn(dgmp.confidence),
                evidence=[
                    f"dgmp_tier={dgmp.procedure_tier}",
                    f"value={dgmp.estimated_value}",
                    dgmp.procedure_description,
                ],
            )
    return TracedField(
        value=ProcedureType.UNKNOWN,
        confidence=cap_fn(0.6),
        evidence=["needs_further_analysis"],
    )


def _extract_simple(pattern: re.Pattern[str], text: str) -> str | None:
    m = pattern.search(text[:5000])
    return m.group(1).strip() if m else None


def _extract_value(text: str) -> tuple[float | None, str | None]:
    m = _VALUE_PATTERN.search(text[:10000])
    if not m:
        return None, None
    raw_num = m.group(1).replace(" ", "").replace(",", ".")
    try:
        val = float(raw_num)
    except ValueError:
        return None, None
    currency = m.group(2) if m.group(2) else None
    if currency is None:
        cm = _CURRENCY_PATTERN.search(text[:5000])
        currency = cm.group(1).upper() if cm else None
    return val, currency


def run_pass_1a_core_recognition(
    *,
    normalized_text: str,
    document_id: str,
    run_id: uuid.UUID,
    quality_class: str = "good",
    block_llm: bool = False,
    filename: str | None = None,
) -> AnnotationPassOutput:
    """Execute Pass 1A: L1 framework + L2 family + L3 type recognition."""
    started = datetime.now(UTC)
    errors: list[PassError] = []

    try:
        # Quality gate: if poor quality and LLM blocked, cap everything
        if quality_class == "poor" and block_llm:
            return AnnotationPassOutput(
                pass_name=_PASS_NAME,
                pass_version=_PASS_VERSION,
                document_id=document_id,
                run_id=run_id,
                started_at=started,
                completed_at=datetime.now(UTC),
                status=PassRunStatus.DEGRADED,
                output_data={
                    "m12_recognition": {},
                    "document_role": "unknown",
                    "taxonomy_core": "unknown",
                    "routing_confidence": 0.6,
                    "routing_source": "deterministic_blocked",
                    "matched_rule": "quality_gate_block",
                    "deterministic": True,
                    "routing_evidence": [
                        f"quality={quality_class}",
                        "block_llm=true",
                    ],
                    "routing_failure_reason": "poor_quality_llm_blocked",
                },
                errors=[],
                metadata={
                    "duration_ms": 0,
                    "quality_class": quality_class,
                    "filename": filename,
                },
            )

        # L1 — Framework detection
        fw_decision = _get_fw_bank().detect_framework(normalized_text)

        # L2 — Family detection
        fam_decision = _get_fam_detector().detect_family(normalized_text)

        # L3 — Type recognition (deterministe)
        type_result = recognize_document_type(normalized_text)

        # LLM ARBITRATION — seulement si le deterministe doute et LLM non bloque
        # Principe : le deterministe propose, le LLM arbitre parmi les candidats.
        # Le LLM ne peut pas inventer un type hors taxonomie.
        recognition_source = "deterministic"
        if not block_llm and (
            type_result.confidence < 0.80
            or type_result.primary_kind == DocumentKindParent.UNKNOWN
        ):
            try:
                from src.procurement.llm_arbitrator import get_arbitrator

                arb = get_arbitrator()
                if arb.is_available():
                    candidates = list(
                        dict.fromkeys(
                            [type_result.primary_kind]
                            + (type_result.secondary_kinds or [])
                        )
                    )
                    llm_field = arb.disambiguate_document_type(
                        text=normalized_text[:3000],
                        candidates=candidates,
                        deterministic_confidence=type_result.confidence,
                    )
                    if (
                        llm_field.value is not None
                        and llm_field.confidence > type_result.confidence
                    ):
                        # Recuperer le DocumentKindParent correspondant
                        for c in candidates:
                            c_val = c.value if hasattr(c, "value") else str(c)
                            if c_val == llm_field.value:
                                from src.procurement.document_type_recognizer import (
                                    TypeRecognitionResult,
                                )

                                type_result = TypeRecognitionResult(
                                    primary_kind=c,
                                    primary_subtype=type_result.primary_subtype,
                                    secondary_kinds=type_result.secondary_kinds,
                                    is_composite=type_result.is_composite,
                                    composite_confidence=type_result.composite_confidence,
                                    confidence=llm_field.confidence,
                                    evidence=llm_field.evidence,
                                    matched_rule="llm_arbitration",
                                )
                                recognition_source = "hybrid_deterministic_llm"
                                logger.info(
                                    "[PASS_1A] LLM arbitration -> %s conf=%.2f",
                                    c_val,
                                    llm_field.confidence,
                                )
                                break
            except Exception as arb_exc:
                logger.warning(
                    "[PASS_1A] LLM arbitration echec (non bloquant) : %s", arb_exc
                )

        # Enrich from text
        deadline = _extract_simple(_DEADLINE_PATTERN, normalized_text)
        proc_ref = _extract_simple(_REFERENCE_PATTERN, normalized_text)
        project = _extract_simple(_PROJECT_PATTERN, normalized_text)
        entity = _extract_simple(_ENTITY_PATTERN, normalized_text)
        zones = list(
            {m.group(1) for m in _ZONE_PATTERN.finditer(normalized_text[:10000])}
        )
        est_val, currency = _extract_value(normalized_text)

        # Submission mode heuristics
        submission_modes: list[str] = []
        if re.search(r"pli\s+ferm[eé]|sealed", normalized_text, re.IGNORECASE):
            submission_modes.append("sealed_envelope")
        if re.search(r"email|courriel|e-mail", normalized_text, re.IGNORECASE):
            submission_modes.append("email")
        if re.search(r"en\s+ligne|online|plateforme", normalized_text, re.IGNORECASE):
            submission_modes.append("online_platform")

        # Visit / sample
        visit = "not_applicable"
        if re.search(
            r"visite\s+(?:de\s+)?(?:site|lieux)", normalized_text, re.IGNORECASE
        ):
            visit = (
                "yes"
                if re.search(r"obligatoire", normalized_text, re.IGNORECASE)
                else "unknown"
            )

        sample = "not_applicable"
        if re.search(r"[eé]chantillon|sample", normalized_text, re.IGNORECASE):
            sample = "yes"

        # Humanitarian context
        humanitarian = "unknown"
        if re.search(
            r"humanitaire|humanitarian|urgence|emergency",
            normalized_text,
            re.IGNORECASE,
        ):
            humanitarian = "yes"

        # Apply quality_class ceiling
        confidence_ceiling = 1.0
        if quality_class == "degraded":
            confidence_ceiling = 0.60
        elif quality_class == "poor":
            confidence_ceiling = 0.60

        def _cap(c: float) -> float:
            return min(c, confidence_ceiling)

        # Determine review status
        review: Literal["resolved", "review_required", "unresolved"] = "resolved"
        if type_result.primary_kind == DocumentKindParent.UNKNOWN:
            review = "unresolved"
        elif quality_class in ("degraded", "poor"):
            review = "review_required"
        elif type_result.confidence < 0.70:
            review = "review_required"

        # Derive layer and stage from type
        layer = DOCUMENT_KIND_TO_LAYER.get(
            type_result.primary_kind, DocumentLayer.UNKNOWN
        )
        stage = DOCUMENT_KIND_TO_STAGE.get(
            type_result.primary_kind, DocumentStage.UNKNOWN
        )

        recognition = ProcedureRecognition(
            framework_detected=TracedField(
                value=fw_decision.framework,
                confidence=_cap(fw_decision.confidence),
                evidence=fw_decision.evidence,
            ),
            procurement_family=TracedField(
                value=fam_decision.family,
                confidence=_cap(fam_decision.confidence),
                evidence=fam_decision.evidence,
            ),
            procurement_family_sub=TracedField(
                value=fam_decision.family_sub,
                confidence=_cap(fam_decision.confidence),
                evidence=[f"sub={fam_decision.family_sub.value}"],
            ),
            document_kind=TracedField(
                value=type_result.primary_kind,
                confidence=_cap(type_result.confidence),
                evidence=type_result.evidence,
            ),
            document_subtype=TracedField(
                value=type_result.primary_subtype,
                confidence=_cap(type_result.confidence),
                evidence=[f"rule={type_result.matched_rule}"],
            ),
            secondary_document_kinds=type_result.secondary_kinds,
            is_composite=TracedField(
                value=type_result.is_composite,
                confidence=_cap(type_result.composite_confidence),
                evidence=[f"composite={type_result.is_composite}"],
            ),
            document_layer=TracedField(
                value=layer,
                confidence=_cap(0.85),
                evidence=[f"derived_from={type_result.primary_kind.value}"],
            ),
            document_stage=TracedField(
                value=stage,
                confidence=_cap(0.85),
                evidence=[f"derived_from={type_result.primary_kind.value}"],
            ),
            procedure_type=_resolve_procedure_type(
                fw_decision.framework,
                est_val,
                currency,
                _cap,
                fam_decision.family,
            ),
            procedure_reference_detected=TracedField(
                value=proc_ref,
                confidence=_cap(0.80) if proc_ref else _cap(0.6),
                evidence=[f"ref={proc_ref}"] if proc_ref else ["not_found"],
            ),
            issuing_entity_detected=TracedField(
                value=entity,
                confidence=_cap(0.70) if entity else _cap(0.6),
                evidence=[f"entity={entity}"] if entity else ["not_found"],
            ),
            project_name_detected=TracedField(
                value=project,
                confidence=_cap(0.70) if project else _cap(0.6),
                evidence=[f"project={project}"] if project else ["not_found"],
            ),
            zone_scope_detected=TracedField(
                value=zones,
                confidence=_cap(0.75) if zones else _cap(0.6),
                evidence=[f"zones={zones}"] if zones else ["not_found"],
            ),
            submission_deadline_detected=TracedField(
                value=deadline,
                confidence=_cap(0.75) if deadline else _cap(0.6),
                evidence=[f"deadline={deadline}"] if deadline else ["not_found"],
            ),
            submission_mode_detected=TracedField(
                value=submission_modes,
                confidence=_cap(0.70) if submission_modes else _cap(0.6),
                evidence=submission_modes or ["not_found"],
            ),
            result_type_detected=TracedField(
                value="unknown",
                confidence=_cap(0.6),
                evidence=["needs_further_analysis"],
            ),
            estimated_value_detected=TracedField(
                value=est_val,
                confidence=_cap(0.70) if est_val else _cap(0.6),
                evidence=[f"value={est_val}"] if est_val else ["not_found"],
            ),
            currency_detected=TracedField(
                value=currency,
                confidence=_cap(0.80) if currency else _cap(0.6),
                evidence=[f"currency={currency}"] if currency else ["not_found"],
            ),
            visit_required=TracedField(
                value=visit,
                confidence=_cap(0.70),
                evidence=[f"visit={visit}"],
            ),
            sample_required=TracedField(
                value=sample,
                confidence=_cap(0.70),
                evidence=[f"sample={sample}"],
            ),
            humanitarian_context=TracedField(
                value=humanitarian,
                confidence=_cap(0.70),
                evidence=[f"humanitarian={humanitarian}"],
            ),
            recognition_source=TracedField(
                value=recognition_source,
                confidence=1.0,
                evidence=[f"pass_1a_{recognition_source}"],
            ),
            review_status=TracedField(
                value=review,
                confidence=_cap(0.80),
                evidence=[
                    f"quality={quality_class}",
                    f"type_conf={type_result.confidence:.2f}",
                ],
            ),
        )

        # Backward-compatible output_data
        output_data: dict[str, Any] = {
            "m12_recognition": recognition.model_dump(mode="json"),
            "document_role": type_result.primary_kind.value,
            "taxonomy_core": type_result.primary_kind.value,
            "routing_confidence": discretize_confidence(_cap(type_result.confidence)),
            "routing_source": recognition_source,
            "matched_rule": type_result.matched_rule,
            "deterministic": recognition_source == "deterministic",
            "routing_evidence": type_result.evidence,
            "routing_failure_reason": (
                None if review != "unresolved" else "no_rule_matched"
            ),
        }

        status = PassRunStatus.SUCCESS
        if review == "review_required":
            status = PassRunStatus.DEGRADED
        elif review == "unresolved":
            status = PassRunStatus.DEGRADED

    except Exception as exc:
        logger.exception("pass_1a_error")
        errors.append(PassError(code="PASS_1A_ERROR", message=str(exc)[:500]))
        status = PassRunStatus.FAILED
        output_data = {}

    completed = datetime.now(UTC)
    return AnnotationPassOutput(
        pass_name=_PASS_NAME,
        pass_version=_PASS_VERSION,
        document_id=document_id,
        run_id=run_id,
        started_at=started,
        completed_at=completed,
        status=status,
        output_data=output_data,
        errors=errors,
        metadata={
            "duration_ms": int((completed - started).total_seconds() * 1000),
            "quality_class": quality_class,
            "filename": filename,
        },
    )
