"""
Endpoints Procurement – Catégories, Lots, Seuils, Références
Constitution V2.1 § M2-Extended
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid

from src.db import get_connection, db_execute_one, db_execute

router = APIRouter(prefix="/api/procurement", tags=["Procurement"])


# ==================== Modèles Pydantic ====================

class CategoryCreate(BaseModel):
    code: str
    name: str
    threshold_usd: Optional[float] = None
    requires_technical_eval: bool = True
    min_suppliers: int = 3


class CategoryResponse(BaseModel):
    id: str
    code: str
    name: str
    threshold_usd: Optional[float]
    requires_technical_eval: bool
    min_suppliers: int
    created_at: str


class LotCreate(BaseModel):
    lot_number: str
    description: Optional[str] = None
    estimated_value: Optional[float] = None


class LotResponse(BaseModel):
    id: str
    case_id: str
    lot_number: str
    description: Optional[str]
    estimated_value: Optional[float]
    created_at: str


class ThresholdResponse(BaseModel):
    id: int
    procedure_type: str
    min_amount_usd: Optional[float]
    max_amount_usd: Optional[float]
    min_suppliers: Optional[int]


class ReferenceCreate(BaseModel):
    ref_type: str  # 'DAO', 'RFQ', 'RFP'
    year: int


class ReferenceResponse(BaseModel):
    id: str
    case_id: str
    ref_type: str
    ref_number: str
    year: int
    sequence: int
    created_at: str


# ==================== Stub Auth ====================
# Permet d'éviter les erreurs de dépendance manquante
def get_current_user():
    """Stub auth dependency – retourne un utilisateur fictif."""
    return {"user_id": "stub_user", "email": "stub@example.com"}


CurrentUser = Depends(get_current_user)


# ==================== Endpoints ====================

@router.post("/categories", response_model=CategoryResponse, status_code=201)
def create_category(payload: CategoryCreate, user: CurrentUser):
    """Créer une catégorie de procurement."""
    with get_connection() as conn:
        # Vérifier unicité code
        existing = db_execute_one(conn, "SELECT id FROM procurement_categories WHERE code=:code", {"code": payload.code})
        if existing:
            raise HTTPException(409, f"Category code '{payload.code}' already exists")
        
        cat_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        db_execute(conn, """
            INSERT INTO procurement_categories (id, code, name, threshold_usd, requires_technical_eval, min_suppliers, created_at)
            VALUES (:id, :code, :name, :threshold, :req, :min, :ts)
        """, {
            "id": cat_id,
            "code": payload.code,
            "name": payload.name,
            "threshold": payload.threshold_usd,
            "req": payload.requires_technical_eval,
            "min": payload.min_suppliers,
            "ts": now
        })
    
    return CategoryResponse(
        id=cat_id,
        code=payload.code,
        name=payload.name,
        threshold_usd=payload.threshold_usd,
        requires_technical_eval=payload.requires_technical_eval,
        min_suppliers=payload.min_suppliers,
        created_at=now
    )


@router.get("/categories", response_model=List[CategoryResponse])
def list_categories(user: CurrentUser):
    """Lister toutes les catégories."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, code, name, threshold_usd, requires_technical_eval, min_suppliers, created_at FROM procurement_categories ORDER BY code"
        ).fetchall()
    
    return [
        CategoryResponse(
            id=r[0], code=r[1], name=r[2], threshold_usd=r[3],
            requires_technical_eval=r[4], min_suppliers=r[5], created_at=r[6]
        )
        for r in rows
    ]


@router.post("/cases/{case_id}/lots", response_model=LotResponse, status_code=201)
def create_lot(case_id: str, payload: LotCreate, user: CurrentUser):
    """Créer un lot pour un case."""
    with get_connection() as conn:
        # Vérifier case existe
        case = db_execute_one(conn, "SELECT id FROM cases WHERE id=:id", {"id": case_id})
        if not case:
            raise HTTPException(404, f"Case '{case_id}' not found")
        
        # Vérifier lot number unique pour cette case
        existing = db_execute_one(conn, 
            "SELECT id FROM lots WHERE case_id=:cid AND lot_number=:num", 
            {"cid": case_id, "num": payload.lot_number}
        )
        if existing:
            raise HTTPException(409, f"Lot number '{payload.lot_number}' already exists for this case")
        
        lot_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        db_execute(conn, """
            INSERT INTO lots (id, case_id, lot_number, description, estimated_value, created_at)
            VALUES (:id, :cid, :num, :desc, :val, :ts)
        """, {
            "id": lot_id,
            "cid": case_id,
            "num": payload.lot_number,
            "desc": payload.description,
            "val": payload.estimated_value,
            "ts": now
        })
    
    return LotResponse(
        id=lot_id,
        case_id=case_id,
        lot_number=payload.lot_number,
        description=payload.description,
        estimated_value=payload.estimated_value,
        created_at=now
    )


