"""
Comprehensive unit tests for offer_processor module.
Tests detection, aggregation, extraction, and supplier name guessing.
"""
import pytest
from src.business.offer_processor import (
    detect_offer_subtype,
    aggregate_supplier_packages,
    guess_supplier_name,
    extract_offer_data_guided,
)
from src.core.models import DAOCriterion


class TestDetectOfferSubtype:
    """Tests for detect_offer_subtype function."""

    def test_combined_offer_all_sections(self):
        """Offer with financial, technical, and admin content should be COMBINED."""
        text = """
        OFFRE COMPLETE
        
        Prix total: 50.000.000 FCFA
        Caractéristiques techniques: conformes aux spécifications
        Documents administratifs: attestation fiscale jointe
        """
        result = detect_offer_subtype(text, "offre_complete.pdf")
        
        assert result.subtype == "COMBINED"
        assert result.has_financial is True
        assert result.has_technical is True
        assert result.has_admin is True
        assert result.confidence in ("HIGH", "MEDIUM")

    def test_financial_only_from_text(self):
        """Offer with only financial content should be FINANCIAL_ONLY."""
        text = """
        BORDEREAU DE PRIX
        
        Montant total: 25.000.000 FCFA
        Délai de livraison: 30 jours
        """
        result = detect_offer_subtype(text, "document.pdf")
        
        assert result.subtype == "FINANCIAL_ONLY"
        assert result.has_financial is True
        assert result.has_technical is False
        assert result.has_admin is False

    def test_technical_only_from_text(self):
        """Offer with only technical content should be TECHNICAL_ONLY."""
        text = """
        OFFRE TECHNIQUE
        
        Spécifications techniques détaillées
        Références clients: Projet ABC, Projet XYZ
        Capacité technique prouvée
        """
        result = detect_offer_subtype(text, "document.pdf")
        
        assert result.subtype == "TECHNICAL_ONLY"
        assert result.has_financial is False
        assert result.has_technical is True
        assert result.has_admin is False

    def test_admin_only_from_text(self):
        """Offer with only admin content should be ADMIN_ONLY."""
        text = """
        DOCUMENTS ADMINISTRATIFS
        
        Attestation fiscale
        Registre de commerce RCCM
        Certificat de conformité
        """
        result = detect_offer_subtype(text, "document.pdf")
        
        assert result.subtype == "ADMIN_ONLY"
        assert result.has_financial is False
        assert result.has_technical is False
        assert result.has_admin is True

    def test_fallback_to_filename_financial(self):
        """Should detect FINANCIAL_ONLY from filename when text is empty."""
        text = "no useful content here"
        result = detect_offer_subtype(text, "offre_financiere_lot1.pdf")
        
        assert result.subtype == "FINANCIAL_ONLY"
        assert result.has_financial is True

    def test_fallback_to_filename_technical(self):
        """Should detect TECHNICAL_ONLY from filename when text is empty."""
        text = "no useful content here"
        result = detect_offer_subtype(text, "specification_technique.pdf")
        
        assert result.subtype == "TECHNICAL_ONLY"
        assert result.has_technical is True

    def test_fallback_to_filename_admin(self):
        """Should detect ADMIN_ONLY from filename when text is empty."""
        text = "no useful content here"
        result = detect_offer_subtype(text, "documents_administratifs.pdf")
        
        assert result.subtype == "ADMIN_ONLY"
        assert result.has_admin is True

    def test_unknown_when_nothing_detected(self):
        """Should return UNKNOWN when no patterns match."""
        text = "some random text without keywords"
        result = detect_offer_subtype(text, "random.pdf")
        
        assert result.subtype == "UNKNOWN"
        assert result.confidence == "LOW"

    def test_combined_two_sections(self):
        """Offer with two sections should be COMBINED with MEDIUM confidence."""
        text = """
        Prix unitaire: 1000 FCFA
        Références techniques: Projet Alpha
        """
        result = detect_offer_subtype(text, "offre.pdf")
        
        assert result.subtype == "COMBINED"
        assert result.has_financial is True
        assert result.has_technical is True
        assert result.confidence == "MEDIUM"


