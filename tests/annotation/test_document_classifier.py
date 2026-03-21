"""
Tests déterministes — classifieur documentaire DMS.
Zéro LLM · Zéro DB · Zéro réseau.
18 cas : succès + priorité + faux positifs + mixtes + dégradés + frozen.
"""

import pytest

from src.annotation.document_classifier import (
    ClassificationResult,
    DocumentRole,
    TaxonomyCore,
    classify_document,
)

# Aligné sur document_classifier._HEADER_WINDOW (non importé : API privée).
_HEADER_LEN = 800

# ── Fixtures corpus Mali ──────────────────────────────────────────────────────

F_FINANCIERE_H1 = (
    "A - Z Sarl\nPROPOSITION FINANCIERE\n"
    "Objet : Offre technique pour l'enquête IAAT\n"
    "LETTRE DE SOUMISSION\n29 194 950 Francs CFA HT\nTOTAL HT 29 194 950\n"
)
F_FINANCIERE_LETTRE = (
    "Cabinet XYZ\nLETTRE DE SOUMISSION\n"
    "Nous proposons quinze millions de Francs CFA HT\nTOTAL HT 15 000 000\n"
)
F_FINANCIERE_BORDEREAU = (
    "BORDEREAU DES PRIX\nLot 1 — ciment 15 000 FCFA\nTOTAL HT 4 450 000\n"
)
F_TECHNIQUE_H1 = "OFFRE TECHNIQUE\nPour l'enquête IAAT\nMéthodologie...\nCV expert...\n"
F_TDR = (
    "TERMES DE REFERENCE\nRecrutement cabinet enquête IAAT\n" "Critères...\nSeuil 60%\n"
)
F_DAO = "DOSSIER D'APPEL D'OFFRES\nFourniture matériaux construction\nLot 1 ciment\n"
F_RFQ = "DEMANDE DE COTATION\nFourniture cartouches impression SCI Mali\n"
F_ATTESTATION = (
    "ATTESTATION DE SERVICES FAITS\n"
    "La société X a fourni les prestations conformément au contrat.\n"
)
F_EMPTY = ""
F_BLANK = "   \n\n\t   "

# Cas mixte : DAO + bordereau des prix dans le même document
F_DAO_PLUS_BORDEREAU = (
    "DOSSIER D'APPEL D'OFFRES\nFourniture ciment\n"
    "BORDEREAU DES PRIX\nLot 1 ciment 15 000\nTOTAL HT 150 000\n"
)
# Cas corps ambigu : pas de titre mais signaux faibles multiples
F_CORPS_AMBIGU = (
    "Bamako, le 01 août 2025\n"
    "Objet : réponse à votre consultation\n"
    "Suite à votre demande, veuillez trouver ci-joint notre proposition.\n"
)
# Cas OCR bruité : titre avec espaces parasites / caractères cassés
F_OCR_BRUITE_FINANCIER = (
    "P R O P O S I T I O N   F I N A N C I E R E\n"
    "LETTRE DE SOUMISSION\nTOTAL HT 5 000 000 Francs CFA HT\n"
)
# RFQ uniquement après les _HEADER_LEN premiers caractères : P4 ne voit pas « RFQ » dans le header.
_DAO_RFQ_PREFIX = "DOSSIER D'APPEL D'OFFRES\n"
_DAO_RFQ_PAD = "." * max(0, _HEADER_LEN - len(_DAO_RFQ_PREFIX))
F_DAO_AVEC_RFQ_DANS_CORPS = (
    f"{_DAO_RFQ_PREFIX}{_DAO_RFQ_PAD}"
    "\nSuite à la RFQ préliminaire du 01/07/2025\n"
    "Lot 1 — fourniture\n"
)


# ── Tests chemins de succès ───────────────────────────────────────────────────


def test_p0_financiere_titre_h1():
    r = classify_document(F_FINANCIERE_H1)
    assert r.taxonomy_core == TaxonomyCore.OFFER_FINANCIAL
    assert r.document_role == DocumentRole.FINANCIAL_OFFER
    assert r.confidence == 1.0
    assert r.deterministic is True
    assert r.matched_rule == "P0_financial_title_header"


