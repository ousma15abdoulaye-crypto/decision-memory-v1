"""
Extraction documentaire – M3A: Typed criterion extraction.

Package decomposed from the original extraction.py monolith.
Re-exports all public symbols for backward compatibility.
"""

from .backend_client import (
    _get_router,
)
from .backend_client import (
    call_annotation_backend as _call_annotation_backend,
)
from .backend_client import (
    extract_fields as _extract_fields,
)
from .backend_client import (
    extract_line_items as _extract_line_items,
)
from .criterion import (
    _MIN_WEIGHTS,
    _OFFER_TYPE_TO_ROLE,
    DaoCriterion,
    classify_criterion,
    extract_dao_criteria_structured,
    extract_dao_criteria_typed,
    validate_criterion_weightings,
)
from .offer_pipeline import (
    extract_and_persist_offer as _extract_and_persist_offer,
)
from .offer_pipeline import (
    extract_dao_content,
    extract_offer_content,
    extract_offer_content_async,
)
from .persistence import (
    persist_tdr_result_to_db as _persist_tdr_result_to_db,
)
from .persistence import (
    tdr_result_to_offer_extraction_row as _tdr_result_to_offer_extraction_row,
)
from .text_extraction import (
    MIN_EXTRACTED_TEXT_CHARS_FOR_ML,
    ExtractionInsufficientTextError,
    _try_llamaparse_pdf_first,
    extract_pdf_text_local_only,
    extract_text_any,
)

__all__ = [
    "ExtractionInsufficientTextError",
    "MIN_EXTRACTED_TEXT_CHARS_FOR_ML",
    "extract_text_any",
    "extract_pdf_text_local_only",
    "_try_llamaparse_pdf_first",
    "DaoCriterion",
    "classify_criterion",
    "validate_criterion_weightings",
    "extract_dao_criteria_structured",
    "extract_dao_criteria_typed",
    "extract_dao_content",
    "extract_offer_content",
    "extract_offer_content_async",
    "_extract_and_persist_offer",
    "_call_annotation_backend",
    "_get_router",
    "_persist_tdr_result_to_db",
    "_tdr_result_to_offer_extraction_row",
    "_extract_fields",
    "_extract_line_items",
    "_OFFER_TYPE_TO_ROLE",
    "_MIN_WEIGHTS",
]
