"""Profils d'évaluation pré‑encodés par catégorie d'achat (Manuel SCI)."""
from typing import Any, Dict

EVALUATION_PROFILES: Dict[str, Dict[str, Any]] = {
    "GENERIC": {
        "criteria": [
            {"category": "essential", "weight": 0.0, "eliminatory": True},
            {"category": "commercial", "weight": 0.50, "min_weight": 0.40},
            {"category": "capacity", "weight": 0.30},
            {"category": "sustainability", "weight": 0.10, "min_weight": 0.10},
        ],
        "min_suppliers": 3
    },
    "HEALTH": {
        "criteria": [
            {"category": "essential", "weight": 0.0, "eliminatory": True},
            {"category": "commercial", "weight": 0.40, "min_weight": 0.40},
            {"category": "capacity", "weight": 0.40},
            {"category": "sustainability", "weight": 0.10, "min_weight": 0.10},
        ],
        "requires_qualified_suppliers": True,
        "min_suppliers": 5
    },
    "CONSTR": {
        "criteria": [
            {"category": "essential", "weight": 0.0, "eliminatory": True},
            {"category": "commercial", "weight": 0.40, "min_weight": 0.40},
            {"category": "capacity", "weight": 0.40},
            {"category": "sustainability", "weight": 0.10, "min_weight": 0.10},
        ],
        "requires_technical_expert": True,
        "requires_site_visit": True,
        "min_suppliers": 5
    },
    "IT": {
        "criteria": [
            {"category": "essential", "weight": 0.0, "eliminatory": True},
            {"category": "commercial", "weight": 0.50, "min_weight": 0.40},
            {"category": "capacity", "weight": 0.35},
            {"category": "sustainability", "weight": 0.15, "min_weight": 0.10},
        ],
        "requires_section_889": True,
        "min_suppliers": 3
    },
    "TRAVEL": {
        "criteria": [
            {"category": "essential", "weight": 0.0, "eliminatory": True},
            {"category": "commercial", "weight": 0.60, "min_weight": 0.40},
            {"category": "capacity", "weight": 0.25},
            {"category": "sustainability", "weight": 0.10, "min_weight": 0.10},
        ],
        "max_procedure": "devis_formel",
        "min_suppliers": 3
    },
    "PROPERTY": {
        "criteria": [
            {"category": "essential", "weight": 0.0, "eliminatory": True},
            {"category": "commercial", "weight": 0.50, "min_weight": 0.40},
            {"category": "capacity", "weight": 0.35},
            {"category": "sustainability", "weight": 0.10, "min_weight": 0.10},
        ],
        "requires_legal_review": True,
        "min_suppliers": 3
    },
    "LABOR": {
        "criteria": [
            {"category": "essential", "weight": 0.0, "eliminatory": True},
            {"category": "commercial", "weight": 0.45, "min_weight": 0.40},
            {"category": "capacity", "weight": 0.40},
            {"category": "sustainability", "weight": 0.10, "min_weight": 0.10},
        ],
        "fee_limits": True,
        "min_suppliers": 3
    },
    "CVA": {
        "criteria": [
            {"category": "essential", "weight": 0.0, "eliminatory": True},
            {"category": "commercial", "weight": 0.50, "min_weight": 0.40},
            {"category": "capacity", "weight": 0.35},
            {"category": "sustainability", "weight": 0.10, "min_weight": 0.10},
        ],
        "requires_fsp_panel": True,
        "min_suppliers": 3
    },
    "FLEET": {
        "criteria": [
            {"category": "essential", "weight": 0.0, "eliminatory": True},
            {"category": "commercial", "weight": 0.45, "min_weight": 0.40},
            {"category": "capacity", "weight": 0.35},
            {"category": "sustainability", "weight": 0.15, "min_weight": 0.10},
        ],
        "safety_standards": True,
        "min_suppliers": 3
    },
    "INSURANCE": {
        "criteria": [
            {"category": "essential", "weight": 0.0, "eliminatory": True},
            {"category": "commercial", "weight": 0.70, "min_weight": 0.40},
            {"category": "capacity", "weight": 0.20},
            {"category": "sustainability", "weight": 0.10, "min_weight": 0.10},
        ],
        "provider": "Marsh/MMB",
        "no_competition": True,
        "min_suppliers": 1
    }
}

def get_profile_for_category(category_code: str) -> Dict[str, Any]:
    """Retourne le profil d'évaluation pour une catégorie donnée (défaut = GENERIC)."""
    return EVALUATION_PROFILES.get(category_code, EVALUATION_PROFILES["GENERIC"])

def get_min_weights() -> Dict[str, float]:
    """Retourne les pondérations minimales exigées par le Manuel SCI."""
    return {"commercial": 0.40, "sustainability": 0.10}
