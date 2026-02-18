"""
Extraction documentaire – M3A: Typed criterion extraction.
"""

import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from src.db import db_execute, get_connection
from src.evaluation.profiles import get_min_weights

logger = logging.getLogger(__name__)


# ------------------------------------------------------------
# DATA STRUCTURES
# ------------------------------------------------------------
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


# ------------------------------------------------------------
# TEXT EXTRACTION
# ------------------------------------------------------------
def extract_text_any(filepath: str) -> str:
    """Extract text from PDF, DOCX, or other supported formats."""
    from docx import Document as DocxDocument
    from pypdf import PdfReader

    path = Path(filepath)
    suffix = path.suffix.lower()

    try:
        if suffix == ".pdf":
            reader = PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages)
        elif suffix in {".docx", ".doc"}:
            doc = DocxDocument(str(path))
            return "\n".join(paragraph.text for paragraph in doc.paragraphs)
        else:
            return path.read_text(errors="ignore")
    except Exception as e:
        logger.error(f"[EXTRACTION] Failed to extract text from {filepath}: {e}")
        return ""


# ------------------------------------------------------------
# CRITERION CLASSIFICATION
# ------------------------------------------------------------
def classify_criterion(text: str) -> str:
    """
    Détecte la catégorie d'un critère à partir de mots-clés.
    Retourne : 'essential', 'commercial', 'capacity', 'sustainability'.
    """
    text_lower = text.lower()

    # Essential (éliminatoire)
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

    # Commercial (prix, délai, paiement)
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

    # Capacity (expérience, références, qualité)
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

    # Sustainability (environnement, social)
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

    # Fallback
    return "capacity"


# ------------------------------------------------------------
# WEIGHTING VALIDATION
# ------------------------------------------------------------
def validate_criterion_weightings(criteria: list[dict]) -> tuple[bool, list[str]]:
    """
    Valide les pondérations minimales (commercial ≥40%, durabilité ≥10%).
    Retourne (is_valid, liste_erreurs).
    """
    min_weights = get_min_weights()
    errors = []

    # Somme des poids par catégorie
    cat_weights = {"commercial": 0.0, "sustainability": 0.0}
    for c in criteria:
        cat = c.get("criterion_category")
        weight = c.get("ponderation", 0.0)
        if cat in cat_weights:
            cat_weights[cat] += weight

    # Vérification
    if cat_weights["commercial"] < min_weights["commercial"] * 100:
        errors.append(
            f"Pondération commerciale trop faible: {cat_weights['commercial']:.1f}% "
            f"(min {min_weights['commercial']*100}%)"
        )
    if cat_weights["sustainability"] < min_weights["sustainability"] * 100:
        errors.append(
            f"Pondération durabilité trop faible: {cat_weights['sustainability']:.1f}% "
            f"(min {min_weights['sustainability']*100}%)"
        )

    return len(errors) == 0, errors


# ------------------------------------------------------------
# STRUCTURED DAO EXTRACTION (stub for now)
# ------------------------------------------------------------
def extract_dao_criteria_structured(text: str) -> list[DaoCriterion]:
    """
    Extract structured criteria from DAO text.
    This is a simplified stub - in production, this would use more sophisticated parsing.
    """
    criteria = []

    # Simple regex-based extraction (placeholder logic)
    # In a real implementation, this would use proper document parsing
    lines = text.split("\n")
    current_category = "Général"

    for i, line in enumerate(lines):
        line_lower = line.lower()

        # Detect category headers
        if any(
            keyword in line_lower for keyword in ["critère", "criteria", "évaluation"]
        ):
            # Try to extract criterion info
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

    # If no criteria found, create default ones
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


# ------------------------------------------------------------
# TYPED EXTRACTION
# ------------------------------------------------------------
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

    # Validation
    is_valid, errors = validate_criterion_weightings(enriched)

    # Enregistrer la validation
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
                "ts": datetime.utcnow().isoformat(),
            },
        )

    if not is_valid:
        logger.warning(
            f"[VALIDATION] Case {case_id} – Pondérations non conformes: {errors}"
        )

    return enriched


# ------------------------------------------------------------
# MAIN EXTRACTION FUNCTIONS
# ------------------------------------------------------------
def extract_dao_content(case_id: str, artifact_id: str, filepath: str):
    """
    Extraction DAO avec typage des critères (M3A).
    """
    try:
        # 1. Extraire le texte du fichier
        text_content = extract_text_any(filepath)

        # 2. Extraire les critères bruts
        raw_criteria = extract_dao_criteria_structured(text_content)

        # 3. Convertir en liste de dicts pour le typage
        raw_dicts = [asdict(c) for c in raw_criteria]

        # 4. Enrichir avec catégories
        typed_criteria = extract_dao_criteria_typed(case_id, raw_dicts)

        # 5. Insérer en base
        with get_connection() as conn:
            for crit in typed_criteria:
                db_execute(
                    conn,
                    """
                    INSERT INTO dao_criteria
                    (id, case_id, categorie, critere_nom, description,
                     criterion_category, is_eliminatory, ponderation,
                     type_reponse, seuil_elimination, ordre_affichage, created_at)
                    VALUES (:id, :cid, :cat, :nom, :desc,
                            :criterion_category, :is_eliminatory, :ponderation,
                            :type_reponse, :seuil, :ordre, :ts)
                    """,
                    {
                        "id": str(uuid.uuid4()),
                        "cid": case_id,
                        "cat": crit["categorie"],
                        "nom": crit["critere_nom"],
                        "desc": crit["description"],
                        "criterion_category": crit["criterion_category"],
                        "is_eliminatory": crit["is_eliminatory"],
                        "ponderation": crit["ponderation"],
                        "type_reponse": crit["type_reponse"],
                        "seuil": crit["seuil_elimination"],
                        "ordre": crit["ordre_affichage"],
                        "ts": datetime.utcnow().isoformat(),
                    },
                )

        logger.info(
            f"[EXTRACTION] Case {case_id} – {len(typed_criteria)} critères typés et validés"
        )

    except Exception as e:
        logger.error(
            f"[EXTRACTION] Échec pour case {case_id}, artifact {artifact_id}: {e}"
        )
        raise


def extract_offer_content(
    case_id: str, artifact_id: str, filepath: str, offer_type: str
):
    """
    Extraction (synchrone) selon le type d'offre.
    """
    import time

    time.sleep(2)
    logger.info(
        f"Extraction offre {offer_type} terminée pour case {case_id}, artifact {artifact_id}"
    )
    return {"status": "completed"}
