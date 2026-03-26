"""
Pass 0.5 — Quality gate (OCR / text usability).

Contrat : docs/contracts/annotation/PASS_0_5_QUALITY_GATE_CONTRACT.md
Formule indicateur (dms-pipeline) : ratio_alphanum×0.4 + densité_lignes×0.3 + mots_clés×0.3
Classes finales alignées sur PASS_0_5_EMPIRICAL_THRESHOLDS.md (char_count + ratios).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Literal

from src.annotation.pass_output import (
    AnnotationPassOutput,
    PassError,
    PassRunStatus,
)

logger = logging.getLogger(__name__)

PASS_NAME = "pass_0_5_quality_gate"
PASS_VERSION = "1.0.0"

QualityClass = Literal["good", "degraded", "poor", "ocr_failed"]

_KEYWORDS = (
    "dao",
    "rfq",
    "tdr",
    "nif",
    "rccm",
    "rib",
    "xof",
    "fcfa",
    "offre",
    "fournisseur",
    "montant",
    "délai",
    "delai",
    "lot",
    "bordereau",
)


def _keyword_score(text: str) -> float:
    low = text.lower()
    hits = sum(1 for k in _KEYWORDS if k in low)
    return min(1.0, hits / 5.0)


def _ocr_composite_score(char_count: int, line_count: int, text: str) -> float:
    """Score 0–1 informatif (pipeline DMS) — ne remplace pas les seuils empiriques."""
    if not text:
        return 0.0
    ratio_alphanum = sum(c.isalnum() for c in text) / max(len(text), 1)
    # Densité : lignes par unité de texte (cible ~1 ligne / 40–80 caractères pour du texte propre)
    denom = max(char_count / 60.0, 1.0)
    densite_lignes = min(1.0, line_count / denom)
    kw = _keyword_score(text)
    return ratio_alphanum * 0.4 + densite_lignes * 0.3 + kw * 0.3


def _replacement_hits(text: str) -> int:
    return text.count("\ufffd")


def _worst_quality(a: QualityClass, b: QualityClass) -> QualityClass:
    """Plus mauvais = plus bas dans l’ordre de gravité."""
    order = {"ocr_failed": 0, "poor": 1, "degraded": 2, "good": 3}
    return a if order[a] <= order[b] else b


def classify_quality(
    normalized_text: str,
    *,
    strict_block_llm_on_poor: bool = True,
) -> tuple[QualityClass, dict[str, Any], bool, list[str]]:
    """
    Retourne (quality_class, metrics, block_llm, operator_hints).
    """
    text = normalized_text or ""
    char_count = len(text)
    word_count = len(text.split())
    alnum = sum(1 for c in text if c.isalnum())
    non_alnum_ratio = 1.0 - (alnum / char_count) if char_count else 0.0
    replacement_char_hits = _replacement_hits(text)
    line_count = len(text.split("\n")) if text else 0
    ocr_quality_score = _ocr_composite_score(char_count, line_count, text)

    metrics: dict[str, Any] = {
        "char_count": char_count,
        "word_count": word_count,
        "non_alnum_ratio": round(non_alnum_ratio, 6),
        "replacement_char_hits": replacement_char_hits,
        "line_count": line_count,
        "ocr_quality_score": round(ocr_quality_score, 6),
    }

    hints: list[str] = []

    if replacement_char_hits > 50 or char_count < 100:
        quality: QualityClass = "ocr_failed"
        hints.extend(["rescan", "alt_source"])
    elif char_count < 200:
        quality = "poor"
    elif char_count < 1000:
        quality = "degraded"
    else:
        quality = "good"

    if quality != "ocr_failed":
        if non_alnum_ratio > 0.45:
            quality = _worst_quality(quality, "poor")
            hints.append("high_noise_ratio")
        elif 0.25 <= non_alnum_ratio <= 0.45:
            quality = _worst_quality(quality, "degraded")
        if replacement_char_hits >= 20:
            quality = _worst_quality(quality, "poor")
            hints.append("replacement_chars")
        elif 5 <= replacement_char_hits <= 19:
            quality = _worst_quality(quality, "degraded")
            hints.append("replacement_chars")

    block_llm = quality == "ocr_failed" or (
        quality == "poor" and strict_block_llm_on_poor
    )
    return quality, metrics, block_llm, hints


def run_pass_0_5_quality_gate(
    normalized_text: str,
    *,
    document_id: str,
    run_id: uuid.UUID,
    strict_block_llm_on_poor: bool = True,
) -> AnnotationPassOutput:
    started = AnnotationPassOutput.utc_now()
    if not (normalized_text or "").strip():
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
                    code="EMPTY_NORMALIZED_TEXT",
                    message="Pass 0.5 requires non-empty normalized_text",
                )
            ],
            metadata={
                "duration_ms": int((completed - started).total_seconds() * 1000),
            },
        )

    qc, metrics, block_llm, hints = classify_quality(
        normalized_text,
        strict_block_llm_on_poor=strict_block_llm_on_poor,
    )
    completed = AnnotationPassOutput.utc_now()
    duration_ms = int((completed - started).total_seconds() * 1000)

    logger.info(
        "pass_0_5_quality_gate_done",
        extra={
            "document_id": document_id,
            "run_id": str(run_id),
            "quality_class": qc,
            "block_llm": block_llm,
            "char_count": metrics["char_count"],
            "duration_ms": duration_ms,
        },
    )

    # Contrat : « success » dès que la classification est posée (§ status Pass 0.5).
    pass_status = PassRunStatus.SUCCESS

    return AnnotationPassOutput(
        pass_name=PASS_NAME,
        pass_version=PASS_VERSION,
        document_id=document_id,
        run_id=run_id,
        started_at=started,
        completed_at=completed,
        status=pass_status,
        output_data={
            "quality_class": qc,
            "metrics": metrics,
            "block_llm": block_llm,
            "operator_hints": hints,
        },
        errors=[],
        metadata={"duration_ms": duration_ms},
    )
