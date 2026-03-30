"""
M12 V6 — Taxonomy Mapping: bidirectional corpus taxonomy_core to M12 enums.

Maps the annotation corpus taxonomy (v3.0.1d) to M12 DocumentKindParent + subtype.
Also bridges legacy TaxonomyCore / DocumentRole from document_classifier.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.procurement.document_ontology import (
    DocumentKindParent,
    DocumentKindSubtype,
    DocumentLayer,
)


@dataclass(frozen=True, slots=True)
class CorpusTypeMapping:
    """Single mapping from a corpus taxonomy_core value to M12 enums."""

    corpus_key: str
    parent: DocumentKindParent
    subtype: DocumentKindSubtype


CORPUS_TO_M12: tuple[CorpusTypeMapping, ...] = (
    CorpusTypeMapping(
        "offer_technical",
        DocumentKindParent.OFFER_TECHNICAL,
        DocumentKindSubtype.GENERIC,
    ),
    CorpusTypeMapping(
        "offer_financial",
        DocumentKindParent.OFFER_FINANCIAL,
        DocumentKindSubtype.GENERIC,
    ),
    CorpusTypeMapping(
        "offer_combined", DocumentKindParent.OFFER_COMBINED, DocumentKindSubtype.GENERIC
    ),
    CorpusTypeMapping("dao", DocumentKindParent.DAO, DocumentKindSubtype.FOURNITURE),
    CorpusTypeMapping(
        "dao_construction_goods",
        DocumentKindParent.DAO,
        DocumentKindSubtype.CONSTRUCTION_GOODS,
    ),
    CorpusTypeMapping(
        "tdr_consultance_audit",
        DocumentKindParent.TDR,
        DocumentKindSubtype.CONSULTANCY_GENERIC,
    ),
    CorpusTypeMapping(
        "tdr_consultancy_baseline_study",
        DocumentKindParent.TDR,
        DocumentKindSubtype.CONSULTANCY_BASELINE_STUDY,
    ),
    CorpusTypeMapping("rfq", DocumentKindParent.RFQ, DocumentKindSubtype.GENERIC),
    CorpusTypeMapping(
        "rfp_consultance",
        DocumentKindParent.ITT,
        DocumentKindSubtype.CONSULTANCY_GENERIC,
    ),
    CorpusTypeMapping(
        "ao_consultancy_baseline_study",
        DocumentKindParent.ITT,
        DocumentKindSubtype.CONSULTANCY_BASELINE_STUDY,
    ),
    CorpusTypeMapping(
        "annex_pricing", DocumentKindParent.PRICE_SCHEDULE, DocumentKindSubtype.GENERIC
    ),
    CorpusTypeMapping(
        "supporting_doc", DocumentKindParent.SUPPORTING_DOC, DocumentKindSubtype.GENERIC
    ),
    CorpusTypeMapping(
        "marketsurvey", DocumentKindParent.MARKET_SURVEY, DocumentKindSubtype.GENERIC
    ),
    CorpusTypeMapping(
        "evaluation_report",
        DocumentKindParent.EVALUATION_DOC,
        DocumentKindSubtype.GENERIC,
    ),
    CorpusTypeMapping(
        "evaluation_report_works",
        DocumentKindParent.EVALUATION_DOC,
        DocumentKindSubtype.WORKS,
    ),
    CorpusTypeMapping(
        "contract", DocumentKindParent.CONTRACT, DocumentKindSubtype.GENERIC
    ),
    CorpusTypeMapping("po", DocumentKindParent.PO, DocumentKindSubtype.GENERIC),
    CorpusTypeMapping("grn", DocumentKindParent.GRN, DocumentKindSubtype.GENERIC),
    CorpusTypeMapping("boq", DocumentKindParent.BOQ, DocumentKindSubtype.WORKS),
    CorpusTypeMapping(
        "submission_letter",
        DocumentKindParent.SUBMISSION_LETTER,
        DocumentKindSubtype.GENERIC,
    ),
    CorpusTypeMapping(
        "admin_doc", DocumentKindParent.ADMIN_DOC, DocumentKindSubtype.ADMIN
    ),
    CorpusTypeMapping(
        "mercuriale",
        DocumentKindParent.MERCURIALE_REFERENCE,
        DocumentKindSubtype.GENERIC,
    ),
    CorpusTypeMapping("unknown", DocumentKindParent.UNKNOWN, DocumentKindSubtype.OTHER),
)

_CORPUS_KEY_TO_MAPPING: dict[str, CorpusTypeMapping] = {
    m.corpus_key: m for m in CORPUS_TO_M12
}

_PARENT_SUBTYPE_TO_CORPUS: dict[tuple[DocumentKindParent, DocumentKindSubtype], str] = {
    (m.parent, m.subtype): m.corpus_key for m in CORPUS_TO_M12
}


def corpus_to_parent_subtype(
    corpus_key: str,
) -> tuple[DocumentKindParent, DocumentKindSubtype]:
    """Map a corpus taxonomy_core value to M12 parent + subtype."""
    mapping = _CORPUS_KEY_TO_MAPPING.get(corpus_key)
    if mapping is None:
        return DocumentKindParent.UNKNOWN, DocumentKindSubtype.OTHER
    return mapping.parent, mapping.subtype


def parent_subtype_to_corpus(
    parent: DocumentKindParent, subtype: DocumentKindSubtype
) -> str:
    """Map M12 parent + subtype back to corpus taxonomy_core key."""
    return _PARENT_SUBTYPE_TO_CORPUS.get((parent, subtype), "unknown")


# Legacy bridge: map old TaxonomyCore (from document_classifier.py) to M12
LEGACY_TAXONOMY_TO_M12: dict[str, DocumentKindParent] = {
    "offer_financial": DocumentKindParent.OFFER_FINANCIAL,
    "offer_technical": DocumentKindParent.OFFER_TECHNICAL,
    "offer_combined": DocumentKindParent.OFFER_COMBINED,
    "tdr_consultance_audit": DocumentKindParent.TDR,
    "dao": DocumentKindParent.DAO,
    "dao_construction_goods": DocumentKindParent.DAO,
    "rfq": DocumentKindParent.RFQ,
    "rfp_consultance": DocumentKindParent.ITT,
    "annex_pricing": DocumentKindParent.PRICE_SCHEDULE,
    "supporting_doc": DocumentKindParent.SUPPORTING_DOC,
    "marketsurvey": DocumentKindParent.MARKET_SURVEY,
    "evaluation_report": DocumentKindParent.EVALUATION_DOC,
    "unknown": DocumentKindParent.UNKNOWN,
}

LEGACY_ROLE_TO_LAYER: dict[str, DocumentLayer] = {
    "source_rules": DocumentLayer.SOURCE_RULES,
    "financial_offer": DocumentLayer.BID_RESPONSE,
    "offer_technical": DocumentLayer.BID_RESPONSE,
    "combined_offer": DocumentLayer.BID_RESPONSE,
    "annex_pricing": DocumentLayer.BID_RESPONSE,
    "supporting_doc": DocumentLayer.UNKNOWN,
    "evaluation_report": DocumentLayer.EVALUATION,
    "unknown": DocumentLayer.UNKNOWN,
}


def legacy_taxonomy_to_m12(taxonomy_core: str) -> DocumentKindParent:
    """Bridge from legacy TaxonomyCore string to M12 DocumentKindParent."""
    return LEGACY_TAXONOMY_TO_M12.get(taxonomy_core, DocumentKindParent.UNKNOWN)


def all_corpus_keys() -> frozenset[str]:
    """All known corpus taxonomy_core values."""
    return frozenset(_CORPUS_KEY_TO_MAPPING.keys())
