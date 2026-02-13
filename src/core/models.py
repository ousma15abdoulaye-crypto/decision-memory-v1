"""
Pydantic models and dataclasses for Decision Memory System.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pydantic import BaseModel


# =========================
# Pydantic Models
# =========================
class CaseCreate(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    case_type: str
    title: str
    lot: Optional[str] = None


class AnalyzeRequest(BaseModel):
    case_id: str


class DecideRequest(BaseModel):
    case_id: str
    chosen_supplier: str
    decision_reason: str
    next_action: str


# =========================
# Dataclasses
# =========================
@dataclass
class CBATemplateSchema:
    """Structure détectée d'un template CBA (adaptive)"""
    template_id: str
    template_name: str
    supplier_header_row: int
    supplier_name_row: int
    supplier_cols: List[int]
    criteria_start_row: int
    criteria_rows: List[Dict[str, Any]]
    sheets: List[str]
    meta: Dict[str, Any]


@dataclass
class DAOCriterion:
    """Critère structuré extrait du DAO"""
    categorie: str
    critere_nom: str
    description: str
    ponderation: float
    type_reponse: str
    seuil_elimination: Optional[float]
    ordre_affichage: int


@dataclass
class OfferSubtype:
    """Classification automatique du type de document d'offre"""
    subtype: str  # FINANCIAL_ONLY | TECHNICAL_ONLY | ADMIN_ONLY | COMBINED
    has_financial: bool
    has_technical: bool
    has_admin: bool
    confidence: str  # HIGH | MEDIUM | LOW


@dataclass
class SupplierPackage:
    """Agrégation de tous les documents d'un fournisseur"""
    supplier_name: str
    offer_ids: List[str]
    documents: List[dict]
    package_status: str  # COMPLETE | PARTIAL | MISSING
    has_financial: bool
    has_technical: bool
    has_admin: bool
    extracted_data: Dict[str, Any]
    missing_fields: List[str]
