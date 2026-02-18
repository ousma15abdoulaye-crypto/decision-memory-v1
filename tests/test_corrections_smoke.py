#!/usr/bin/env python3
"""
Test smoke des corrections PR
Vérifie que les corrections n'ont pas cassé la logique de base
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.business.offer_processor import (
    aggregate_supplier_packages,
    guess_supplier_name,
)


def test_guess_supplier_name_order():
    """Test que l'ordre de fallback est correct"""

    # Cas a) Filename valide et significatif
    _ = """
    Société: OMEGA CORPORATION

    Prix: 1000000 FCFA
    """

    # Filename avec nom significatif
    name = guess_supplier_name("irrelevant text", "offre_alpha_industries_2026.pdf")
    assert "ALPHA" in name, f"Expected ALPHA in '{name}'"
    print(f"✓ Test a) Filename: {name}")

    # Cas b) Pattern Société dans texte (prioritaire sur ligne majuscule)
    text_with_both = """
    TITLE LINE IN CAPS

    Société: BETA SERVICES SARL

    ANOTHER CAPS LINE
    """
    name = guess_supplier_name(text_with_both, "123_offre.pdf")
    assert "BETA" in name, f"Expected BETA in '{name}'"
    print(f"✓ Test b) Pattern Société: {name}")

    # Cas c) Ligne majuscule non-titre
    text_caps_only = """
    OFFRE TECHNIQUE

    GAMMA CONSTRUCTION SARL

    Prix: 500000 FCFA
    """
    name = guess_supplier_name(text_caps_only, "doc.pdf")
    assert "GAMMA" in name, f"Expected GAMMA in '{name}'"
    print(f"✓ Test c) Ligne majuscule: {name}")

    # Cas d) Fallback final
    name = guess_supplier_name("no useful text", "123.pdf")
    assert name == "FOURNISSEUR_INCONNU", f"Expected FOURNISSEUR_INCONNU, got '{name}'"
    print(f"✓ Test d) Fallback: {name}")


def test_missing_fields_separation():
    """Test que missing_parts et missing_extracted_fields sont séparés"""

    offers = [
        {
            "supplier_name": "TEST SUPPLIER",
            "artifact_id": "art-001",
            "subtype": {
                "subtype": "FINANCIAL_ONLY",
                "has_financial": True,
                "has_technical": False,
                "has_admin": False,
            },
            "total_price": "1000000 FCFA",
            "total_price_source": "Pattern",
            "currency": "XOF",
            "lead_time_days": None,  # Manquant dans partie financière
            "lead_time_source": None,
            "validity_days": 90,
            "validity_source": "Pattern",
            "technical_refs": [],
            "missing_fields": ["Délai livraison"],
        }
    ]

    packages = aggregate_supplier_packages(offers)

    assert len(packages) == 1
    pkg = packages[0]

    # Vérifier missing_parts (sections non soumises)
    assert (
        "TECHNICAL" in pkg.extracted_data["missing_parts"]
    ), "Should have TECHNICAL in missing_parts"
    assert (
        "ADMIN" in pkg.extracted_data["missing_parts"]
    ), "Should have ADMIN in missing_parts"

    # Vérifier missing_extracted_fields (données manquantes dans sections soumises)
    assert (
        "Délai livraison" in pkg.extracted_data["missing_extracted_fields"]
    ), "Should have Délai in missing_extracted_fields"

    # missing_fields devrait contenir seulement les champs extraits manquants
    assert pkg.missing_fields == [
        "Délai livraison"
    ], f"Expected ['Délai livraison'], got {pkg.missing_fields}"

    print(f"✓ missing_parts: {pkg.extracted_data['missing_parts']}")
    print(
        f"✓ missing_extracted_fields: {pkg.extracted_data['missing_extracted_fields']}"
    )
    print(f"✓ missing_fields (compat): {pkg.missing_fields}")


def test_no_id_in_supplier_name():
    """Vérifier qu'aucun ID n'est utilisé comme nom"""

    # Filename avec UUID
    name = guess_supplier_name("test", "offre_abc123def456_lot1.pdf")
    assert "abc123def456" not in name.lower(), f"UUID should be removed from '{name}'"
    print(f"✓ UUID removed: {name}")

    # Filename vide après nettoyage
    name = guess_supplier_name("no pattern", "2026_offre_lot.pdf")
    assert (
        name == "FOURNISSEUR_INCONNU"
    ), f"Empty filename should return FOURNISSEUR_INCONNU, got '{name}'"
    print(f"✓ Empty filename handled: {name}")


def main():
    print("\n" + "=" * 60)
    print("TESTS SMOKE — CORRECTIONS PR")
    print("=" * 60 + "\n")

    try:
        print("Test 1: Ordre de fallback guess_supplier_name")
        print("-" * 60)
        test_guess_supplier_name_order()
        print()

        print("Test 2: Séparation missing_parts / missing_extracted_fields")
        print("-" * 60)
        test_missing_fields_separation()
        print()

        print("Test 3: Pas d'ID dans les noms")
        print("-" * 60)
        test_no_id_in_supplier_name()
        print()

        print("=" * 60)
        print("✅ TOUS LES TESTS SMOKE PASSÉS")
        print("=" * 60)
        print("\nCorrections validées:")
        print("  ✓ guess_supplier_name() - ordre de fallback correct")
        print("  ✓ missing_fields séparés (parts vs extracted)")
        print("  ✓ Aucun ID technique dans les noms")
        print()

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
