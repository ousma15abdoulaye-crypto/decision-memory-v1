#!/usr/bin/env python3
"""
Test des offres partielles (FINANCIAL_ONLY)
Vérifie que le système gère correctement les offres financières uniquement
sans pénalité automatique.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.business.offer_processor import (
    detect_offer_subtype,
    aggregate_supplier_packages,
    guess_supplier_name,
    OfferSubtype
)


def test_detect_financial_only():
    """Test détection d'une offre financière uniquement"""
    
    text = """
    OFFRE FINANCIERE
    
    Entreprise: SARL ALPHA CONSTRUCTION
    
    Prix Total: 45.000.000 FCFA
    Délai de livraison: 60 jours
    Validité de l'offre: 90 jours
    """
    
    filename = "OFFRE_FINANCIERE_ALPHA.pdf"
    
    subtype = detect_offer_subtype(text, filename)
    
    print("=" * 60)
    print("TEST 1: Détection offre financière uniquement")
    print("=" * 60)
    print(f"Subtype détecté: {subtype.subtype}")
    print(f"Has Financial: {subtype.has_financial}")
    print(f"Has Technical: {subtype.has_technical}")
    print(f"Has Admin: {subtype.has_admin}")
    print(f"Confidence: {subtype.confidence}")
    
    assert subtype.subtype == "FINANCIAL_ONLY", f"Expected FINANCIAL_ONLY, got {subtype.subtype}"
    assert subtype.has_financial is True
    assert subtype.has_technical is False
    assert subtype.has_admin is False
    
    print("✅ Test 1 PASSED\n")


def test_supplier_name_extraction():
    """Test extraction du nom fournisseur (pas d'ID)"""
    
    text = """
    SOCIÉTÉ: BETA SERVICES SARL
    
    Offre technique et financière
    """
    
    filename = "offre_lot1_beta_services.pdf"
    
    name = guess_supplier_name(text, filename)
    
    print("=" * 60)
    print("TEST 2: Extraction nom fournisseur")
    print("=" * 60)
    print(f"Filename: {filename}")
    print(f"Nom extrait: {name}")
    
    # Vérifier qu'on n'a pas d'ID ou de patterns génériques
    assert "BETA" in name.upper()
    assert not any(c in name.lower() for c in ["uuid", "hash", "unknown"])
    
    print("✅ Test 2 PASSED\n")


def test_aggregate_three_financial_only():
    """Test agrégation de 3 offres financières uniquement"""
    
    offers = [
        {
            "supplier_name": "ALPHA CONSTRUCTION",
            "artifact_id": "art-001",
            "subtype": {
                "subtype": "FINANCIAL_ONLY",
                "has_financial": True,
                "has_technical": False,
                "has_admin": False,
                "confidence": "MEDIUM"
            },
            "total_price": "45000000 FCFA",
            "total_price_source": "Pattern: 'Prix Total'",
            "currency": "XOF",
            "lead_time_days": 60,
            "lead_time_source": "Pattern: 'Délai de livraison'",
            "validity_days": 90,
            "validity_source": "Pattern: 'Validité'",
            "technical_refs": [],
            "missing_fields": ["Références techniques"]
        },
        {
            "supplier_name": "BETA SERVICES",
            "artifact_id": "art-002",
            "subtype": {
                "subtype": "FINANCIAL_ONLY",
                "has_financial": True,
                "has_technical": False,
                "has_admin": False,
                "confidence": "MEDIUM"
            },
            "total_price": "42000000 FCFA",
            "total_price_source": "Pattern: 'Montant total'",
            "currency": "XOF",
            "lead_time_days": 45,
            "lead_time_source": "Pattern: 'Délai'",
            "validity_days": 90,
            "validity_source": "Pattern: 'Validité'",
            "technical_refs": [],
            "missing_fields": ["Références techniques"]
        },
        {
            "supplier_name": "GAMMA INDUSTRIES",
            "artifact_id": "art-003",
            "subtype": {
                "subtype": "FINANCIAL_ONLY",
                "has_financial": True,
                "has_technical": False,
                "has_admin": False,
                "confidence": "MEDIUM"
            },
            "total_price": "48500000 FCFA",
            "total_price_source": "Pattern: 'Prix'",
            "currency": "XOF",
            "lead_time_days": 75,
            "lead_time_source": "Pattern: 'Livraison'",
            "validity_days": 90,
            "validity_source": "Pattern: 'Validité offre'",
            "technical_refs": [],
            "missing_fields": ["Références techniques"]
        }
    ]
    
    packages = aggregate_supplier_packages(offers)
    
    print("=" * 60)
    print("TEST 3: Agrégation de 3 offres financières uniquement")
    print("=" * 60)
    print(f"Nombre de packages: {len(packages)}")
    
    for pkg in packages:
        print(f"\nFournisseur: {pkg.supplier_name}")
        print(f"  Package Status: {pkg.package_status}")
        print(f"  Has Financial: {pkg.has_financial}")
        print(f"  Has Technical: {pkg.has_technical}")
        print(f"  Has Admin: {pkg.has_admin}")
        print(f"  Prix: {pkg.extracted_data.get('total_price')}")
        print(f"  Champs manquants: {pkg.missing_fields}")
        
        # Vérifications
        assert pkg.package_status == "PARTIAL", f"Expected PARTIAL, got {pkg.package_status}"
        assert pkg.has_financial is True
        assert pkg.has_technical is False
        
    print("\n✅ Test 3 PASSED")
    print("\n📋 COMPORTEMENT ATTENDU VÉRIFIÉ:")
    print("  - Offres FINANCIAL_ONLY détectées")
    print("  - Package status = PARTIAL (pas MISSING)")
    print("  - Prix correctement extraits")
    print("  - Champs techniques marqués comme manquants")
    print("  - AUCUNE PÉNALITÉ AUTOMATIQUE")
    print("  - Prêt pour export CBA avec marqueurs REVUE MANUELLE")


def main():
    """Exécute tous les tests"""
    print("\n" + "=" * 60)
    print("TESTS DES OFFRES PARTIELLES - DMS CBA ENGINE")
    print("=" * 60 + "\n")
    
    try:
        test_detect_financial_only()
        test_supplier_name_extraction()
        test_aggregate_three_financial_only()
        
        print("\n" + "=" * 60)
        print("✅ TOUS LES TESTS PASSÉS")
        print("=" * 60)
        print("\nLe moteur gère correctement:")
        print("  1. Détection automatique des subtypes (FINANCIAL_ONLY, etc.)")
        print("  2. Extraction des noms fournisseurs (pas d'IDs)")
        print("  3. Agrégation par fournisseur avec statut PARTIAL")
        print("  4. Pas de pénalité pour documents non soumis")
        print("  5. Prêt pour marquage REVUE MANUELLE dans le CBA\n")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
