"""
Package ``src.annotation`` — outils autour de l’annotation DMS.

- :mod:`src.annotation.document_classifier` — classifieur déterministe pré-LLM (ARCH-01),
  littéraux alignés sur ``prompts/system_prompt.txt``.
- :mod:`src.annotation.m12_export_io` — lecture des exports JSONL m12-v2.
- :mod:`src.annotation.structured_pdf_preview` — métadonnées tables PDF pour le bridge LS.
"""

from src.annotation.document_classifier import (
    ClassificationResult,
    DocumentRole,
    TaxonomyCore,
    classify_document,
)

__all__ = [
    "ClassificationResult",
    "DocumentRole",
    "TaxonomyCore",
    "classify_document",
]
