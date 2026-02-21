"""
src/couche_a/criteria/service.py

Service criteria — psycopg v3 raw — DMS V3.3.2

Règles absolues :
  - import psycopg (v3) — jamais psycopg2
  - Toutes les requêtes SQL paramétrées avec %s
  - Aucun ORM
  - org_id sur toutes les requêtes SELECT / UPDATE / DELETE
  - Aucun import depuis couche_b
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional

import psycopg          # v3 — jamais psycopg2
import psycopg.errors

from src.db.connection import get_db_cursor


# ─────────────────────────────────────────────────────────────
# SCHÉMAS DE DONNÉES
# ─────────────────────────────────────────────────────────────

@dataclass
class CriterionRecord:
    """Représentation d'un critère tel que stocké en DB."""
    id: str
    case_id: str
    org_id: str
    label: str
    category: str
    weight_pct: float
    min_weight_pct: Optional[float]
    is_essential: bool
    threshold: Optional[float]
    scoring_method: str
    canonical_item_id: Optional[str]
    currency: str
    description: Optional[str]
    created_at: str


@dataclass
class CriterionCreateInput:
    """Données d'entrée validées par le router avant d'arriver ici."""
    case_id: str
    org_id: str
    label: str
    category: str
    weight_pct: float
    scoring_method: str
    is_essential: bool = False
    min_weight_pct: Optional[float] = None
    threshold: Optional[float] = None
    canonical_item_id: Optional[str] = None
    currency: str = "XOF"          # Règle R4 — ADR-0002 SR-6
    description: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# OPÉRATIONS
# ─────────────────────────────────────────────────────────────

def create_criterion(inp: CriterionCreateInput) -> CriterionRecord:
    """
    Insère un critère en DB.

    Règle R4 : currency défaut XOF.
    Règle R6 : canonical_item_id optionnel avant M-NORMALISATION-ITEMS.

    Lève :
        psycopg.errors.ForeignKeyViolation       — case_id inexistant
        psycopg.errors.CheckViolation            — weight_pct hors bornes
        psycopg.errors.InvalidTextRepresentation — enum invalide
    """
    criterion_id = str(uuid.uuid4())

    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO criteria (
                id,
                case_id,
                org_id,
                label,
                category,
                weight_pct,
                min_weight_pct,
                is_essential,
                threshold,
                scoring_method,
                canonical_item_id,
                currency,
                description
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s
            )
            RETURNING
                id,
                case_id,
                org_id,
                label,
                category,
                weight_pct,
                min_weight_pct,
                is_essential,
                threshold,
                scoring_method,
                canonical_item_id,
                currency,
                description,
                created_at::TEXT
            """,
            (
                criterion_id,
                inp.case_id,
                inp.org_id,
                inp.label,
                inp.category,
                inp.weight_pct,
                inp.min_weight_pct,
                inp.is_essential,
                inp.threshold,
                inp.scoring_method,
                inp.canonical_item_id,
                inp.currency,
                inp.description,
            ),
        )
        row = cur.fetchone()

    return _row_to_record(row)


def get_criteria_by_case(case_id: str, org_id: str) -> list[CriterionRecord]:
    """
    Retourne tous les critères d'un dossier pour une org donnée,
    triés par date de création ASC.

    Règle R7 : org_id obligatoire — isolation multi-tenant.
    """
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT
                id,
                case_id,
                org_id,
                label,
                category,
                weight_pct,
                min_weight_pct,
                is_essential,
                threshold,
                scoring_method,
                canonical_item_id,
                currency,
                description,
                created_at::TEXT
            FROM criteria
            WHERE case_id = %s
              AND org_id  = %s
            ORDER BY created_at ASC
            """,
            (case_id, org_id),
        )
        rows = cur.fetchall()

    return [_row_to_record(r) for r in rows]


