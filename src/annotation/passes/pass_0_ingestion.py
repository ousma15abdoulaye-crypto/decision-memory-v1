"""
Pass 0 — Ingestion (normalisation, page_map, features).

Contrat : docs/contracts/annotation/PASS_0_INGESTION_CONTRACT.md
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from typing import Any

from src.annotation.pass_output import (
    AnnotationPassOutput,
    PassError,
    PassRunStatus,
)

PASS_NAME = "pass_0_ingestion"
PASS_VERSION = "1.0.0"

# Page break: form feed between pages (common PDF text extraction)
_PAGE_BREAK = "\f"


def _normalize_text(raw: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    if not raw:
        return "", notes
    # NFKC — pas d’invention de contenu
    t = unicodedata.normalize("NFKC", raw)
    # Normaliser fins de ligne
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse espaces / lignes vides excessives (hors \f)
    parts = t.split(_PAGE_BREAK)
    norm_parts: list[str] = []
    for i, p in enumerate(parts):
        p2 = re.sub(r"[ \t]+", " ", p)
        p2 = re.sub(r"\n{3,}", "\n\n", p2)
        p2 = p2.strip()
        if p2:
            norm_parts.append(p2)
        elif i < len(parts) - 1:
            notes.append("empty_page_segment_after_form_feed")
    if _PAGE_BREAK in raw and not notes:
        notes.append("page_breaks_normalized")
    normalized = (
        _PAGE_BREAK.join(norm_parts)
        if len(norm_parts) > 1
        else (norm_parts[0] if norm_parts else "")
    )
    return normalized, notes


def _build_page_map(normalized: str) -> list[dict[str, int]]:
    if not normalized:
        return []
    if _PAGE_BREAK not in normalized:
        return [{"page_index": 0, "char_start": 0, "char_end": len(normalized)}]
    segments = normalized.split(_PAGE_BREAK)
    page_map: list[dict[str, int]] = []
    pos = 0
    for i, seg in enumerate(segments):
        start = pos
        end = pos + len(seg)
        page_map.append({"page_index": i, "char_start": start, "char_end": end})
        if i < len(segments) - 1:
            pos = end + 1  # saut du \f
    return page_map


def _features(text: str, extraction_method_hint: str) -> dict[str, Any]:
    n = len(text)
    lines = text.split("\n") if text else []
    line_count = len(lines)
    alnum = sum(1 for c in text if c.isalnum())
    non_alnum_ratio = 1.0 - (alnum / n) if n else 0.0
    return {
        "char_count": n,
        "line_count": line_count,
        "non_alnum_ratio": round(non_alnum_ratio, 6),
        "extraction_method_hint": extraction_method_hint,
    }


def run_pass_0_ingestion(
    raw_text: str,
    *,
    document_id: str,
    run_id: uuid.UUID,
    file_metadata: dict[str, Any] | None = None,
) -> AnnotationPassOutput:
    """
    Entrée : texte brut + métadonnées optionnelles (mime, extraction_method_hint).
    """
    started = AnnotationPassOutput.utc_now()
    file_metadata = file_metadata or {}
    hint = file_metadata.get("extraction_method_hint") or file_metadata.get(
        "extraction_method"
    )
    if hint not in ("native_pdf", "tesseract", "unknown", None):
        hint = "unknown"
    if hint is None:
        hint = "unknown"

    normalized, norm_notes = _normalize_text(raw_text or "")
    if not normalized.strip():
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
                    code="EMPTY_INPUT",
                    message="Empty or whitespace-only text after normalization",
                )
            ],
            metadata={
                "duration_ms": int((completed - started).total_seconds() * 1000),
            },
        )

    page_map = _build_page_map(normalized)
    feats = _features(normalized, str(hint))
    completed = AnnotationPassOutput.utc_now()
    duration_ms = int((completed - started).total_seconds() * 1000)

    return AnnotationPassOutput(
        pass_name=PASS_NAME,
        pass_version=PASS_VERSION,
        document_id=document_id,
        run_id=run_id,
        started_at=started,
        completed_at=completed,
        status=PassRunStatus.SUCCESS,
        output_data={
            "normalized_text": normalized,
            "normalization_notes": norm_notes,
            "page_map": page_map,
            "features": feats,
        },
        errors=[],
        metadata={"duration_ms": duration_ms},
    )
