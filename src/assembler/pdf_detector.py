"""Détection du type de PDF : natif vs scan — avant OCR.

Évite d'appeler Mistral OCR 3 (coûteux) sur un PDF natif extractable
avec pdfminer/pypdf2 gratuitement.

Référence : Plan V4.2.0 Phase 4 — src/assembler/pdf_detector.py
ADR-V420-001 (pydantic-ai).
"""

from __future__ import annotations

import logging
from enum import StrEnum
from pathlib import Path

logger = logging.getLogger(__name__)

MIN_CHARS_NATIVE = 50


class FileType(StrEnum):
    NATIVE_PDF = "native_pdf"
    SCAN = "scan"
    WORD = "word"
    EXCEL = "excel"
    IMAGE = "image"
    UNKNOWN = "unknown"


def detect_file_type(file_path: str | Path) -> FileType:
    """Détecte le type d'un fichier pour sélectionner le moteur OCR approprié.

    Args:
        file_path: Chemin vers le fichier extrait du ZIP.

    Returns:
        FileType enum indiquant le type détecté.
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext in {".docx", ".doc"}:
        return FileType.WORD

    if ext in {".xlsx", ".xls"}:
        return FileType.EXCEL

    if ext in {".jpg", ".jpeg", ".png", ".tiff", ".tif"}:
        return FileType.IMAGE

    if ext != ".pdf":
        return FileType.UNKNOWN

    try:
        import pypdf  # type: ignore[import-untyped]

        with open(path, "rb") as f:
            reader = pypdf.PdfReader(f)
            text = ""
            for page in reader.pages[:3]:
                text += page.extract_text() or ""
                if len(text) >= MIN_CHARS_NATIVE:
                    break

        if len(text.strip()) >= MIN_CHARS_NATIVE:
            return FileType.NATIVE_PDF
        return FileType.SCAN

    except Exception as exc:
        logger.debug("[PDF-DETECT] Erreur lecture PDF %s : %s — assume SCAN", path, exc)
        return FileType.SCAN
