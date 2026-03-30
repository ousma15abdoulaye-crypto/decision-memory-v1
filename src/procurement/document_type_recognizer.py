"""
M12 V6 L3 — Document Type Recognizer.

Recognizes document_kind (parent + subtype) with composite detection.
Includes the ao vs dao discriminant.
Absorbs and extends the legacy classify_document() deterministic rules.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Literal

from src.procurement.document_ontology import (
    DocumentKindParent,
    DocumentKindSubtype,
)

logger = logging.getLogger(__name__)

_HEADER_WINDOW = 800
_BODY_WINDOW = 5000
_FULL_WINDOW = 20000
_COMPOSITE_WINDOW = 800


@dataclass(frozen=True, slots=True)
class TypeRecognitionResult:
    primary_kind: DocumentKindParent
    primary_subtype: DocumentKindSubtype
    secondary_kinds: list[DocumentKindParent]
    is_composite: Literal["yes", "no", "unknown"]
    composite_confidence: float
    confidence: float
    evidence: list[str]
    matched_rule: str


_RULES: list[
    tuple[
        re.Pattern[str],
        str,
        DocumentKindParent,
        DocumentKindSubtype,
        float,
        str,
    ]
] = [
    # Financial offers — check first (header)
    (
        re.compile(
            r"PROPOSITION\s+FINANCI[EÈ]RE|OFFRE\s+FINANCI[EÈ]RE",
            re.IGNORECASE,
        ),
        "header",
        DocumentKindParent.OFFER_FINANCIAL,
        DocumentKindSubtype.GENERIC,
        0.95,
        "R01_financial_title_header",
    ),
    # Bordereau + total -> financial
    (
        re.compile(r"BORDEREAU\s+DES\s+PRIX", re.IGNORECASE),
        "body_with_total",
        DocumentKindParent.OFFER_FINANCIAL,
        DocumentKindSubtype.GENERIC,
        0.90,
        "R02_bordereau_prix_total",
    ),
    # Technical offers
    (
        re.compile(
            r"OFFRE\s+TECHNIQUE|PROPOSITION\s+TECHNIQUE",
            re.IGNORECASE,
        ),
        "header",
        DocumentKindParent.OFFER_TECHNICAL,
        DocumentKindSubtype.GENERIC,
        0.95,
        "R03_technical_title_header",
    ),
    # Evaluation doc / ACO / PV
    (
        re.compile(
            r"ANALYSE?\s+(?:ET\s+)?COMPAR(?:AISON|ATIVE)\s+(?:DES\s+)?OFFRES?"
            r"|PROC[EÈ]S[- ]VERBAL\s+D.(?:OUVERTURE|[EÉ]VALUATION)"
            r"|RAPPORT\s+D.[EÉ]VALUATION"
            r"|\bACO\b",
            re.IGNORECASE,
        ),
        "header",
        DocumentKindParent.EVALUATION_DOC,
        DocumentKindSubtype.GENERIC,
        0.90,
        "R04_evaluation_doc_header",
    ),
    # TDR
    (
        re.compile(
            r"TERMES?\s+DE\s+R[EÉ]F[EÉ]RENCE|\bTDR\b",
            re.IGNORECASE,
        ),
        "header",
        DocumentKindParent.TDR,
        DocumentKindSubtype.CONSULTANCY_GENERIC,
        0.90,
        "R05_tdr_header",
    ),
    # Contract
    (
        re.compile(
            r"CONTRAT\s+DE\s+|CONVENTION\s+DE\s+|ACCORD[- ]CADRE" r"|MARCH[EÉ]\s+N[°o]",
            re.IGNORECASE,
        ),
        "header",
        DocumentKindParent.CONTRACT,
        DocumentKindSubtype.GENERIC,
        0.85,
        "R06_contract_header",
    ),
    # DAO — full dossier: "DOSSIER D'APPEL D'OFFRES" or "APPEL D'OFFRES" in header
    (
        re.compile(
            r"DOSSIER\s+D.APPEL\s+D.OFFRES?"
            r"|APPEL\s+D.OFFRES?\s+(?:RESTREINT|OUVERT|POUR|RELATIF|CONCERNANT|N[°o])"
            r"|APPEL\s+D.OFFRES\b",
            re.IGNORECASE,
        ),
        "header",
        DocumentKindParent.DAO,
        DocumentKindSubtype.FOURNITURE,
        0.85,
        "R07_dao_header",
    ),
    # RFQ
    (
        re.compile(
            r"DEMANDE\s+DE\s+COTATION|REQUEST\s+FOR\s+QUOTATION|\bRFQ\b",
            re.IGNORECASE,
        ),
        "header",
        DocumentKindParent.RFQ,
        DocumentKindSubtype.GENERIC,
        0.85,
        "R09_rfq_header",
    ),
    # PO
    (
        re.compile(
            r"BON\s+DE\s+COMMANDE|PURCHASE\s+ORDER|\bPO\s+N",
            re.IGNORECASE,
        ),
        "header",
        DocumentKindParent.PO,
        DocumentKindSubtype.GENERIC,
        0.85,
        "R10_po_header",
    ),
    # GRN
    (
        re.compile(
            r"BON\s+DE\s+R[EÉ]CEPTION|GOODS\s+RECEIVED\s+NOTE|\bGRN\b",
            re.IGNORECASE,
        ),
        "header",
        DocumentKindParent.GRN,
        DocumentKindSubtype.GENERIC,
        0.85,
        "R11_grn_header",
    ),
    # Market survey
    (
        re.compile(
            r"[EÉ]TUDE\s+DE\s+MARCH[EÉ]|MARKET\s+SURVEY|PROSPECTION",
            re.IGNORECASE,
        ),
        "body",
        DocumentKindParent.MARKET_SURVEY,
        DocumentKindSubtype.GENERIC,
        0.80,
        "R12_market_survey_body",
    ),
    # Submission letter (narrowed: "Je soussigné" alone is too broad — catches certificates)
    (
        re.compile(
            r"LETTRE\s+DE\s+SOUMISSION",
            re.IGNORECASE,
        ),
        "header",
        DocumentKindParent.SUBMISSION_LETTER,
        DocumentKindSubtype.GENERIC,
        0.80,
        "R13_submission_letter_header",
    ),
    # Financial offer — broader body patterns (supplier quotes, budgets)
    (
        re.compile(
            r"FOURNITURE\s+DE\s+.*(?:PRIX|MONTANT|TOTAL)"
            r"|DEVIS\s+(?:ESTIMATIF|N[°o])"
            r"|OFFRE\s+DE\s+PRIX"
            r"|(?:Honoraire|Honoraires)\s+.*\d+\s*\d{3}"
            r"|C\.\s*Unitaires?\s+Total",
            re.IGNORECASE,
        ),
        "body",
        DocumentKindParent.OFFER_FINANCIAL,
        DocumentKindSubtype.GENERIC,
        0.75,
        "R17_financial_body_prix",
    ),
    # Supporting documents: CVs / resumes (most common supporting doc type)
    (
        re.compile(
            r"CURRICULUM\s+VITAE"
            r"|\bCV\b\s"
            r"|PROFIL\s+PROFESSIONNEL"
            r"|P\s*R\s*O\s*F\s*I\s*L\s+P\s*R\s*O\s*F\s*E\s*S"
            r"|EXPERIENCES?\s+PROFESSIONNELLES?"
            r"|E\s*X\s*P\s*E\s*R\s*I\s*E\s*N\s*C\s*E\s*S?\s+P\s*R\s*O\s*F"
            r"|RENSEIGNEMENTS\s+PERSONNELS"
            r"|PROFESSIONAL\s+(?:EXPERIENCE|PROFILE|BACKGROUND)"
            r"|PORTFOLIO\s+MANAGER"
            r"|PROFIL\b.*\bEXPERIENCE"
            r"|EDUCATION\s+.*EXPERIENCE",
            re.IGNORECASE,
        ),
        "body",
        DocumentKindParent.SUPPORTING_DOC,
        DocumentKindSubtype.GENERIC,
        0.80,
        "R18_supporting_cv_body",
    ),
    # Supporting documents: policies, compliance, code of conduct
    (
        re.compile(
            r"POLITIQUE\s+DE\s+(?:SAUVEGARDE|D[EÉ]VELOPPEMENT\s+DURABLE|PROTECTION)"
            r"|SAFEGUARDING\s+POLICY"
            r"|SUSTAINABLE\s+DEVELOPMENT\s+POLICY"
            r"|CODE\s+(?:DE\s+)?CONDUITE"
            r"|CODE\s+OF\s+CONDUCT"
            r"|ENGAGEMENT\s+.*(?:RESPECT|POLITIQUES?)"
            r"|CONDITIONS\s+G[EÉ]N[EÉ]RALES\s+D.ACHAT",
            re.IGNORECASE,
        ),
        "body",
        DocumentKindParent.SUPPORTING_DOC,
        DocumentKindSubtype.GENERIC,
        0.85,
        "R14_supporting_policy_body",
    ),
    # Supporting documents: admin docs, company registration
    (
        re.compile(
            r"DOCUMENTS?\s+ADMINISTRATIF"
            r"|ADMINISTRATIVE\s+DOCUMENTS?"
            r"|FICHE\s+SIGNAL[EÉ]TIQUE"
            r"|PI[EÈ]CES?\s+ADMINISTRATIVES?"
            r"|DOSSIER\s+ADMINISTRATIF"
            r"|D[EÉ]CLARATION\s+(?:DE\s+)?CONSTITUTION"
            r"|PERSONNE\s+MORALE"
            r"|CERTIFICAT\s+D.IMMATRICULATION",
            re.IGNORECASE,
        ),
        "body",
        DocumentKindParent.SUPPORTING_DOC,
        DocumentKindSubtype.ADMIN,
        0.80,
        "R15_supporting_admin_body",
    ),
    # Supporting documents: certificates, legal attestations (OCR-resilient)
    (
        re.compile(
            r"ATTESTATION\s+(?:DE\s+|D.)"
            r"|CERTIFICAT\s+(?:DE\s+|D.)"
            r"|C\s*E\s*R\s*T\s*I\s*F\s*I\s*C\s*A\s*T\s+D"
            r"|IMMATRICULATION"
            r"|QUITUS\s+FISCAL"
            r"|REGISTRE\s+(?:DE\s+)?COMMERCE",
            re.IGNORECASE,
        ),
        "body",
        DocumentKindParent.SUPPORTING_DOC,
        DocumentKindSubtype.CERTIFICATION,
        0.75,
        "R16_supporting_certificate_body",
    ),
    # Supporting documents: digital signatures, compliance envelopes
    (
        re.compile(
            r"DocuSign\s+Envelope"
            r"|ENGAGEMENT\s+(?:DE|DU|POUR)\s+"
            r"|RESPECT\s+DES\s+POLITIQUES",
            re.IGNORECASE,
        ),
        "body",
        DocumentKindParent.SUPPORTING_DOC,
        DocumentKindSubtype.GENERIC,
        0.70,
        "R19_supporting_digital_body",
    ),
]

_TOTAL_PATTERN = re.compile(r"TOTAL\s+(?:HT|TTC|G[EÉ]N[EÉ]RAL)", re.IGNORECASE)


def _check_composite(
    text: str, primary: DocumentKindParent
) -> tuple[list[DocumentKindParent], Literal["yes", "no", "unknown"], float]:
    """Check if document contains title-level signals for multiple types.

    Only checks the first ~800 chars (header area) to avoid false positives
    from incidental mentions of financial/technical terms deep in body text.
    """
    secondary: list[DocumentKindParent] = []
    header_area = text[:_COMPOSITE_WINDOW]

    has_tech = bool(
        re.search(
            r"OFFRE\s+TECHNIQUE|PROPOSITION\s+TECHNIQUE", header_area, re.IGNORECASE
        )
    )
    has_fin = bool(
        re.search(
            r"OFFRE\s+FINANCI[EÈ]RE|PROPOSITION\s+FINANCI[EÈ]RE",
            header_area,
            re.IGNORECASE,
        )
    )

    if primary == DocumentKindParent.OFFER_TECHNICAL and has_fin:
        secondary.append(DocumentKindParent.OFFER_FINANCIAL)
        return secondary, "yes", 0.80
    if primary == DocumentKindParent.OFFER_FINANCIAL and has_tech:
        secondary.append(DocumentKindParent.OFFER_TECHNICAL)
        return secondary, "yes", 0.80

    return secondary, "no", 0.95


def recognize_document_type(text: str) -> TypeRecognitionResult:
    """Deterministic document type recognition with composite detection."""
    if not text or not text.strip():
        return TypeRecognitionResult(
            primary_kind=DocumentKindParent.UNKNOWN,
            primary_subtype=DocumentKindSubtype.OTHER,
            secondary_kinds=[],
            is_composite="unknown",
            composite_confidence=0.0,
            confidence=0.60,
            evidence=["empty_text"],
            matched_rule="empty_text",
        )

    header = text[:_HEADER_WINDOW]
    body = text[:_BODY_WINDOW]

    for pattern, scope, kind, subtype, conf, rule in _RULES:
        target = header if scope == "header" else body
        if scope == "body_with_total":
            if pattern.search(body) and _TOTAL_PATTERN.search(body):
                sec, comp, comp_conf = _check_composite(text, kind)
                if comp == "yes" and kind in (
                    DocumentKindParent.OFFER_TECHNICAL,
                    DocumentKindParent.OFFER_FINANCIAL,
                ):
                    return TypeRecognitionResult(
                        DocumentKindParent.OFFER_COMBINED,
                        DocumentKindSubtype.GENERIC,
                        [kind],
                        comp,
                        comp_conf,
                        conf,
                        [rule, "composite_detected"],
                        rule,
                    )
                return TypeRecognitionResult(
                    kind,
                    subtype,
                    sec,
                    comp,
                    comp_conf,
                    conf,
                    [rule],
                    rule,
                )
            continue

        if pattern.search(target):
            sec, comp, comp_conf = _check_composite(text, kind)
            if comp == "yes" and kind in (
                DocumentKindParent.OFFER_TECHNICAL,
                DocumentKindParent.OFFER_FINANCIAL,
            ):
                return TypeRecognitionResult(
                    DocumentKindParent.OFFER_COMBINED,
                    DocumentKindSubtype.GENERIC,
                    [kind],
                    comp,
                    comp_conf,
                    conf,
                    [rule, "composite_detected"],
                    rule,
                )
            return TypeRecognitionResult(
                kind,
                subtype,
                sec,
                comp,
                comp_conf,
                conf,
                [rule],
                rule,
            )

    return TypeRecognitionResult(
        DocumentKindParent.UNKNOWN,
        DocumentKindSubtype.OTHER,
        [],
        "unknown",
        0.0,
        0.30,
        ["no_rule_matched"],
        "fallback_unknown",
    )