class TestAggregateSupplierPackages:
    """Tests for aggregate_supplier_packages function."""

    def test_single_supplier_complete(self):
        """Single supplier with all sections should be COMPLETE."""
        offers = [
            {
                "supplier_name": "ACME Corp",
                "artifact_id": "art-001",
                "subtype": {
                    "has_financial": True,
                    "has_technical": True,
                    "has_admin": True,
                },
                "total_price": "100000 FCFA",
                "currency": "XOF",
                "lead_time_days": 30,
                "validity_days": 90,
                "technical_refs": ["Ref1"],
            }
        ]
        packages = aggregate_supplier_packages(offers)
        
        assert len(packages) == 1
        assert packages[0].supplier_name == "ACME Corp"
        assert packages[0].package_status == "COMPLETE"
        assert packages[0].has_financial is True
        assert packages[0].has_technical is True
        assert packages[0].has_admin is True

    def test_single_supplier_partial(self):
        """Single supplier with only financial should be PARTIAL."""
        offers = [
            {
                "supplier_name": "BETA Inc",
                "artifact_id": "art-002",
                "subtype": {
                    "has_financial": True,
                    "has_technical": False,
                    "has_admin": False,
                },
                "total_price": "50000 FCFA",
                "currency": "XOF",
                "lead_time_days": None,
                "validity_days": None,
                "technical_refs": [],
            }
        ]
        packages = aggregate_supplier_packages(offers)
        
        assert len(packages) == 1
        assert packages[0].package_status == "PARTIAL"
        assert "TECHNICAL" in packages[0].extracted_data["missing_parts"]
        assert "ADMIN" in packages[0].extracted_data["missing_parts"]

    def test_multiple_documents_same_supplier(self):
        """Multiple documents from same supplier should be merged."""
        offers = [
            {
                "supplier_name": "GAMMA Ltd",
                "artifact_id": "art-001",
                "subtype": {"has_financial": True, "has_technical": False, "has_admin": False},
                "total_price": "75000 FCFA",
                "currency": "XOF",
                "lead_time_days": 45,
                "validity_days": 90,
                "technical_refs": [],
            },
            {
                "supplier_name": "GAMMA Ltd",
                "artifact_id": "art-002",
                "subtype": {"has_financial": False, "has_technical": True, "has_admin": False},
                "total_price": None,
                "currency": "XOF",
                "lead_time_days": None,
                "validity_days": None,
                "technical_refs": ["Project X", "Project Y"],
            },
        ]
        packages = aggregate_supplier_packages(offers)
        
        assert len(packages) == 1
        pkg = packages[0]
        assert pkg.supplier_name == "GAMMA Ltd"
        assert pkg.has_financial is True
        assert pkg.has_technical is True
        assert len(pkg.offer_ids) == 2
        assert pkg.extracted_data["total_price"] == "75000 FCFA"
        assert "Project X" in pkg.extracted_data["technical_refs"]

    def test_multiple_suppliers(self):
        """Multiple suppliers should create separate packages."""
        offers = [
            {
                "supplier_name": "ALPHA",
                "artifact_id": "art-001",
                "subtype": {"has_financial": True, "has_technical": False, "has_admin": False},
                "total_price": "100",
                "currency": "XOF",
                "lead_time_days": 30,
                "validity_days": 90,
                "technical_refs": [],
            },
            {
                "supplier_name": "BETA",
                "artifact_id": "art-002",
                "subtype": {"has_financial": True, "has_technical": True, "has_admin": False},
                "total_price": "200",
                "currency": "XOF",
                "lead_time_days": 60,
                "validity_days": 90,
                "technical_refs": ["Ref"],
            },
        ]
        packages = aggregate_supplier_packages(offers)
        
        assert len(packages) == 2
        names = {p.supplier_name for p in packages}
        assert names == {"ALPHA", "BETA"}

    def test_missing_status_no_financial_no_technical(self):
        """Offer with no financial and no technical should be MISSING."""
        offers = [
            {
                "supplier_name": "DELTA",
                "artifact_id": "art-001",
                "subtype": {"has_financial": False, "has_technical": False, "has_admin": True},
                "total_price": None,
                "currency": "XOF",
                "lead_time_days": None,
                "validity_days": None,
                "technical_refs": [],
            }
        ]
        packages = aggregate_supplier_packages(offers)
        
        assert len(packages) == 1
        assert packages[0].package_status == "MISSING"

    def test_missing_extracted_fields_tracked(self):
        """Missing extracted fields should be tracked separately from missing parts."""
        offers = [
            {
                "supplier_name": "EPSILON",
                "artifact_id": "art-001",
                "subtype": {"has_financial": True, "has_technical": True, "has_admin": False},
                "total_price": None,  # Missing from financial section
                "currency": "XOF",
                "lead_time_days": 30,
                "validity_days": None,  # Missing from financial section
                "technical_refs": [],  # Missing from technical section
            }
        ]
        packages = aggregate_supplier_packages(offers)
        
        pkg = packages[0]
        assert "Prix total" in pkg.extracted_data["missing_extracted_fields"]
        assert "Validité offre" in pkg.extracted_data["missing_extracted_fields"]
        assert "Références techniques" in pkg.extracted_data["missing_extracted_fields"]
        assert "ADMIN" in pkg.extracted_data["missing_parts"]

    def test_deduplication_of_technical_refs(self):
        """Technical refs should be deduplicated when merging."""
        offers = [
            {
                "supplier_name": "ZETA",
                "artifact_id": "art-001",
                "subtype": {"has_financial": False, "has_technical": True, "has_admin": False},
                "total_price": None,
                "currency": "XOF",
                "lead_time_days": None,
                "validity_days": None,
                "technical_refs": ["Project A", "Project B"],
            },
            {
                "supplier_name": "ZETA",
                "artifact_id": "art-002",
                "subtype": {"has_financial": False, "has_technical": True, "has_admin": False},
                "total_price": None,
                "currency": "XOF",
                "lead_time_days": None,
                "validity_days": None,
                "technical_refs": ["Project B", "Project C"],  # B is duplicate
            },
        ]
        packages = aggregate_supplier_packages(offers)
        
        refs = packages[0].extracted_data["technical_refs"]
        assert len(refs) == 3
        assert set(refs) == {"Project A", "Project B", "Project C"}


