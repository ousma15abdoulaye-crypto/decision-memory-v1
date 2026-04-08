"""
Criterion classification, weighting validation, and DAO extraction.

Extraction documentaire – M3A: Typed criterion extraction.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from src.db import db_execute, get_connection

logger = logging.getLogger(__name__)

# ADR-0010 D3 -- no evaluation import in couche_a; values inlined from procurement rules
_MIN_WEIGHTS: dict[str, float] = {"commercial": 0.40, "sustainability": 0.10}

_OFFER_TYPE_TO_ROLE: dict[str, str] = {
    "technique": "technical_offer",
    "financiere": "financial_offer",
    "administrative": "supporting_doc",
    "registre": "supporting_doc",
}


@dataclass
class DaoCriterion:
    """Structure d'un critère DAO brut."""

    categorie: str
    critere_nom: str
    description: str
    ponderation: float
    type_reponse: str = "text"
    seuil_elimination: float = None
    ordre_affichage: int = 0


def classify_criterion(text: str) -> str:
    """
    Détecte la catégorie d'un critère à partir de mots-clés.
    Retourne : 'essential', 'commercial', 'capacity', 'sustainability'.
    """
    text_lower = text.lower()

    essential_kw = [
        "obligatoire",
        "requis",
        "must",
        "exigé",
        "exige",
        "impératif",
        "imperatif",
        "imperativement",
        "impérativement",
        "essentiel",
        "conditions générales",
        "conditions generales",
        "certifie",
        "sanctions",
        "terrorisme",
        "admissibilité",
        "admissibilite",
        "admis",
        "déclaration sur l'honneur",
        "declaration sur l'honneur",
    ]
    if any(k in text_lower for k in essential_kw):
        return "essential"

    commercial_kw = [
        "prix",
        "coût",
        "montant",
        "tarif",
        "délai",
        "livraison",
        "paiement",
        "financial",
        "cost",
        "price",
        "budget",
        "payment",
    ]
    if any(k in text_lower for k in commercial_kw):
        return "commercial"

    capacity_kw = [
        "expérience",
        "références",
        "qualification",
        "certification",
        "capacité",
        "personnel",
        "equipment",
        "facilities",
        "qualité",
        "experience",
        "quality",
        "certified",
        "staff",
    ]
    if any(k in text_lower for k in capacity_kw):
        return "capacity"

    sustain_kw = [
        "environnement",
        "social",
        "durabilité",
        "durabilite",
        "durable",
        "rse",
        "éthique",
        "ethique",
        "développement durable",
        "developpement durable",
        "sustainable",
        "green",
        "eco",
        "environmental",
        "ethical",
        "gender",
        "diversity",
        "child labor",
    ]
    if any(k in text_lower for k in sustain_kw):
        return "sustainability"

    return "capacity"


def validate_criterion_weightings(criteria: list[dict]) -> tuple[bool, list[str]]:
    """
    Valide les pondérations minimales (commercial ≥40%, durabilité ≥10%).
    Retourne (is_valid, liste_erreurs).
    """
    min_weights = _MIN_WEIGHTS
    errors = []

    cat_weights = {"commercial": 0.0, "sustainability": 0.0}
    for c in criteria:
        cat = c.get("criterion_category")
        weight = c.get("ponderation", 0.0)
        if cat in cat_weights:
            cat_weights[cat] += weight

    if cat_weights["commercial"] < min_weights["commercial"] * 100:
        errors.append(
            f"Pondération commerciale trop faible: {cat_weights['commercial']:.1f}% "
            f"(min {min_weights['commercial'] * 100}%)"
        )
    if cat_weights["sustainability"] < min_weights["sustainability"] * 100:
        errors.append(
            f"Pondération durabilité trop faible: {cat_weights['sustainability']:.1f}% "
            f"(min {min_weights['sustainability'] * 100}%)"
        )

    return len(errors) == 0, errors


def extract_dao_criteria_structured(text: str) -> list[DaoCriterion]:
    """
    Extract structured criteria from DAO text.
    Simplified stub — in production, use more sophisticated parsing.
    """
    criteria = []

    lines = text.split("\n")
    current_category = "Général"

    for i, line in enumerate(lines):
        line_lower = line.lower()

        if any(
            keyword in line_lower for keyword in ["critère", "criteria", "évaluation"]
        ):
            if "prix" in line_lower or "coût" in line_lower:
                criteria.append(
                    DaoCriterion(
                        categorie=current_category,
                        critere_nom="Prix",
                        description=line.strip(),
                        ponderation=50.0,
                        ordre_affichage=len(criteria),
                    )
                )
            elif "expérience" in line_lower or "référence" in line_lower:
                criteria.append(
                    DaoCriterion(
                        categorie=current_category,
                        critere_nom="Expérience",
                        description=line.strip(),
                        ponderation=30.0,
                        ordre_affichage=len(criteria),
                    )
                )
            elif "durabilité" in line_lower or "environnement" in line_lower:
                criteria.append(
                    DaoCriterion(
                        categorie=current_category,
                        critere_nom="Durabilité",
                        description=line.strip(),
                        ponderation=10.0,
                        ordre_affichage=len(criteria),
                    )
                )

    if not criteria:
        criteria = [
            DaoCriterion(
                "Général", "Prix", "Prix total de l'offre", 50.0, ordre_affichage=0
            ),
            DaoCriterion(
                "Général",
                "Capacité technique",
                "Expérience et références",
                30.0,
                ordre_affichage=1,
            ),
            DaoCriterion(
                "Général",
                "Durabilité",
                "Politique environnementale et sociale",
                10.0,
                ordre_affichage=2,
            ),
        ]

    return criteria


def extract_dao_criteria_typed(
    case_id: str, extracted_criteria: list[dict]
) -> list[dict]:
    """
    Enrichit les critères extraits avec catégories, drapeau éliminatoire,
    et valide les pondérations.
    """
    enriched = []

    for crit in extracted_criteria:
        description = crit.get("description", "")
        category = classify_criterion(description)
        is_eliminatory = category == "essential"

        enriched.append(
            {
                "case_id": case_id,
                "categorie": crit.get("categorie", "Général"),
                "critere_nom": crit["critere_nom"],
                "description": description,
                "criterion_category": category,
                "is_eliminatory": is_eliminatory,
                "ponderation": crit.get("ponderation", 0.0),
                "type_reponse": crit.get("type_reponse", "text"),
                "seuil_elimination": crit.get("seuil_elimination"),
                "ordre_affichage": crit.get("ordre_affichage", 0),
            }
        )

    is_valid, errors = validate_criterion_weightings(enriched)

    with get_connection() as conn:
        comm_weight = sum(
            c["ponderation"]
            for c in enriched
            if c["criterion_category"] == "commercial"
        )
        sust_weight = sum(
            c["ponderation"]
            for c in enriched
            if c["criterion_category"] == "sustainability"
        )
        db_execute(
            conn,
            """
            INSERT INTO criteria_weighting_validation
            (case_id, commercial_weight, sustainability_weight, is_valid, validation_errors, created_at)
            VALUES (:cid, :comm, :sust, :valid, :errors, :ts)
            """,
            {
                "cid": case_id,
                "comm": comm_weight,
                "sust": sust_weight,
                "valid": is_valid,
                "errors": "\n".join(errors) if errors else None,
                "ts": datetime.now(UTC).isoformat(),
            },
        )

    if not is_valid:
        logger.warning(
            f"[VALIDATION] Case {case_id} – Pondérations non conformes: {errors}"
        )

    return enriched
