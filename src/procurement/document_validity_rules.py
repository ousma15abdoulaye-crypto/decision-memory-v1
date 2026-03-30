"""
M12 V6 L5 — Document Validity Judgment.

Computes validity status from mandatory parts detection results.
"""

from __future__ import annotations

from typing import Literal

from src.procurement.procedure_models import (
    DocumentValidity,
    PartDetectionResult,
    TracedField,
)


def compute_validity(
    detection_details: list[PartDetectionResult],
    optional_present: list[str],
    not_applicable: list[str],
    document_kind: str,
    quality_class: str = "good",
) -> DocumentValidity:
    """
    Compute document validity from part detection results.

    quality_class from Pass 0.5: good/degraded/poor/ocr_failed.
    """
    if quality_class == "ocr_failed" or document_kind == "unknown":
        return DocumentValidity(
            document_validity_status=TracedField(
                value="not_assessable",
                confidence=0.60,
                evidence=[f"quality_class={quality_class}", f"kind={document_kind}"],
            ),
            mandatory_detected_count=0,
            mandatory_total_count=len(detection_details),
            mandatory_coverage=0.0,
            mandatory_parts_present=[],
            mandatory_parts_missing=[d.part_name for d in detection_details],
            mandatory_parts_detection_details=detection_details,
            optional_parts_present=optional_present,
            not_applicable_parts=not_applicable,
        )

    total = len(detection_details)
    detected = [d for d in detection_details if d.detection_level != "not_detected"]
    detected_count = len(detected)
    coverage = detected_count / total if total > 0 else 0.0

    present_names = [d.part_name for d in detected]
    missing_names = [
        d.part_name for d in detection_details if d.detection_level == "not_detected"
    ]

    status: Literal["valid", "invalid", "partial", "not_assessable"]
    if total == 0:
        status = "not_assessable"
        confidence = 0.60
    elif detected_count == total:
        status = "valid"
        avg_conf = sum(d.confidence for d in detected) / detected_count
        confidence = min(0.95, avg_conf)
    elif detected_count > 0:
        status = "partial"
        avg_conf = sum(d.confidence for d in detected) / detected_count
        confidence = min(0.80, avg_conf * coverage)
    else:
        status = "invalid"
        confidence = 0.60

    if quality_class == "degraded":
        confidence = min(confidence, 0.60)
    if quality_class == "poor":
        confidence = min(confidence, 0.50)

    evidence = [f"coverage={coverage:.2f}", f"detected={detected_count}/{total}"]

    return DocumentValidity(
        document_validity_status=TracedField(
            value=status,
            confidence=confidence,
            evidence=evidence,
        ),
        mandatory_detected_count=detected_count,
        mandatory_total_count=total,
        mandatory_coverage=round(coverage, 4),
        mandatory_parts_present=present_names,
        mandatory_parts_missing=missing_names,
        mandatory_parts_detection_details=detection_details,
        optional_parts_present=optional_present,
        not_applicable_parts=not_applicable,
    )