class TestGuessSupplierName:
    """Tests for guess_supplier_name function."""

    def test_extract_from_filename(self):
        """Should extract supplier name from meaningful filename."""
        name = guess_supplier_name("irrelevant text", "ALPHA_CONSTRUCTION_offre.pdf")
        assert "ALPHA" in name
        assert "CONSTRUCTION" in name

    def test_extract_from_societe_pattern(self):
        """Should extract from 'Société: ...' pattern in text when filename is generic."""
        text = """
        Société: BETA SERVICES SARL
        
        Some content here
        """
        # Use a filename that won't produce a valid supplier name after cleaning
        name = guess_supplier_name(text, "123.pdf")
        assert "BETA" in name

    def test_extract_from_entreprise_pattern(self):
        """Should extract from 'Entreprise: ...' pattern in text."""
        text = """
        Entreprise: GAMMA INDUSTRIES
        """
        name = guess_supplier_name(text, "doc.pdf")
        assert "GAMMA" in name

    def test_extract_from_caps_line(self):
        """Should extract from uppercase line when no other patterns match."""
        text = """
        OFFRE TECHNIQUE
        
        DELTA CORPORATION INTERNATIONAL
        
        Some content here
        """
        name = guess_supplier_name(text, "123.pdf")
        assert "DELTA" in name

    def test_fallback_to_unknown(self):
        """Should return FOURNISSEUR_INCONNU when nothing found."""
        name = guess_supplier_name("no useful text", "123.pdf")
        assert name == "FOURNISSEUR_INCONNU"

    def test_removes_uuid_from_filename(self):
        """Should remove UUID-like patterns (8+ hex chars) from filename."""
        # UUID-like pattern of 8+ hex chars should be removed
        name = guess_supplier_name("text", "offre_abcdef12_acme.pdf")
        assert "abcdef12" not in name.lower()

    def test_removes_common_keywords(self):
        """Should remove common keywords like 'offre', 'dao'."""
        name = guess_supplier_name("text", "offre_acme_corp_dao.pdf")
        # Should include supplier name but not generic keywords
        assert "ACME" in name
        # Check that 'offre' and 'dao' are removed as separate words
        words = name.lower().split()
        assert "offre" not in words
        assert "dao" not in words

    def test_skips_section_titles_in_caps(self):
        """Should skip section titles like 'OFFRE TECHNIQUE'."""
        text = """
        OFFRE TECHNIQUE
        
        REAL SUPPLIER NAME HERE
        """
        name = guess_supplier_name(text, "doc.pdf")
        assert "OFFRE" not in name
        assert "REAL" in name or "SUPPLIER" in name

    def test_max_length_80(self):
        """Supplier name should be capped at 80 characters."""
        long_text = "A" * 200
        text = f"Société: {long_text}"
        name = guess_supplier_name(text, "doc.pdf")
        assert len(name) <= 80

    def test_filename_priority_over_text_pattern(self):
        """Meaningful filename should take priority over text patterns."""
        text = "Société: OTHER NAME"
        name = guess_supplier_name(text, "PREFERRED_SUPPLIER_offre.pdf")
        assert "PREFERRED" in name


