"""Tests pour l'extraction typée des critères (M3A)."""
from src.couche_a.extraction import classify_criterion, validate_criterion_weightings
from src.evaluation.profiles import get_profile_for_category


def test_classify_essential():
    """Test classification of essential criteria."""
    assert classify_criterion("Ce critère est obligatoire") == "essential"
    assert classify_criterion("Le fournisseur doit impérativement fournir") == "essential"
    assert classify_criterion("Conditions générales acceptées") == "essential"


def test_classify_commercial():
    """Test classification of commercial criteria."""
    assert classify_criterion("Prix unitaire en FCFA") == "commercial"
    assert classify_criterion("Délai de livraison maximum 30 jours") == "commercial"
    assert classify_criterion("Conditions de paiement") == "commercial"


def test_classify_capacity():
    """Test classification of capacity criteria."""
    assert classify_criterion("Expérience similaire dans les 3 dernières années") == "capacity"
    assert classify_criterion("Certification ISO 9001") == "capacity"
    assert classify_criterion("Références de projets antérieurs") == "capacity"


def test_classify_sustainability():
    """Test classification of sustainability criteria."""
    assert classify_criterion("Politique environnementale") == "sustainability"
    assert classify_criterion("Engagement social et communautaire") == "sustainability"
    assert classify_criterion("Pratiques de développement durable") == "sustainability"


def test_validate_weightings_ok():
    """Test validation with correct weightings."""
    criteria = [
        {"criterion_category": "commercial", "ponderation": 50},
        {"criterion_category": "sustainability", "ponderation": 15},
        {"criterion_category": "capacity", "ponderation": 35}
    ]
    is_valid, errors = validate_criterion_weightings(criteria)
    assert is_valid is True
    assert errors == []


def test_validate_weightings_fail_commercial():
    """Test validation fails when commercial weight is too low."""
    criteria = [
        {"criterion_category": "commercial", "ponderation": 30},
        {"criterion_category": "sustainability", "ponderation": 20},
        {"criterion_category": "capacity", "ponderation": 50}
    ]
    is_valid, errors = validate_criterion_weightings(criteria)
    assert is_valid is False
    assert any("commercial" in e.lower() for e in errors)


def test_validate_weightings_fail_sustainability():
    """Test validation fails when sustainability weight is too low."""
    criteria = [
        {"criterion_category": "commercial", "ponderation": 60},
        {"criterion_category": "sustainability", "ponderation": 5},
        {"criterion_category": "capacity", "ponderation": 35}
    ]
    is_valid, errors = validate_criterion_weightings(criteria)
    assert is_valid is False
    assert any("durabilité" in e or "sustainability" in e.lower() for e in errors)


def test_validate_weightings_fail_both():
    """Test validation fails when both weights are too low."""
    criteria = [
        {"criterion_category": "commercial", "ponderation": 30},
        {"criterion_category": "sustainability", "ponderation": 5},
        {"criterion_category": "capacity", "ponderation": 65}
    ]
    is_valid, errors = validate_criterion_weightings(criteria)
    assert is_valid is False
    assert len(errors) == 2


def test_profile_for_category():
    """Test profile retrieval for categories."""
    profile = get_profile_for_category("HEALTH")
    assert profile["requires_qualified_suppliers"] is True
    assert profile["min_suppliers"] == 5
    assert profile["criteria"][0]["category"] == "essential"


def test_profile_for_category_generic():
    """Test generic profile is returned for unknown categories."""
    profile = get_profile_for_category("UNKNOWN")
    assert profile["min_suppliers"] == 3
    assert len(profile["criteria"]) == 4


def test_profile_for_category_it():
    """Test IT category profile."""
    profile = get_profile_for_category("IT")
    assert profile["requires_section_889"] is True
    assert profile["min_suppliers"] == 3


def test_profile_for_category_construction():
    """Test construction category profile."""
    profile = get_profile_for_category("CONSTR")
    assert profile["requires_technical_expert"] is True
    assert profile["requires_site_visit"] is True
    assert profile["min_suppliers"] == 5
