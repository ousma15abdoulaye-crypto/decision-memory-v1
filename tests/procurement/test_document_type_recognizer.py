"""Tests for src/procurement/document_type_recognizer.py — L3 type recognition."""

from __future__ import annotations

from src.procurement.document_ontology import DocumentKindParent
from src.procurement.document_type_recognizer import recognize_document_type


class TestTypeRecognition:
    def test_financial_offer(self) -> None:
        text = "PROPOSITION FINANCIÈRE\nBordereau des prix\nTotal HT: 15 000 000 FCFA"
        result = recognize_document_type(text)
        assert result.primary_kind == DocumentKindParent.OFFER_FINANCIAL

    def test_technical_offer(self) -> None:
        text = "OFFRE TECHNIQUE\nMéthodologie proposée\nNotre approche consiste"
        result = recognize_document_type(text)
        assert result.primary_kind == DocumentKindParent.OFFER_TECHNICAL

    def test_evaluation_doc_aco(self) -> None:
        text = "ANALYSE ET COMPARAISON DES OFFRES\nFournisseur 1\nFournisseur 2"
        result = recognize_document_type(text)
        assert result.primary_kind == DocumentKindParent.EVALUATION_DOC

    def test_evaluation_doc_pv(self) -> None:
        text = "PROCÈS-VERBAL D'ÉVALUATION\nComité d'évaluation"
        result = recognize_document_type(text)
        assert result.primary_kind == DocumentKindParent.EVALUATION_DOC

    def test_tdr(self) -> None:
        text = "TERMES DE RÉFÉRENCE\nObjectif de la mission\nLivrables attendus"
        result = recognize_document_type(text)
        assert result.primary_kind == DocumentKindParent.TDR

    def test_dao(self) -> None:
        text = "DOSSIER D'APPEL D'OFFRES\nInstructions aux soumissionnaires"
        result = recognize_document_type(text)
        assert result.primary_kind == DocumentKindParent.DAO

    def test_rfq(self) -> None:
        text = "DEMANDE DE COTATION\nArticles demandés\nQuantités"
        result = recognize_document_type(text)
        assert result.primary_kind == DocumentKindParent.RFQ

    def test_contract(self) -> None:
        text = "CONTRAT DE PRESTATION\nEntre la partie A d'une part\nEt la partie B d'autre part"
        result = recognize_document_type(text)
        assert result.primary_kind == DocumentKindParent.CONTRACT

    def test_po(self) -> None:
        text = "BON DE COMMANDE\nPO N° BC-2024-001\nFournisseur: ABC"
        result = recognize_document_type(text)
        assert result.primary_kind == DocumentKindParent.PO

    def test_grn(self) -> None:
        text = "BON DE RÉCEPTION\nGRN N° 2024-001\nQuantité reçue\nConforme"
        result = recognize_document_type(text)
        assert result.primary_kind == DocumentKindParent.GRN

    def test_unknown_for_empty(self) -> None:
        result = recognize_document_type("")
        assert result.primary_kind == DocumentKindParent.UNKNOWN

    def test_composite_detection(self) -> None:
        text = (
            "OFFRE TECHNIQUE\nMéthodologie\n" * 10
            + "\nOFFRE FINANCIÈRE\nBordereau des prix\nTotal HT: 5M FCFA"
        )
        result = recognize_document_type(text)
        assert (
            result.is_composite == "yes"
            or result.primary_kind == DocumentKindParent.OFFER_COMBINED
        )

    def test_evaluation_never_classified_as_offer(self) -> None:
        """Critical rule: evaluation_doc must NEVER be classified as offer_*."""
        text = (
            "ANALYSE ET COMPARAISON DES OFFRES RAPPORT D'ÉVALUATION tableau comparatif"
        )
        result = recognize_document_type(text)
        assert result.primary_kind not in (
            DocumentKindParent.OFFER_TECHNICAL,
            DocumentKindParent.OFFER_FINANCIAL,
            DocumentKindParent.OFFER_COMBINED,
        )