class TestExtractOfferDataGuided:
    """Tests for extract_offer_data_guided function."""

    def test_extract_price_with_commercial_criteria(self):
        """Should extract price when commercial criteria present."""
        text = "Prix total: 50.000.000 FCFA"
        criteria = [DAOCriterion(
            categorie="commercial",
            critere_nom="Prix",
            description="Prix de l'offre",
            ponderation=50.0,
            type_reponse="number",
            seuil_elimination=None,
            ordre_affichage=0
        )]
        
        result = extract_offer_data_guided(text, criteria)
        
        assert result["total_price"] is not None
        assert "50" in result["total_price"]
        assert "FCFA" in result["total_price"]

    def test_extract_lead_time(self):
        """Should extract lead time in days."""
        text = "Délai de livraison: 45 jours"
        criteria = []
        
        result = extract_offer_data_guided(text, criteria)
        
        assert result["lead_time_days"] == 45
        assert "Délai" in result["lead_time_source"]

    def test_extract_validity(self):
        """Should extract offer validity in days."""
        text = "Validité de l'offre: 90 jours"
        criteria = []
        
        result = extract_offer_data_guided(text, criteria)
        
        assert result["validity_days"] == 90
        assert "Validité" in result["validity_source"]

    def test_extract_technical_refs(self):
        """Should extract technical references when technical criteria present."""
        text = """
        Référence: Projet Infrastructure Dakar 2024
        Client: Ministère des Travaux Publics
        """
        criteria = [DAOCriterion(
            categorie="technique",
            critere_nom="Expérience",
            description="Références techniques",
            ponderation=30.0,
            type_reponse="text",
            seuil_elimination=None,
            ordre_affichage=0
        )]
        
        result = extract_offer_data_guided(text, criteria)
        
        assert len(result["technical_refs"]) > 0

    def test_missing_fields_tracked(self):
        """Should track missing fields."""
        text = "Some text without prices or dates"
        criteria = [DAOCriterion(
            categorie="commercial",
            critere_nom="Prix",
            description="Prix",
            ponderation=50.0,
            type_reponse="number",
            seuil_elimination=None,
            ordre_affichage=0
        )]
        
        result = extract_offer_data_guided(text, criteria)
        
        assert "Prix total" in result["missing_fields"]
        assert "Délai livraison" in result["missing_fields"]
        assert "Validité offre" in result["missing_fields"]

    def test_default_currency_xof(self):
        """Default currency should be XOF."""
        result = extract_offer_data_guided("text", [])
        assert result["currency"] == "XOF"

    def test_price_extraction_various_formats(self):
        """Should handle various price formats."""
        test_cases = [
            ("Montant total: 1 000 000 FCFA", "1 000 000"),
            ("Total: 1.500.000 CFA", "1.500.000"),
            ("Prix: 2500000 XOF", "2500000"),
        ]
        
        criteria = [DAOCriterion(
            categorie="commercial",
            critere_nom="Prix",
            description="Prix",
            ponderation=50.0,
            type_reponse="number",
            seuil_elimination=None,
            ordre_affichage=0
        )]
        
        for text, expected_amount in test_cases:
            result = extract_offer_data_guided(text, criteria)
            assert result["total_price"] is not None, f"Failed for: {text}"

    def test_no_price_extraction_without_commercial_criteria(self):
        """Should not extract price when no commercial criteria."""
        text = "Prix total: 50.000.000 FCFA"
        criteria = [DAOCriterion(
            categorie="technique",
            critere_nom="Technique",
            description="Technique",
            ponderation=50.0,
            type_reponse="text",
            seuil_elimination=None,
            ordre_affichage=0
        )]
        
        result = extract_offer_data_guided(text, criteria)
        
        # Price should not be extracted since no commercial criteria
        assert result["total_price"] is None
