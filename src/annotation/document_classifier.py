"""
Classifieur documentaire déterministe — DMS v1.0
Exécuté AVANT le LLM. Résultat non modifiable par le LLM.

CONTRAT TRANSITOIRE (ARCH-01) :
  deterministic=True  → règle Python a tranché. Le LLM n'écrase pas.
  deterministic=False → UNKNOWN. Le LLM propose uniquement.
                        ARCH-02 imposera validation contre enums fermées
                        et escalade review_required si LLM incohérent.

TAXONOMIE PROVISOIRE : bornée au routing initial, pas au canon métier final.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, unique


@unique
class TaxonomyCore(str, Enum):
    OFFER_FINANCIAL = "offer_financial"
    OFFER_TECHNICAL = "offer_technical"
    OFFER_COMBINED = "offer_combined"
    TDR_CONSULTANCE_AUDIT = "tdr_consultance_audit"
    DAO = "dao"
    DAO_CONSTRUCTION = "dao_construction_goods"
    RFQ = "rfq"
    RFP_CONSULTANCE = "rfp_consultance"
    ANNEX_PRICING = "annex_pricing"
    SUPPORTING_DOC = "supporting_doc"
    MARKET_SURVEY = "marketsurvey"
    EVALUATION_REPORT = "evaluation_report"
    UNKNOWN = "unknown"


@unique
class DocumentRole(str, Enum):
    SOURCE_RULES = "source_rules"
    FINANCIAL_OFFER = "financial_offer"
    TECHNICAL_OFFER = "technical_offer"
    COMBINED_OFFER = "combined_offer"
    ANNEX_PRICING = "annex_pricing"
    SUPPORTING_DOC = "supporting_doc"
    EVALUATION_REPORT = "evaluation_report"
    TDR = "tdr"
    DAO = "dao"
    RFQ = "rfq"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    """
    Résultat immuable du classifieur (frozen dataclass).

    Attributs :
      taxonomy_core : TaxonomyCore — famille documentaire
      document_role : DocumentRole — rôle dans le pipeline
      confidence    : float 0.0–1.0
      matched_rule  : str — règle ayant tranché (traçabilité)
      deterministic : bool — True = LLM ne surcharge PAS
    """

    taxonomy_core: TaxonomyCore
    document_role: DocumentRole
    confidence: float
    matched_rule: str
    deterministic: bool

    def to_dict(self) -> dict[str, str | float | bool]:
        return {
            "taxonomy_core": self.taxonomy_core.value,
            "document_role": self.document_role.value,
            "confidence": self.confidence,
            "matched_rule": self.matched_rule,
            "deterministic": self.deterministic,
        }


# ── Fenêtres de lecture ───────────────────────────────────────────────────────
_HEADER_WINDOW = 800  # titres H1 toujours dans les 800 premiers caractères
_BODY_WINDOW = 5000  # signaux structurels dans les 5 000 premiers caractères

# ── Patterns compilés une seule fois au chargement du module ─────────────────

_P0_FINANCIAL = re.compile(
    r"PROPOSITION\s+FINANCI[EÈ]RE"
    r"|OFFRE\s+FINANCI[EÈ]RE"
    r"|#\s*PROPOSITION\s+FINANCI[EÈ]RE"
    r"|#\s*OFFRE\s+FINANCI[EÈ]RE",
    re.IGNORECASE,
)
_P0B_SUBMISSION = re.compile(r"LETTRE\s+DE\s+SOUMISSION", re.IGNORECASE)
_P0B_AMOUNT = re.compile(
    r"TOTAL\s+HT|TOTAL\s+TTC|MONTANT\s+TOTAL|FRANCS\s+CFA\s+HT|FCFA\s+HT",
    re.IGNORECASE,
)
_P0C_BORDEREAU = re.compile(r"BORDEREAU\s+DES\s+PRIX", re.IGNORECASE)
_P0C_TOTAL = re.compile(r"TOTAL\s+(?:HT|TTC|G[EÉ]N[EÉ]RAL)", re.IGNORECASE)

_P1_TECHNICAL = re.compile(
    r"OFFRE\s+TECHNIQUE"
    r"|PROPOSITION\s+TECHNIQUE"
    r"|#\s*OFFRE\s+TECHNIQUE"
    r"|#\s*PROPOSITION\s+TECHNIQUE",
    re.IGNORECASE,
)
_P2_TDR = re.compile(
    r"TERMES?\s+DE\s+R[EÉ]F[EÉ]RENCE"
    r"|#\s*TERMES?\s+DE\s+R[EÉ]F[EÉ]RENCE"
    r"|\bTDR\b",
    re.IGNORECASE,
)
_P3_DAO = re.compile(
    r"DOSSIER\s+D.APPEL\s+D.OFFRES?" r"|APPEL\s+D.OFFRES?" r"|\bDAO\b",
    re.IGNORECASE,
)
_P4_RFQ = re.compile(
    r"DEMANDE\s+DE\s+COTATION" r"|REQUEST\s+FOR\s+QUOTATION" r"|\bRFQ\b",
    re.IGNORECASE,
)


def classify_document(raw_text: str) -> ClassificationResult:
    """
    Classifie un document de manière déterministe.
    Ordre : P0 > P0b > P0c > P1 > P2 > P3 > P4 > FALLBACK.
    Ne lève jamais d'exception. Retourne UNKNOWN au pire.
    """
    if not raw_text or not raw_text.strip():
        return ClassificationResult(
            taxonomy_core=TaxonomyCore.UNKNOWN,
            document_role=DocumentRole.UNKNOWN,
            confidence=0.0,
            matched_rule="empty_text",
            deterministic=True,
        )

    header = raw_text[:_HEADER_WINDOW]
    body = raw_text[:_BODY_WINDOW]

    if _P0_FINANCIAL.search(header):
        return ClassificationResult(
            TaxonomyCore.OFFER_FINANCIAL,
            DocumentRole.FINANCIAL_OFFER,
            1.0,
            "P0_financial_title_header",
            True,
        )
    if _P0B_SUBMISSION.search(body) and _P0B_AMOUNT.search(body):
        return ClassificationResult(
            TaxonomyCore.OFFER_FINANCIAL,
            DocumentRole.FINANCIAL_OFFER,
            1.0,
            "P0b_lettre_soumission_plus_montant",
            True,
        )
    if _P0C_BORDEREAU.search(body) and _P0C_TOTAL.search(body):
        return ClassificationResult(
            TaxonomyCore.OFFER_FINANCIAL,
            DocumentRole.FINANCIAL_OFFER,
            1.0,
            "P0c_bordereau_prix_plus_total",
            True,
        )
    if _P1_TECHNICAL.search(header):
        return ClassificationResult(
            TaxonomyCore.OFFER_TECHNICAL,
            DocumentRole.TECHNICAL_OFFER,
            1.0,
            "P1_technical_title_header",
            True,
        )
    if _P2_TDR.search(header):
        return ClassificationResult(
            TaxonomyCore.TDR_CONSULTANCE_AUDIT,
            DocumentRole.TDR,
            1.0,
            "P2_tdr_header",
            True,
        )
    if _P3_DAO.search(header):
        return ClassificationResult(
            TaxonomyCore.DAO,
            DocumentRole.DAO,
            0.8,
            "P3_dao_header",
            True,
        )
    if _P4_RFQ.search(header):
        return ClassificationResult(
            TaxonomyCore.RFQ,
            DocumentRole.RFQ,
            0.8,
            "P4_rfq_header",
            True,
        )

    return ClassificationResult(
        TaxonomyCore.UNKNOWN,
        DocumentRole.UNKNOWN,
        0.0,
        "fallback_llm_required",
        False,
    )