@router.get("/cases/{case_id}/lots", response_model=List[LotResponse])
def list_lots(case_id: str, user: CurrentUser):
    """Lister les lots d'un case."""
    with get_connection() as conn:
        # Vérifier case existe
        case = db_execute_one(conn, "SELECT id FROM cases WHERE id=:id", {"id": case_id})
        if not case:
            raise HTTPException(404, f"Case '{case_id}' not found")
        
        rows = conn.execute(
            "SELECT id, case_id, lot_number, description, estimated_value, created_at FROM lots WHERE case_id=:cid ORDER BY lot_number",
            {"cid": case_id}
        ).fetchall()
    
    return [
        LotResponse(
            id=r[0], case_id=r[1], lot_number=r[2], description=r[3],
            estimated_value=r[4], created_at=r[5]
        )
        for r in rows
    ]


@router.get("/thresholds", response_model=List[ThresholdResponse])
def list_thresholds(user: CurrentUser):
    """Lister les seuils de procédure."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, procedure_type, min_amount_usd, max_amount_usd, min_suppliers FROM procurement_thresholds ORDER BY min_amount_usd"
        ).fetchall()
    
    return [
        ThresholdResponse(
            id=r[0], procedure_type=r[1], min_amount_usd=r[2],
            max_amount_usd=r[3], min_suppliers=r[4]
        )
        for r in rows
    ]


@router.post("/cases/{case_id}/references", response_model=ReferenceResponse, status_code=201)
def create_reference(case_id: str, payload: ReferenceCreate, user: CurrentUser):
    """Générer une référence procurement pour un case (DAO-2026-001, RFQ-2026-042, etc.)."""
    with get_connection() as conn:
        # Vérifier case existe
        case = db_execute_one(conn, "SELECT id FROM cases WHERE id=:id", {"id": case_id})
        if not case:
            raise HTTPException(404, f"Case '{case_id}' not found")
        
        # Vérifier qu'il n'y a pas déjà une référence pour ce case
        existing = db_execute_one(conn, "SELECT id FROM procurement_references WHERE case_id=:cid", {"cid": case_id})
        if existing:
            raise HTTPException(409, f"Reference already exists for case '{case_id}'")
        
        # Calculer le prochain numéro de séquence pour ce type et cette année
        seq_row = db_execute_one(conn, 
            "SELECT COALESCE(MAX(sequence), 0) + 1 FROM procurement_references WHERE ref_type=:type AND year=:year",
            {"type": payload.ref_type, "year": payload.year}
        )
        sequence = seq_row[0] if seq_row else 1
        
        # Générer le ref_number
        ref_number = f"{payload.ref_type}-{payload.year}-{sequence:03d}"
        
        ref_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        db_execute(conn, """
            INSERT INTO procurement_references (id, case_id, ref_type, ref_number, year, sequence, created_at)
            VALUES (:id, :cid, :type, :num, :year, :seq, :ts)
        """, {
            "id": ref_id,
            "cid": case_id,
            "type": payload.ref_type,
            "num": ref_number,
            "year": payload.year,
            "seq": sequence,
            "ts": now
        })
    
    return ReferenceResponse(
        id=ref_id,
        case_id=case_id,
        ref_type=payload.ref_type,
        ref_number=ref_number,
        year=payload.year,
        sequence=sequence,
        created_at=now
    )


@router.get("/cases/{case_id}/references", response_model=ReferenceResponse)
def get_reference(case_id: str, user: CurrentUser):
    """Récupérer la référence procurement d'un case."""
    with get_connection() as conn:
        row = db_execute_one(conn, 
            "SELECT id, case_id, ref_type, ref_number, year, sequence, created_at FROM procurement_references WHERE case_id=:cid",
            {"cid": case_id}
        )
        if not row:
            raise HTTPException(404, f"No reference found for case '{case_id}'")
    
    return ReferenceResponse(
        id=row[0], case_id=row[1], ref_type=row[2], ref_number=row[3],
        year=row[4], sequence=row[5], created_at=row[6]
    )
