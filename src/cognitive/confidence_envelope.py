"""ConfidenceEnvelope — INV-C09 (SPEC BLOC5 B.3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class ConfidenceEnvelope:
    overall: float
    ocr_quality: float | None
    classification: float | None
    extraction: float | None
    assembly: float | None
    regulatory_match: float | None
    data_points: int
    computed_at: str
    model_version: str


def regime_from_overall(overall: float) -> str:
    if overall >= 0.8:
        return "green"
    if overall >= 0.5:
        return "yellow"
    return "red"


def requires_hitl(overall: float) -> bool:
    return regime_from_overall(overall) == "red"


def compute_bundle_confidence(doc_confidences: list[float]) -> float:
    """Confiance bundle = min(docs) ; [] => 0.0 (INV-C09)."""

    if not doc_confidences:
        return 0.0
    return float(min(doc_confidences))


def compute_frame_confidence(bundle_overalls: list[float]) -> float:
    """Moyenne simple des confiances bundle ; [] => 0.0."""

    if not bundle_overalls:
        return 0.0
    return float(sum(bundle_overalls) / len(bundle_overalls))


def build_envelope_from_overall(
    overall: float,
    *,
    model_version: str = "v1",
) -> ConfidenceEnvelope:
    now = datetime.now(UTC).isoformat()
    return ConfidenceEnvelope(
        overall=overall,
        ocr_quality=None,
        classification=None,
        extraction=None,
        assembly=None,
        regulatory_match=None,
        data_points=0,
        computed_at=now,
        model_version=model_version,
    )
