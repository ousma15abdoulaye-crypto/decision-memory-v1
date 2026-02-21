"""
src/couche_a/criteria/router.py

Router FastAPI — criteria — DMS V3.3.2

Règles absolues :
  - Pydantic v2 — validation entrées/sorties
  - psycopg.errors — interception exceptions DB typées
  - org_id en query parameter obligatoire sur GET / DELETE
  - case_id vient du path — jamais du body
  - Aucune logique DB directe — service.py exclusivement
  - Aucun import depuis couche_b
"""
from __future__ import annotations

from typing import Optional

import psycopg.errors
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from src.couche_a.criteria.service import (
    CriterionCreateInput,
    CriterionRecord,
    create_criterion,
    delete_criterion,
    get_criteria_by_case,
    get_criterion_by_id,
    validate_weight_sum,
)

router = APIRouter(
    prefix="/cases/{case_id}/criteria",
    tags=["criteria"],
)


# ─────────────────────────────────────────────────────────────
# VALEURS ENUM — ISSUES DE P0 (vérification DB)
# ─────────────────────────────────────────────────────────────

_CATEGORY_VALUES: set[str] = {
    "commercial",
    "capacity",
    "sustainability",
    "essential",
}

_SCORING_METHOD_VALUES: set[str] = {
    "formula",
    "points_scale",
    "judgment",
    "paliers",
}


# ─────────────────────────────────────────────────────────────
# SCHÉMAS PYDANTIC v2
# ─────────────────────────────────────────────────────────────

class CriterionCreateRequest(BaseModel):
    """
    Body du POST /cases/{case_id}/criteria.
    case_id absent — vient du path.
    org_id présent — isolation multi-tenant Règle R7.
    currency défaut XOF — Règle R4 ADR-0002 SR-6.
    """
    org_id: str
    label: str = Field(min_length=1, max_length=500)
    category: str
    weight_pct: float = Field(ge=0.0, le=100.0)
    scoring_method: str
    is_essential: bool = False
    min_weight_pct: Optional[float] = Field(default=None, ge=0.0)
    threshold: Optional[float] = None
    canonical_item_id: Optional[str] = None
    currency: str = "XOF"
    description: Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in _CATEGORY_VALUES:
            raise ValueError(
                f"category doit être l'une de : {sorted(_CATEGORY_VALUES)}"
            )
        return v

    @field_validator("scoring_method")
    @classmethod
    def validate_scoring_method(cls, v: str) -> str:
        if v not in _SCORING_METHOD_VALUES:
            raise ValueError(
                f"scoring_method doit être l'une de : {sorted(_SCORING_METHOD_VALUES)}"
            )
        return v


class CriterionResponse(BaseModel):
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


class WeightSumResponse(BaseModel):
    case_id: str
    org_id: str
    total: float
    delta: float
    is_valid: bool
    status: str
    message: Optional[str]


# ─────────────────────────────────────────────────────────────
# ENDPOINTS
# Ordre de déclaration non négociable :
#   POST "" → GET "" → GET "/validate/weights" → GET "/{id}" → DELETE "/{id}"
# ─────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=CriterionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un critère d'évaluation",
)
def create_criterion_endpoint(
    case_id: str,
    body: CriterionCreateRequest,
):
    """
    Crée un critère pour le dossier AO identifié par case_id (path).
    Règle R4 : currency défaut XOF.
    Règle R7 : org_id dans le body — isolation multi-tenant.
    """
    try:
        record = create_criterion(
            CriterionCreateInput(
                case_id=case_id,
                org_id=body.org_id,
                label=body.label,
                category=body.category,
                weight_pct=body.weight_pct,
                scoring_method=body.scoring_method,
                is_essential=body.is_essential,
                min_weight_pct=body.min_weight_pct,
                threshold=body.threshold,
                canonical_item_id=body.canonical_item_id,
                currency=body.currency,
                description=body.description,
            )
        )
    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="case_id introuvable",
        )
    except psycopg.errors.CheckViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Violation contrainte : {exc}",
        )
    except psycopg.errors.InvalidTextRepresentation as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Valeur enum invalide : {exc}",
        )

    return _record_to_response(record)


@router.get(
    "",
    response_model=list[CriterionResponse],
    summary="Lister les critères d'un dossier",
)
def list_criteria_by_case(
    case_id: str,
    org_id: str = Query(..., description="Identifiant organisation — obligatoire"),
):
    """
    Retourne tous les critères du dossier triés par created_at ASC.
    Règle R7 : filtre org_id — aucune fuite inter-org.
    """
    records = get_criteria_by_case(case_id, org_id)
    return [_record_to_response(r) for r in records]


@router.get(
    "/validate/weights",
    response_model=WeightSumResponse,
    summary="Valider la somme des poids non-essentiels",
)
def validate_weights_endpoint(
    case_id: str,
    org_id: str = Query(..., description="Identifiant organisation — obligatoire"),
):
    """
    Retourne la somme des poids NON essentiels et son statut R1.
    Règle R1 : somme valide si |total - 100| <= 0.01%.
    Outil préventif — le trigger DEFERRED reste le verrou final.
    """
    result = validate_weight_sum(case_id, org_id)
    return WeightSumResponse(**result)


@router.get(
    "/{criterion_id}",
    response_model=CriterionResponse,
    summary="Récupérer un critère par son id",
)
def get_criterion_endpoint(
    case_id: str,
    criterion_id: str,
    org_id: str = Query(..., description="Identifiant organisation — obligatoire"),
):
    """
    Retourne un critère par son id.
    Règle R7 : 404 si critère hors org ou inexistant.
    case_id présent dans la signature pour cohérence du path
    mais le filtre d'isolation repose sur criterion_id + org_id.
    """
    record = get_criterion_by_id(criterion_id, org_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Critère introuvable",
        )
    return _record_to_response(record)


@router.delete(
    "/{criterion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un critère",
)
def delete_criterion_endpoint(
    case_id: str,
    criterion_id: str,
    org_id: str = Query(..., description="Identifiant organisation — obligatoire"),
):
    """
    Supprime un critère.
    Règle R7 : 404 si critère hors org ou inexistant.
    Règle gouvernance : suppression autorisée uniquement si dossier en 'draft'
    (enforced dans service.delete_criterion).
    """
    deleted = delete_criterion(criterion_id, org_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Critère introuvable",
        )


# ─────────────────────────────────────────────────────────────
# HELPER INTERNE
# ─────────────────────────────────────────────────────────────

def _record_to_response(r: CriterionRecord) -> CriterionResponse:
    return CriterionResponse(
        id=r.id,
        case_id=r.case_id,
        org_id=r.org_id,
        label=r.label,
        category=r.category,
        weight_pct=r.weight_pct,
        min_weight_pct=r.min_weight_pct,
        is_essential=r.is_essential,
        threshold=r.threshold,
        scoring_method=r.scoring_method,
        canonical_item_id=r.canonical_item_id,
        currency=r.currency,
        description=r.description,
        created_at=r.created_at,
    )
