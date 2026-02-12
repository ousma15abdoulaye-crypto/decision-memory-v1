"""
Couche A - Procurement References & Validation
Endpoints pour gestion des références de procurement et validation des seuils/procédures.
Constitution V2.1 : Sync only, helpers src.db
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional

router = APIRouter(prefix="/api/couche-a/references", tags=["procurement_references"])


@router.get("/validate-procedure-threshold")
def validate_procedure_threshold(
    estimated_value: float = Query(..., description="Valeur estimée en USD"),
    procedure_type: str = Query(..., description="Type de procédure: devis_unique, devis_simple, devis_formel, appel_offres_ouvert")
) -> Dict[str, Any]:
    """
    Valide que la procédure choisie est conforme au seuil estimé (Manuel SCI §4.2).
    
    Seuils Save the Children:
    - devis_unique: 0 - 100 USD (1 fournisseur)
    - devis_simple: 101 - 1000 USD (3 fournisseurs minimum)
    - devis_formel: 1001 - 10000 USD (3 fournisseurs minimum)
    - appel_offres_ouvert: >100000 USD (5 fournisseurs minimum)
    
    Returns:
        dict: {"valid": bool, "reason": str (si invalid), "recommended": str (suggestion)}
    """
    thresholds = {
        "devis_unique": (0, 100),
        "devis_simple": (101, 1000),
        "devis_formel": (1001, 10000),
        "appel_offres_ouvert": (100001, None)
    }
    
    if procedure_type not in thresholds:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid procedure type. Must be one of: {', '.join(thresholds.keys())}"
        )
    
    min_val, max_val = thresholds[procedure_type]
    
    # Validation
    if estimated_value < min_val:
        # Recommander une procédure moins stricte
        recommended = None
        if estimated_value <= 100:
            recommended = "devis_unique"
        elif estimated_value <= 1000:
            recommended = "devis_simple"
        elif estimated_value <= 10000:
            recommended = "devis_formel"
        
        return {
            "valid": False, 
            "reason": f"Valeur trop faible pour {procedure_type} (minimum: {min_val} USD)",
            "recommended": recommended
        }
    
    if max_val and estimated_value > max_val:
        # Recommander une procédure plus stricte
        recommended = None
        if estimated_value > 100000:
            recommended = "appel_offres_ouvert"
        elif estimated_value > 10000:
            recommended = "devis_formel"  # Note: il y a un gap 10k-100k dans les specs
        elif estimated_value > 1000:
            recommended = "devis_formel"
        
        return {
            "valid": False, 
            "reason": f"Valeur trop élevée pour {procedure_type} (maximum: {max_val} USD)",
            "recommended": recommended
        }
    
    return {
        "valid": True,
        "message": f"Procédure {procedure_type} valide pour montant {estimated_value} USD"
    }


@router.get("/purchase-categories")
def get_purchase_categories() -> Dict[str, Any]:
    """
    Liste des 9 catégories d'achat du Manuel SCI.
    
    Returns:
        dict: Liste des catégories avec leurs règles spécifiques
    """
    from src.db import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, code, label, is_high_risk, requires_expert, specific_rules_json
            FROM purchase_categories
            ORDER BY code
        """))
        rows = result.fetchall()
        
        categories = [
            {
                "id": row[0],
                "code": row[1],
                "label": row[2],
                "is_high_risk": row[3],
                "requires_expert": row[4],
                "specific_rules": row[5]
            }
            for row in rows
        ]
        
        return {
            "count": len(categories),
            "categories": categories
        }


@router.get("/procurement-thresholds")
def get_procurement_thresholds() -> Dict[str, Any]:
    """
    Retourne les seuils de procédure configurés.
    
    Returns:
        dict: Liste des seuils avec min/max et nombre minimum de fournisseurs
    """
    from src.db import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT procedure_type, min_amount_usd, max_amount_usd, min_suppliers, description_en, description_fr
            FROM procurement_thresholds
            ORDER BY min_amount_usd
        """))
        rows = result.fetchall()
        
        thresholds = [
            {
                "procedure_type": row[0],
                "min_amount_usd": float(row[1]) if row[1] else 0,
                "max_amount_usd": float(row[2]) if row[2] else None,
                "min_suppliers": row[3],
                "description_en": row[4],
                "description_fr": row[5]
            }
            for row in rows
        ]
        
        return {
            "count": len(thresholds),
            "thresholds": thresholds
        }