def test_p0b_lettre_soumission_plus_montant():
    r = classify_document(F_FINANCIERE_LETTRE)
    assert r.taxonomy_core == TaxonomyCore.OFFER_FINANCIAL
    assert r.document_role == DocumentRole.FINANCIAL_OFFER
    assert r.matched_rule == "P0b_lettre_soumission_plus_montant"


def test_p0c_bordereau_plus_total():
    r = classify_document(F_FINANCIERE_BORDEREAU)
    assert r.taxonomy_core == TaxonomyCore.OFFER_FINANCIAL
    assert r.document_role == DocumentRole.FINANCIAL_OFFER
    assert r.matched_rule == "P0c_bordereau_prix_plus_total"


def test_p1_technique_titre_h1():
    r = classify_document(F_TECHNIQUE_H1)
    assert r.taxonomy_core == TaxonomyCore.OFFER_TECHNICAL
    assert r.document_role == DocumentRole.OFFER_TECHNICAL
    assert r.confidence == 1.0
    assert r.deterministic is True


def test_p2_tdr():
    r = classify_document(F_TDR)
    assert r.taxonomy_core == TaxonomyCore.TDR_CONSULTANCE_AUDIT
    assert r.document_role == DocumentRole.SOURCE_RULES
    assert r.confidence == 1.0


def test_p3_dao():
    r = classify_document(F_DAO)
    assert r.taxonomy_core == TaxonomyCore.DAO_CONSTRUCTION
    assert r.document_role == DocumentRole.SOURCE_RULES
    assert r.confidence == 0.8


def test_p4_rfq():
    r = classify_document(F_RFQ)
    assert r.taxonomy_core == TaxonomyCore.RFQ
    assert r.document_role == DocumentRole.SOURCE_RULES
    assert r.confidence == 0.8


# ── Tests fallback et cas dégradés ────────────────────────────────────────────


def test_fallback_attestation():
    """Document sans signal connu → fallback LLM, pas de classification forcée."""
    r = classify_document(F_ATTESTATION)
    assert r.taxonomy_core == TaxonomyCore.UNKNOWN
    assert r.document_role == DocumentRole.UNKNOWN
    assert r.confidence == 0.0
    assert r.deterministic is False
    assert r.matched_rule == "fallback_llm_required"


def test_empty_text():
    r = classify_document(F_EMPTY)
    assert r.taxonomy_core == TaxonomyCore.UNKNOWN
    assert r.matched_rule == "empty_text"
    assert r.deterministic is True  # UNKNOWN déterministe, pas fallback LLM


def test_blank_text():
    r = classify_document(F_BLANK)
    assert r.taxonomy_core == TaxonomyCore.UNKNOWN
    assert r.matched_rule == "empty_text"
    assert r.deterministic is True


# ── Tests priorité de patterns ────────────────────────────────────────────────


def test_priorite_p0_gagne_sur_p0b():
    """
    P0 (titre H1) doit gagner sur P0b (lettre + montant) même si les deux
    signaux sont présents. Vérifier que matched_rule = P0, pas P0b.
    """
    r = classify_document(F_FINANCIERE_H1)
    assert r.matched_rule == "P0_financial_title_header"
    # P0b aurait aussi matché (lettre + TOTAL HT présents dans la fixture)
    # → P0 doit avoir la priorité absolue


def test_dao_avec_bordereau_retourne_financier():
    """
    DAO + bordereau des prix dans le même document.
    P0c (bordereau + TOTAL HT) doit prendre le dessus sur P3 (DAO).
    Ce cas représente un DAO avec BPU intégré — c'est une offre financière
    sur le plan de l'extraction, pas un dossier source.
    """
    r = classify_document(F_DAO_PLUS_BORDEREAU)
    assert r.taxonomy_core == TaxonomyCore.OFFER_FINANCIAL
    assert r.matched_rule == "P0c_bordereau_prix_plus_total"