def get_criterion_by_id(
    criterion_id: str,
    org_id: str,
) -> Optional[CriterionRecord]:
    """
    Retourne un critère par son id, filtré par org_id.
    Retourne None si non trouvé ou si org_id ne correspond pas.

    Règle R7 : org_id obligatoire — pas de fuite inter-org.
    """
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT
                id,
                case_id,
                org_id,
                label,
                category,
                weight_pct,
                min_weight_pct,
                is_essential,
                threshold,
                scoring_method,
                canonical_item_id,
                currency,
                description,
                created_at::TEXT
            FROM criteria
            WHERE id     = %s
              AND org_id = %s
            """,
            (criterion_id, org_id),
        )
        row = cur.fetchone()

    return _row_to_record(row) if row else None


def delete_criterion(criterion_id: str, org_id: str) -> bool:
    """Suppression autorisée uniquement si le dossier parent est en 'draft'."""
    with get_db_cursor() as cur:
        cur.execute(
            """
            DELETE FROM criteria
            WHERE id     = %s
              AND org_id = %s
              AND case_id IN (
                  SELECT id FROM cases WHERE status = 'draft'
              )
            """,
            (criterion_id, org_id),
        )
        return cur.rowcount > 0


def get_weight_sum(case_id: str, org_id: str) -> float:
    """
    Retourne la somme des weight_pct des critères NON essentiels
    d'un dossier pour une org donnée.

    Règle R1 : la somme doit être comprise entre 99.99 et 100.01
    quand case.status = 'evaluation'. Ce service expose la valeur
    brute — la validation métier complète est dans validate_weight_sum
    et dans le trigger DEFERRED en DB.

    Retourne 0.0 si aucun critère non-essentiel n'existe.
    """
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(SUM(weight_pct), 0.0)
            FROM criteria
            WHERE case_id      = %s
              AND org_id       = %s
              AND is_essential = FALSE
            """,
            (case_id, org_id),
        )
        row = cur.fetchone()

    # dict_row : la colonne COALESCE retourne la clé 'coalesce'
    if row is None:
        return 0.0
    val = next(iter(row.values()))
    return float(val) if val is not None else 0.0


def validate_weight_sum(case_id: str, org_id: str) -> dict:
    """
    Valide que la somme des poids non-essentiels respecte la Règle R1.

    Règle R1 Constitution V3.3.2 :
        |somme - 100| <= 0.01%

    Retourne un dict structuré utilisable par le router et les tests.
    Le trigger DB est le verrou final — cette fonction est le signal
    préventif avant COMMIT.
    """
    total = get_weight_sum(case_id, org_id)
    delta = abs(total - 100.0)
    is_valid = delta <= 0.01

    return {
        "case_id":  case_id,
        "org_id":   org_id,
        "total":    total,
        "delta":    delta,
        "is_valid": is_valid,
        "status":   "ok" if is_valid else "invalid",
        "message":  None if is_valid else (
            f"Somme poids non-essentiels = {total:.2f}%. "
            f"Doit etre 100%. Delta : {delta:.2f}%."
        ),
    }


# ─────────────────────────────────────────────────────────────
# HELPER INTERNE — MAPPING ROW → DATACLASS
# ─────────────────────────────────────────────────────────────

def _row_to_record(row: dict) -> CriterionRecord:
    """
    Mappe un dict psycopg v3 (dict_row) vers CriterionRecord.
    get_db_cursor() utilise row_factory=dict_row — accès par clé.
    """
    return CriterionRecord(
        id=str(row["id"]),
        case_id=str(row["case_id"]),
        org_id=str(row["org_id"]),
        label=str(row["label"]),
        category=str(row["category"]),
        weight_pct=float(row["weight_pct"]),
        min_weight_pct=float(row["min_weight_pct"]) if row["min_weight_pct"] is not None else None,
        is_essential=bool(row["is_essential"]),
        threshold=float(row["threshold"]) if row["threshold"] is not None else None,
        scoring_method=str(row["scoring_method"]),
        canonical_item_id=str(row["canonical_item_id"]) if row["canonical_item_id"] is not None else None,
        currency=str(row["currency"]),
        description=str(row["description"]) if row["description"] is not None else None,
        created_at=str(row["created_at"]),
    )
