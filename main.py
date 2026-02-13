import json
import os
import re
import uuid

# Load .env before db import (DATABASE_URL required)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure logging pour resilience patterns
from src.logging_config import configure_logging
configure_logging()

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from docx import Document
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter

from pypdf import PdfReader

from src.db import get_connection, db_execute, db_execute_one, db_fetchall, init_db_schema
from src.couche_a.routers import router as upload_router
from src.auth_router import router as auth_router
from src.ratelimit import init_rate_limit, limiter
from src.auth import CurrentUser
from src.core.config import (
    APP_TITLE, APP_VERSION, BASE_DIR, DATA_DIR, UPLOADS_DIR, OUTPUTS_DIR, 
    STATIC_DIR, INVARIANTS
)
from src.core.models import (
    CaseCreate, AnalyzeRequest, DecideRequest,
    CBATemplateSchema, DAOCriterion, OfferSubtype, SupplierPackage
)
from src.core.dependencies import (
    safe_save_upload, register_artifact, get_artifacts,
    add_memory, list_memory
)
from src.business.extraction import extract_text_from_docx, extract_text_from_pdf, extract_text_any
from src.business.offer_processor import (
    detect_offer_subtype, aggregate_supplier_packages,
    guess_supplier_name, extract_offer_data_guided
)
from src.business.templates import analyze_cba_template, fill_cba_adaptive, generate_pv_adaptive
from src.api import health, cases, documents

# ❌ REMOVED: from src.couche_a.procurement import router as procurement_router (M2-Extended)

# =========================
# Database — PostgreSQL only (schema created on startup)
# =========================
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    init_db_schema()
    yield

app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)

# Initialize rate limiting
init_rate_limit(app)

# Include routers
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(health.router)
app.include_router(cases.router)
app.include_router(documents.router)
# ❌ REMOVED: app.include_router(procurement_router) (M2-Extended)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")