def test_faux_positif_rfq_dans_corps_dao():
    """
    Padding entre titre DAO et « RFQ » : la mention est hors fenêtre header (800).
    P3 matche sur le titre dans raw_text[:800] ; P4 (\bRFQ\b) ne matche pas le header.
    """
    assert "RFQ" not in F_DAO_AVEC_RFQ_DANS_CORPS[:_HEADER_LEN]
    assert len(F_DAO_AVEC_RFQ_DANS_CORPS[:_HEADER_LEN]) == _HEADER_LEN
    r = classify_document(F_DAO_AVEC_RFQ_DANS_CORPS)
    assert r.taxonomy_core == TaxonomyCore.DAO_CONSTRUCTION
    assert r.matched_rule == "P3_dao_header"


def test_corps_ambigu_retourne_fallback():
    """
    Corps ambigu sans titre connu → UNKNOWN, fallback LLM.
    On ne force pas une classification incertaine.
    """
    r = classify_document(F_CORPS_AMBIGU)
    assert r.taxonomy_core == TaxonomyCore.UNKNOWN
    assert r.deterministic is False


# ── Test dégradé OCR ──────────────────────────────────────────────────────────


def test_ocr_bruite_titre_sans_p0_mais_p0b_lettre_et_total_ht():
    """
    Titre bruité : espaces entre lettres → P0 (regex compact) ne matche pas.
    LETTRE DE SOUMISSION + TOTAL HT / Francs CFA HT dans le corps → P0b classe
    offer_financial / financial_offer (pas UNKNOWN / fallback LLM).
    """
    r = classify_document(F_OCR_BRUITE_FINANCIER)
    assert r.taxonomy_core == TaxonomyCore.OFFER_FINANCIAL
    assert r.matched_rule == "P0b_lettre_soumission_plus_montant"


# ── Test golden — cas sentinelle AZ SARL ─────────────────────────────────────


def test_golden_az_sarl_ne_regresse_jamais():
    """
    GOLDEN — texte réel Offre-Financiere.pdf (A-Z SARL, 29 194 950 FCFA).
    'Objet : Offre technique' dans la lettre NE doit PAS router offer_technical.
    Ce test ne doit JAMAIS régresser.
    """
    r = classify_document(F_FINANCIERE_H1)
    assert r.taxonomy_core == TaxonomyCore.OFFER_FINANCIAL
    assert r.document_role == DocumentRole.FINANCIAL_OFFER
    assert r.confidence == 1.0
    assert r.deterministic is True
    assert r.matched_rule == "P0_financial_title_header"


# ── Test structure to_dict ────────────────────────────────────────────────────


def test_to_dict_structure_et_types():
    r = classify_document(F_FINANCIERE_H1)
    d = r.to_dict()
    assert set(d.keys()) == {
        "taxonomy_core",
        "document_role",
        "confidence",
        "matched_rule",
        "deterministic",
    }
    assert isinstance(d["taxonomy_core"], str)
    assert isinstance(d["document_role"], str)
    assert isinstance(d["confidence"], float)
    assert isinstance(d["matched_rule"], str)
    assert isinstance(d["deterministic"], bool)
    # Offre financière : pas de confusion avec offer_technical
    assert d["document_role"] == "financial_offer"
    assert d["document_role"] != "offer_technical"
    assert d["taxonomy_core"] == "offer_financial"


def test_technical_fixture_emits_offer_technical_role():
    d = classify_document(F_TECHNIQUE_H1).to_dict()
    assert d["taxonomy_core"] == "offer_technical"
    assert d["document_role"] == "offer_technical"


def test_classification_result_est_frozen():
    """Contrat doc : résultat immuable (dataclass frozen)."""
    r = ClassificationResult(
        TaxonomyCore.DAO_CONSTRUCTION,
        DocumentRole.SOURCE_RULES,
        0.8,
        "P3_dao_header",
        True,
    )
    with pytest.raises(AttributeError, match="cannot assign|frozen"):
        r.matched_rule = "x"  # type: ignore[misc]