# =========================
# CBA Template Analysis (ADAPTIVE)


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest):
    """
    Main analysis pipeline:
    1. Extract DAO criteria (structured)
    2. Extract offer data (DAO-guided)
    3. Generate CBA (template-adaptive)
    4. Generate PV (template-specific)
    5. Store memory (passive)
    """
    case_id = payload.case_id

    with get_connection() as conn:
        case = db_execute_one(conn, "SELECT * FROM cases WHERE id=:id", {"id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="case not found")

    # Step 1: DAO extraction
    dao_arts = get_artifacts(case_id, "dao")
    if not dao_arts:
        raise HTTPException(status_code=400, detail="Missing DAO (upload kind=dao)")

    dao_path = dao_arts[0]["path"]
    dao_text = extract_text_any(dao_path)
    dao_criteria = extract_dao_criteria_structured(dao_text)

    # Store criteria in DB
    with get_connection() as conn:
        for c in dao_criteria:
            db_execute(conn, """
                INSERT INTO dao_criteria 
                (id, case_id, categorie, critere_nom, description, ponderation, type_reponse, seuil_elimination, ordre_affichage, created_at)
                VALUES (:id, :cid, :cat, :nom, :desc, :pond, :type_reponse, :seuil, :ordre, :ts)
            """, {
                "id": str(uuid.uuid4()), "cid": case_id, "cat": c.categorie, "nom": c.critere_nom,
                "desc": c.description, "pond": c.ponderation, "type_reponse": c.type_reponse,
                "seuil": c.seuil_elimination, "ordre": c.ordre_affichage,
                "ts": datetime.utcnow().isoformat(),
            })

    # Step 2: Offers extraction (DAO-guided) + SUBTYPE DETECTION
    offer_arts = get_artifacts(case_id, "offer")
    if not offer_arts:
        raise HTTPException(status_code=400, detail="Missing OFFERS (upload kind=offer)")

    raw_offers: List[dict] = []
    for off in offer_arts:
        txt = extract_text_any(off["path"])
        supplier_name = guess_supplier_name(txt, off["filename"])
        
        # CRITIQUE: Détection du subtype (FINANCIAL_ONLY, etc.)
        subtype = detect_offer_subtype(txt, off["filename"])
        
        offer_data = extract_offer_data_guided(txt, dao_criteria)

        raw_offers.append({
            "supplier_name": supplier_name,
            "subtype": asdict(subtype),
            **offer_data,
            "source_filename": off["filename"],
            "artifact_id": off["id"]
        })

        # Store extraction in DB
        with get_connection() as conn:
            db_execute(conn, """
                INSERT INTO offer_extractions (id, case_id, artifact_id, supplier_name, extracted_data_json, missing_fields_json, created_at)
                VALUES (:id, :cid, :aid, :supplier, :extracted, :missing, :ts)
            """, {
                "id": str(uuid.uuid4()), "cid": case_id, "aid": off["id"], "supplier": supplier_name,
                "extracted": json.dumps({**offer_data, "subtype": asdict(subtype)}, ensure_ascii=False),
                "missing": json.dumps(offer_data.get("missing_fields", []), ensure_ascii=False),
                "ts": datetime.utcnow().isoformat(),
            })

    # CRITIQUE: Agrégation par fournisseur (gestion offres partielles)
    supplier_packages = aggregate_supplier_packages(raw_offers)
    
    # Conversion en format compatible avec le reste du système
    suppliers: List[dict] = []
    for pkg in supplier_packages:
        suppliers.append({
            "supplier_name": pkg.supplier_name,
            "package_status": pkg.package_status,
            "has_financial": pkg.has_financial,
            "has_technical": pkg.has_technical,
            "has_admin": pkg.has_admin,
            **pkg.extracted_data,
            "offer_ids": pkg.offer_ids,
            "document_count": len(pkg.documents)
        })

    # Memory entry avec traçabilité des décisions
    add_memory(case_id, "extraction", {
        "dao_source": dao_arts[0]["filename"],
        "offers_sources": [o["filename"] for o in offer_arts],
        "dao_criteria_count": len(dao_criteria),
        "dao_criteria": [asdict(c) for c in dao_criteria],
        "raw_offers_count": len(raw_offers),
        "supplier_packages_count": len(supplier_packages),
        "packages_summary": [
            {
                "supplier": pkg.supplier_name,
                "status": pkg.package_status,
                "subtypes": [d.get("subtype", {}).get("subtype") for d in pkg.documents]
            }
            for pkg in supplier_packages
        ],
        "offers_summary": suppliers,
        "note": "DAO-driven extraction with partial offers support. Subtype detection enabled. No scoring/ranking. Human validates."
    })

    # Step 3: Generate CBA (adaptive)
    cba_out = None
    cba_tpl = get_artifacts(case_id, "cba_template")
    if cba_tpl:
        cba_out = fill_cba_adaptive(cba_tpl[0]["path"], case_id, suppliers, dao_criteria)
        register_artifact(case_id, "output_cba", Path(cba_out).name, cba_out, 
                        meta={"template_used": cba_tpl[0]["filename"]})

    # Step 4: Generate PV (adaptive)
    pv_tpl = get_artifacts(case_id, "pv_template")
    pv_tpl_path = pv_tpl[0]["path"] if pv_tpl else None
    pv_out = generate_pv_adaptive(pv_tpl_path, case_id, case["title"], suppliers, dao_criteria, decision=None)
    register_artifact(case_id, "output_pv", Path(pv_out).name, pv_out, 
                     meta={"template_used": pv_tpl[0]["filename"] if pv_tpl else "default", "decision_included": False})

    # Statistiques et warnings
    partial_offers = [s for s in suppliers if s.get("package_status") == "PARTIAL"]
    complete_offers = [s for s in suppliers if s.get("package_status") == "COMPLETE"]
    financial_only = [s for s in suppliers if s.get("has_financial") and not s.get("has_technical")]
    
    return {
        "ok": True,
        "case_id": case_id,
        "dao_criteria_count": len(dao_criteria),
        "offers_count": len(suppliers),
        "raw_documents_count": len(raw_offers),
        "output_cba_generated": bool(cba_out),
        "output_pv_generated": True,
        "downloads": {
            "cba": f"/api/download/{case_id}/output_cba" if cba_out else None,
            "pv": f"/api/download/{case_id}/output_pv",
        },
        "package_stats": {
            "complete": len(complete_offers),
            "partial": len(partial_offers),
            "financial_only": len(financial_only)
        },
        "warnings": {
            "missing_data_count": sum(len(s.get("missing_fields", [])) for s in suppliers),
            "suppliers_with_missing_data": [s["supplier_name"] for s in suppliers if s.get("missing_fields")],
            "partial_offers_detected": len(partial_offers) > 0,
            "note": "Offres partielles gérées en mode LENIENT. Aucune pénalité automatique. Champs manquants marqués REVUE MANUELLE."
        }
    }


@app.post("/api/decide")
def decide(payload: DecideRequest):
    """Record human decision and regenerate PV"""
    case_id = payload.case_id

    with get_connection() as conn:
        case = db_execute_one(conn, "SELECT * FROM cases WHERE id=:id", {"id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="case not found")

    decision = {
        "chosen_supplier": payload.chosen_supplier.strip(),
        "decision_reason": payload.decision_reason.strip(),
        "next_action": payload.next_action.strip(),
        "decided_at": datetime.utcnow().isoformat(),
        "human_final": True,
    }
    add_memory(case_id, "decision", decision)

    # Get latest extraction data
    with get_connection() as conn:
        extractions = db_fetchall(conn, "SELECT * FROM offer_extractions WHERE case_id=:cid", {"cid": case_id})
        criteria_rows = db_fetchall(conn, "SELECT * FROM dao_criteria WHERE case_id=:cid", {"cid": case_id})

    suppliers = []
    for ext in extractions:
        data = json.loads(ext["extracted_data_json"])
        suppliers.append({
            "supplier_name": ext["supplier_name"],
            **data,
            "artifact_id": ext["artifact_id"]
        })

    dao_criteria = [
        DAOCriterion(
            categorie=r["categorie"],
            critere_nom=r["critere_nom"],
            description=r["description"] or "",
            ponderation=r["ponderation"],
            type_reponse=r["type_reponse"],
            seuil_elimination=r["seuil_elimination"],
            ordre_affichage=r["ordre_affichage"]
        )
        for r in criteria_rows
    ]

    # Regenerate PV with decision
    pv_tpl = get_artifacts(case_id, "pv_template")
    pv_tpl_path = pv_tpl[0]["path"] if pv_tpl else None
    pv_out = generate_pv_adaptive(pv_tpl_path, case_id, case["title"], suppliers, dao_criteria, decision=decision)
    register_artifact(case_id, "output_pv", Path(pv_out).name, pv_out, 
                     meta={"template_used": pv_tpl[0]["filename"] if pv_tpl else "default", "decision_included": True})

    return {
        "ok": True,
        "case_id": case_id,
        "pv_with_decision": f"/api/download/{case_id}/output_pv"
    }



# Rebuild Pydantic models to resolve forward references
try:
    CaseCreate.model_rebuild()
    AnalyzeRequest.model_rebuild()
    DecideRequest.model_rebuild()
except Exception:
    pass  # Ignore if models don't need rebuilding

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)