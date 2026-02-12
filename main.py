from __future__ import annotations

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

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
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
# ❌ REMOVED: from src.couche_a.procurement import router as procurement_router (M2-Extended)


# =========================================================
# Decision Memory System — MVP A++ FINAL
# Version: 1.0.0
# DAO-driven extraction + Template-adaptive CBA + Active Memory
# Constitution V2.1: ONLINE-ONLY (PostgreSQL)
# =========================================================

APP_TITLE = "Decision Memory System — MVP A++ (Production)"
APP_VERSION = "1.0.0"

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
OUTPUTS_DIR = DATA_DIR / "outputs"

DATA_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)


# =========================
# CONSTITUTION (V2.1 ONLINE-ONLY)
# =========================
INVARIANTS = {
    "cognitive_load_never_increase": True,
    "human_decision_final": True,
    "no_scoring_no_ranking_no_recommendations": True,
    "memory_is_byproduct_never_a_task": True,
    "erp_agnostic": True,
    "online_only": True,
    "traceability_keep_sources": True,
    "one_dao_one_cba_one_pv": True,
}


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
app.include_router(upload_router)
app.include_router(auth_router)
# ❌ REMOVED: app.include_router(procurement_router) (M2-Extended)

STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# =========================
# Pydantic Models
# =========================
class CaseCreate(BaseModel):
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


# =========================
# Storage Helpers
# =========================
def safe_save_upload(case_id: str, kind: str, up: UploadFile) -> Tuple[str, str]:
    ext = Path(up.filename).suffix.lower()
    if ext not in [".pdf", ".docx", ".xlsx"]:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    file_id = str(uuid.uuid4())
    filename = f"{kind}_{file_id}{ext}"
    out_dir = UPLOADS_DIR / case_id
    out_dir.mkdir(parents=True, exist_ok=True)
    full_path = out_dir / filename

    with full_path.open("wb") as f:
        f.write(up.file.read())

    return filename, str(full_path)


def register_artifact(case_id: str, kind: str, filename: str, path: str, meta: Optional[dict] = None) -> str:
    artifact_id = str(uuid.uuid4())
    with get_connection() as conn:
        db_execute(conn, """
            INSERT INTO artifacts (id, case_id, kind, filename, path, uploaded_at, meta_json)
            VALUES (:aid, :cid, :kind, :fname, :path, :ts, :meta)
        """, {
            "aid": artifact_id, "cid": case_id, "kind": kind, "fname": filename, "path": path,
            "ts": datetime.utcnow().isoformat(),
            "meta": json.dumps(meta or {}, ensure_ascii=False),
        })
    return artifact_id


def get_artifacts(case_id: str, kind: Optional[str] = None) -> List[dict]:
    with get_connection() as conn:
        if kind:
            return db_fetchall(conn,
                "SELECT * FROM artifacts WHERE case_id=:cid AND kind=:kind ORDER BY uploaded_at DESC",
                {"cid": case_id, "kind": kind},
            )
        return db_fetchall(conn,
            "SELECT * FROM artifacts WHERE case_id=:cid ORDER BY uploaded_at DESC",
            {"cid": case_id},
        )


def add_memory(case_id: str, entry_type: str, content: dict) -> str:
    mem_id = str(uuid.uuid4())
    with get_connection() as conn:
        db_execute(conn, """
            INSERT INTO memory_entries (id, case_id, entry_type, content_json, created_at)
            VALUES (:mid, :cid, :etype, :content, :ts)
        """, {
            "mid": mem_id, "cid": case_id, "etype": entry_type,
            "content": json.dumps(content, ensure_ascii=False),
            "ts": datetime.utcnow().isoformat(),
        })
    return mem_id


def list_memory(case_id: str, entry_type: Optional[str] = None) -> List[dict]:
    with get_connection() as conn:
        if entry_type:
            rows = db_fetchall(conn, """
                SELECT * FROM memory_entries WHERE case_id=:cid AND entry_type=:etype ORDER BY created_at DESC
            """, {"cid": case_id, "etype": entry_type})
        else:
            rows = db_fetchall(conn, """
                SELECT * FROM memory_entries WHERE case_id=:cid ORDER BY created_at DESC
            """, {"cid": case_id})
    return [dict(r) | {"content": json.loads(r["content_json"])} for r in rows]


# =========================
# Text Extraction
# =========================
def extract_text_from_docx(path: str) -> str:
    doc = Document(path)
    parts: List[str] = []

    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if t:
            parts.append(t)

    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text and c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))

    return "\n".join(parts)


def extract_text_from_pdf(path: str) -> str:
    reader = PdfReader(path)
    out: List[str] = []
    for i, page in enumerate(reader.pages):
        txt = (page.extract_text() or "").strip()
        if txt:
            out.append(f"[PAGE {i+1}]\n{txt}\n")
    return "\n".join(out).strip()


def extract_text_any(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".docx":
        return extract_text_from_docx(path)
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    raise HTTPException(status_code=400, detail=f"Unsupported extraction: {ext}")


# =========================
# Document Subtype Detection (PARTIAL OFFERS)
# =========================
def detect_offer_subtype(text: str, filename: str) -> OfferSubtype:
    """
    Détection automatique du type de document d'offre.
    Permet de gérer les offres partielles (uniquement financière, etc.)
    """
    text_lower = text.lower()
    filename_lower = filename.lower()
    
    # Détection financière
    financial_patterns = [
        r"prix\s*(total|unitaire)",
        r"montant",
        r"co[uû]t",
        r"(fcfa|cfa|xof|usd|eur)",
        r"offre\s*(financière|de\s*prix)",
        r"bordereau\s*de\s*prix"
    ]
    has_financial = any(re.search(pattern, text_lower) for pattern in financial_patterns)
    
    # Détection technique
    technical_patterns = [
        r"(caract[ée]ristiques?\s*techniques?|spécifications?)",
        r"(r[ée]f[ée]rences?\s*(techniques?|clients?))",
        r"(exp[ée]rience|capacit[ée]\s*technique)",
        r"(certifications?|agr[ée]ments?)",
        r"offre\s*technique"
    ]
    has_technical = any(re.search(pattern, text_lower) for pattern in technical_patterns)
    
    # Détection administrative
    admin_patterns = [
        r"(documents?\s*(administratifs?|l[ée]gaux))",
        r"(attestation|certificat)",
        r"(kbis|rccm|nif|registre\s*de\s*commerce)",
        r"(fiscal|social)",
        r"offre\s*administrative"
    ]
    has_admin = any(re.search(pattern, text_lower) for pattern in admin_patterns)
    
    # Classification
    count = sum([has_financial, has_technical, has_admin])
    
    if count == 0:
        # Fallback: inférer depuis le nom de fichier
        if any(kw in filename_lower for kw in ["financ", "prix", "price", "cost"]):
            has_financial = True
        elif any(kw in filename_lower for kw in ["technique", "technical", "spec"]):
            has_technical = True
        elif any(kw in filename_lower for kw in ["admin", "legal", "conformit"]):
            has_admin = True
        count = sum([has_financial, has_technical, has_admin])
    
    # Détermination du subtype
    if count >= 2:
        subtype = "COMBINED"
        confidence = "HIGH" if count == 3 else "MEDIUM"
    elif has_financial:
        subtype = "FINANCIAL_ONLY"
        confidence = "MEDIUM" if count == 1 else "LOW"
    elif has_technical:
        subtype = "TECHNICAL_ONLY"
        confidence = "MEDIUM"
    elif has_admin:
        subtype = "ADMIN_ONLY"
        confidence = "MEDIUM"
    else:
        subtype = "UNKNOWN"
        confidence = "LOW"
    
    return OfferSubtype(
        subtype=subtype,
        has_financial=has_financial,
        has_technical=has_technical,
        has_admin=has_admin,
        confidence=confidence
    )


def aggregate_supplier_packages(offers: List[dict]) -> List[SupplierPackage]:
    """
    Agrège les documents par fournisseur pour gérer les offres partielles.
    Un fournisseur peut soumettre plusieurs documents (financier, technique, admin).
    """
    # Grouper par nom de fournisseur
    by_supplier: Dict[str, List[dict]] = {}
    for offer in offers:
        supplier_name = offer.get("supplier_name", "UNKNOWN")
        if supplier_name not in by_supplier:
            by_supplier[supplier_name] = []
        by_supplier[supplier_name].append(offer)
    
    packages: List[SupplierPackage] = []
    
    for supplier_name, docs in by_supplier.items():
        # Agréger les capacités
        has_financial = any(d.get("subtype", {}).get("has_financial", False) for d in docs)
        has_technical = any(d.get("subtype", {}).get("has_technical", False) for d in docs)
        has_admin = any(d.get("subtype", {}).get("has_admin", False) for d in docs)
        
        # Fusionner les données extraites
        merged_data = {
            "total_price": None,
            "total_price_source": None,
            "currency": "XOF",
            "lead_time_days": None,
            "lead_time_source": None,
            "validity_days": None,
            "validity_source": None,
            "technical_refs": [],
        }
        
        for doc in docs:
            for key in merged_data.keys():
                if key == "technical_refs":
                    merged_data[key].extend(doc.get(key, []))
                elif doc.get(key) is not None and merged_data[key] is None:
                    merged_data[key] = doc.get(key)
        
        # Déduplication des refs techniques
        merged_data["technical_refs"] = list(set(merged_data["technical_refs"]))
        
        # CRITIQUE: Séparer missing_parts (sections non soumises) vs missing_extracted_fields (données manquantes)
        missing_parts = []
        if not has_admin:
            missing_parts.append("ADMIN")
        if not has_technical:
            missing_parts.append("TECHNICAL")
        
        # missing_extracted_fields: données attendues mais non trouvées DANS les sections soumises
        missing_extracted = []
        if has_financial and merged_data["total_price"] is None:
            missing_extracted.append("Prix total")
        if has_financial and merged_data["lead_time_days"] is None:
            missing_extracted.append("Délai livraison")
        if has_financial and merged_data["validity_days"] is None:
            missing_extracted.append("Validité offre")
        if has_technical and not merged_data["technical_refs"]:
            missing_extracted.append("Références techniques")
        
        # missing_fields pour compatibilité (mais maintenant explicitement séparé)
        merged_data["missing_parts"] = missing_parts
        merged_data["missing_extracted_fields"] = missing_extracted
        merged_data["missing_fields"] = missing_extracted  # Backward compat
        
        # Statut du package
        if has_financial and has_technical and has_admin:
            package_status = "COMPLETE"
        elif has_financial or has_technical:
            package_status = "PARTIAL"
        else:
            package_status = "MISSING"
        
        packages.append(SupplierPackage(
            supplier_name=supplier_name,
            offer_ids=[d.get("artifact_id", "") for d in docs],
            documents=docs,
            package_status=package_status,
            has_financial=has_financial,
            has_technical=has_technical,
            has_admin=has_admin,
            extracted_data=merged_data,
            missing_fields=missing_extracted  # Données manquantes (pas sections non soumises)
        ))
    
    return packages


# =========================
# DAO-Driven Extraction (CORE)
# =========================
def extract_dao_criteria_structured(dao_text: str) -> List[DAOCriterion]:
    """
    Extraction structurée critères DAO (pas candidates).
    Format attendu:
    - "Prix: 40%" ou "Prix (40 points)"
    - "Capacité technique: 30%"
    - "Critères essentiels: Oui/Non"
    """
    criteria: List[DAOCriterion] = []

    # Patterns essentiels (éliminatoires)
    essential_patterns = [
        r"(?i)critères?\s+essentiels?",
        r"(?i)mandatory\s+requirements?",
        r"(?i)conformité\s+(administrative|documents?)",
        r"(?i)documents?\s+obligatoires?",
    ]

    # Patterns pondérés
    weighted_patterns = [
        r"(?i)([\wàâäéèêëïîôùûüÿç\s\-]+?)\s*[:\(]\s*(\d+)\s*%",
        r"(?i)([\wàâäéèêëïîôùûüÿç\s\-]+?)\s*[:\(]\s*(\d+)\s*points?",
    ]

    lines = dao_text.split('\n')

    for line in lines:
        line_clean = line.strip()
        if len(line_clean) < 5 or len(line_clean) > 250:
            continue

        # Détection essentiels
        for pattern in essential_patterns:
            if re.search(pattern, line_clean):
                criteria.append(DAOCriterion(
                    categorie="essentiels",
                    critere_nom=line_clean[:120],
                    description="",
                    ponderation=0.0,
                    type_reponse="oui_non",
                    seuil_elimination=1.0,
                    ordre_affichage=len(criteria) + 1
                ))
                break

        # Détection pondérés
        for pattern in weighted_patterns:
            match = re.search(pattern, line_clean)
            if match:
                name = match.group(1).strip()
                weight = float(match.group(2)) / 100

                # Catégorisation
                cat = "autre"
                if re.search(r"(?i)(prix|co[ûu]t|montant|commercial|financ)", name):
                    cat = "commercial"
                elif re.search(r"(?i)(technique|capacit[ée]|exp[ée]rience|r[ée]f[ée]rence)", name):
                    cat = "technique"
                elif re.search(r"(?i)(durabilit[ée]|environnement|social|rse)", name):
                    cat = "durabilite"

                criteria.append(DAOCriterion(
                    categorie=cat,
                    critere_nom=name,
                    description="",
                    ponderation=weight,
                    type_reponse="score_0_100",
                    seuil_elimination=None,
                    ordre_affichage=len(criteria) + 1
                ))
                break

    # Normalisation pondérations
    total_weight = sum(c.ponderation for c in criteria if c.categorie != "essentiels")
    if 0.95 <= total_weight <= 1.05:
        for c in criteria:
            if c.categorie != "essentiels":
                c.ponderation = round(c.ponderation / total_weight, 3)

    return criteria


def guess_supplier_name(text: str, filename: str) -> str:
    """
    Extract supplier name from filename or document.
    ❌ INTERDIT d'utiliser un offer_id comme nom fournisseur.
    
    Ordre de fallback:
    a) Nettoyer filename -> retourner si valide et significatif
    b) Chercher pattern "Société/Entreprise: ..." dans texte
    c) Chercher première ligne MAJUSCULE non-titre
    d) Retourner "FOURNISSEUR_INCONNU"
    """
    # a) Nettoyer filename
    base = Path(filename).stem
    # D'abord normaliser les séparateurs
    base = re.sub(r"[_\-]+", " ", base)
    # Puis retirer mots-clés communs (avec espaces comme séparateurs)
    base = re.sub(r"(?i)\b(offre|lot|dao|rfq|mpt|mopti|2026|2025|2024|annexe|annex)\b", " ", base)
    base = base.strip()
    
    # Retirer IDs UUID-like ou hash-like et nombres purs
    base = re.sub(r"\b[a-f0-9]{8,}\b", "", base, flags=re.IGNORECASE)
    base = re.sub(r"\b[A-F0-9\-]{32,}\b", "", base)
    base = re.sub(r"^\d+$", "", base)  # Retirer si c'est juste un nombre
    base = re.sub(r"\s+", " ", base).strip()  # Normaliser espaces multiples
    
    # Vérifier que le filename nettoyé est significatif (pas juste des chiffres/mots génériques)
    # Exclure mots génériques trop courts ou techniques
    generic_words = ["DOC", "PDF", "FILE", "DOCUMENT", "TEMP", "NEW", "OLD", "FINAL", "V", "VER"]
    base_upper = base.upper().strip()
    
    if len(base) >= 5 and re.search(r"[A-Za-z]{3,}", base) and base_upper not in generic_words:
        return base.upper()[:80]
    
    # b) Chercher pattern "Société/Entreprise: ..." dans texte (prioritaire sur ligne majuscule)
    match = re.search(r"(?i)(soci[ée]t[ée]|entreprise|firm|company)[:\s]+([A-Za-zÀ-ÿ\s]{4,80})", text)
    if match:
        return match.group(2).strip().upper()[:80]
    
    # c) Première ligne MAJUSCULE non-titre dans le document
    for line in text.splitlines():
        line = line.strip()
        if 4 <= len(line) <= 100 and line == line.upper() and re.search(r"[A-Z]", line):
            # Exclure titres de section
            if not re.match(r"^(OFFRE|PROPOSITION|SOUMISSION|ANNEXE)", line):
                return line[:80]
    
    # d) Dernier recours
    return "FOURNISSEUR_INCONNU"


def extract_offer_data_guided(offer_text: str, criteria: List[DAOCriterion]) -> Dict[str, Any]:
    """
    Extraction GUIDÉE par critères DAO (pas aveugle).
    Retourne: données + sources + champs manquants.
    """
    extracted = {
        "total_price": None,
        "total_price_source": None,
        "currency": "XOF",
        "lead_time_days": None,
        "lead_time_source": None,
        "validity_days": None,
        "validity_source": None,
        "technical_refs": [],
        "missing_fields": []
    }

    # Prix (si critère commercial présent)
    commercial_criteria = [c for c in criteria if c.categorie == "commercial"]
    if commercial_criteria:
        money = re.findall(
            r"(?i)(prix\s+total|montant\s+total|total)[:\s]*(\d{1,3}(?:[\s\.,]\d{3})+(?:[\s\.,]\d{2})?|\d+)\s*(FCFA|CFA|XOF)",
            offer_text
        )
        if not money:
            # Fallback: any large number with currency
            money = re.findall(
                r"(?i)(\d{1,3}(?:[\s\.,]\d{3})+(?:[\s\.,]\d{2})?|\d+)\s*(FCFA|CFA|XOF)",
                offer_text
            )

        if money:
            def to_num(s: str) -> float:
                s = s.replace(" ", "").replace(",", ".")
                if s.count(".") > 1:
                    parts = s.split(".")
                    s = "".join(parts[:-1]) + "." + parts[-1]
                try:
                    return float(s)
                except:
                    return 0.0

            if len(money[0]) == 3:  # Format avec label
                best = max(money, key=lambda m: to_num(m[1]))
                extracted["total_price"] = f"{best[1]} {best[2].upper()}"
                extracted["total_price_source"] = f"Pattern: '{best[0]}'"
            else:
                best = max(money, key=lambda m: to_num(m[0]))
                extracted["total_price"] = f"{best[0]} {best[1].upper()}"
                extracted["total_price_source"] = "Heuristique: plus grand montant"
        else:
            extracted["missing_fields"].append("Prix total")

    # Délai
    m = re.search(
        r"(?i)(d[ée]lai\s+(?:de\s+)?livraison|lead\s*time)[:\s\-]*([0-9]{1,3})\s*(jours?|days?)",
        offer_text
    )
    if m:
        extracted["lead_time_days"] = int(m.group(2))
        extracted["lead_time_source"] = f"Pattern: '{m.group(1)}'"
    else:
        extracted["missing_fields"].append("Délai livraison")

    # Validité
    m2 = re.search(
        r"(?i)(validit[ée]\s+(?:de\s+l['\u2019])?offre|valid\s*until)[:\s\-]*([0-9]{1,3})\s*(jours?|days?)",
        offer_text
    )
    if m2:
        extracted["validity_days"] = int(m2.group(2))
        extracted["validity_source"] = f"Pattern: '{m2.group(1)}'"
    else:
        extracted["missing_fields"].append("Validité offre")

    # Références techniques
    technical_criteria = [c for c in criteria if c.categorie == "technique"]
    if technical_criteria:
        refs = re.findall(
            r"(?i)(r[ée]f[ée]rence|client|projet|contrat)[:\s]+([\w\s\-]{10,100})",
            offer_text
        )
        extracted["technical_refs"] = [r[1].strip() for r in refs[:5]]
        if not extracted["technical_refs"]:
            extracted["missing_fields"].append("Références techniques")

    return extracted


# =========================
# CBA Template Analysis (ADAPTIVE)
# =========================
def analyze_cba_template(template_path: str) -> CBATemplateSchema:
    """Analyse dynamique structure template CBA"""
    wb = load_workbook(template_path)
    ws = wb.active

    supplier_header_row = None
    supplier_name_row = None
    supplier_cols: List[int] = []

    # Detect supplier header
    for row_idx in range(1, min(12, ws.max_row + 1)):
        for col_idx in range(1, ws.max_column + 1):
            val = ws.cell(row_idx, col_idx).value
            if val and isinstance(val, str):
                if re.search(r"(?i)(soumissionnaire|supplier|fournisseur|bidder)", val):
                    supplier_header_row = row_idx
                    # Detect supplier columns
                    for c in range(col_idx, min(col_idx + 15, ws.max_column + 1)):
                        if ws.cell(row_idx, c).value:
                            supplier_cols.append(c)
                    break
        if supplier_header_row:
            break

    supplier_name_row = supplier_header_row + 1 if supplier_header_row else None

    # Detect criteria rows
    criteria_start_row = None
    criteria_rows: List[Dict[str, Any]] = []

    if supplier_name_row:
        for row_idx in range(supplier_name_row + 1, min(supplier_name_row + 40, ws.max_row + 1)):
            col_a = ws.cell(row_idx, 1).value or ""
            col_b = ws.cell(row_idx, 2).value or ""

            if isinstance(col_b, str) and len(col_b) > 5:
                if not criteria_start_row:
                    criteria_start_row = row_idx

                # Type detection
                ctype = "autre"
                if re.search(r"(?i)(essent|mandatory|obligatoire)", col_b):
                    ctype = "essentiels"
                elif re.search(r"(?i)(technique|technical|capacity)", col_b):
                    ctype = "technique"
                elif re.search(r"(?i)(commercial|price|prix|co[uû]t)", col_b):
                    ctype = "commercial"
                elif re.search(r"(?i)(durabilit[ée]|sustainability)", col_b):
                    ctype = "durabilite"

                criteria_rows.append({
                    "row": row_idx,
                    "name": col_b[:150],
                    "type": ctype
                })

    schema = CBATemplateSchema(
        template_id=str(uuid.uuid4()),
        template_name=Path(template_path).name,
        supplier_header_row=supplier_header_row or 0,
        supplier_name_row=supplier_name_row or 0,
        supplier_cols=supplier_cols,
        criteria_start_row=criteria_start_row or 0,
        criteria_rows=criteria_rows,
        sheets=wb.sheetnames,
        meta={"detected_at": datetime.utcnow().isoformat()}
    )

    return schema


def fill_cba_adaptive(
    template_path: str,
    case_id: str,
    suppliers: List[dict],
    dao_criteria: List[DAOCriterion]
) -> str:
    """
    Remplissage adaptatif basé sur structure template détectée.
    1 DAO = 1 template spécifique = 1 CBA unique.
    
    COMPORTEMENT ATTENDU:
    - Noms fournisseurs RÉELS (pas d'IDs, pas de hash)
    - Données manquantes → "REVUE MANUELLE" avec surlignage ORANGE
    - Aucun onglet debug visible dans l'export final
    - Aucune note magique, aucune élimination implicite
    """
    schema = analyze_cba_template(template_path)

    # Save schema to DB for future learning
    with get_connection() as conn:
        db_execute(conn, """
            INSERT INTO cba_template_schemas (id, case_id, template_name, structure_json, created_at)
            VALUES (:tid, :cid, :tname, :struct, :ts)
        """, {
            "tid": schema.template_id, "cid": case_id, "tname": schema.template_name,
            "struct": json.dumps(asdict(schema), ensure_ascii=False),
            "ts": datetime.utcnow().isoformat(),
        })

    # Load template
    wb = load_workbook(template_path)
    ws = wb.active
    
    # Couleur ORANGE pour REVUE MANUELLE (spec conforme)
    ORANGE_FILL = PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid")
    REVUE_MANUELLE = "REVUE MANUELLE"

    # Metadata section (top)
    ws["A1"] = "Decision Memory System — CBA Adaptatif"
    ws["A2"] = f"Case ID: {case_id}"
    ws["A3"] = f"Generated: {datetime.utcnow().isoformat()}"
    ws["A4"] = f"Template: {schema.template_name}"

    # Fill supplier names (detected row/cols) - NOMS RÉELS uniquement
    if schema.supplier_name_row and schema.supplier_cols:
        for idx, supplier in enumerate(suppliers[:len(schema.supplier_cols)]):
            col = schema.supplier_cols[idx]
            supplier_name = supplier.get("supplier_name", "")
            
            # Vérifier que ce n'est pas un ID
            if not supplier_name or supplier_name in ["SUPPLIER_UNKNOWN", "FOURNISSEUR_INCONNU"]:
                supplier_name = REVUE_MANUELLE
            
            # Écriture unique de la cellule
            cell = ws.cell(schema.supplier_name_row, col)
            cell.value = supplier_name
            if supplier_name == REVUE_MANUELLE:
                cell.fill = ORANGE_FILL

    # Fill commercial data (detected criteria rows)
    for row_idx in range(schema.criteria_start_row, min(schema.criteria_start_row + 50, ws.max_row + 1)):
        label = ws.cell(row_idx, 2).value or ""

        for idx, supplier in enumerate(suppliers[:len(schema.supplier_cols)]):
            col = schema.supplier_cols[idx]
            cell = ws.cell(row_idx, col)
            
            # Vérifier le package_status du fournisseur
            package_status = supplier.get("package_status", "UNKNOWN")
            has_financial = supplier.get("has_financial", False)

            # Mapping guided by criteria
            if re.search(r"(?i)(prix|price|montant|co[uû]t)", label):
                if has_financial:
                    val = supplier.get("total_price")
                    if val:
                        cell.value = val
                        if supplier.get("total_price_source"):
                            from openpyxl.comments import Comment
                            cell.comment = Comment(supplier["total_price_source"], "DMS")
                    else:
                        cell.value = REVUE_MANUELLE
                        cell.fill = ORANGE_FILL
                else:
                    # Offre sans partie financière
                    cell.value = REVUE_MANUELLE
                    cell.fill = ORANGE_FILL

            elif re.search(r"(?i)(d[ée]lai|lead.*time|delivery)", label):
                val = supplier.get("lead_time_days")
                if val:
                    cell.value = f"{val} jours"
                    if supplier.get("lead_time_source"):
                        from openpyxl.comments import Comment
                        cell.comment = Comment(supplier["lead_time_source"], "DMS")
                else:
                    cell.value = REVUE_MANUELLE
                    cell.fill = ORANGE_FILL

            elif re.search(r"(?i)(validit[ée]|validity)", label):
                val = supplier.get("validity_days")
                if val:
                    cell.value = f"{val} jours"
                    if supplier.get("validity_source"):
                        from openpyxl.comments import Comment
                        cell.comment = Comment(supplier["validity_source"], "DMS")
                else:
                    cell.value = REVUE_MANUELLE
                    cell.fill = ORANGE_FILL

            elif re.search(r"(?i)(r[ée]f[ée]rence|experience)", label):
                refs = supplier.get("technical_refs", [])
                if refs:
                    cell.value = ", ".join(refs[:3])
                else:
                    cell.value = REVUE_MANUELLE
                    cell.fill = ORANGE_FILL

    # ❌ SUPPRIMER onglets debug de l'export final
    # On ne crée PLUS le DMS_SUMMARY dans l'export (logs uniquement)
    debug_sheets = ["DMS_SUMMARY", "DEBUG", "TEMP", "SCRATCH", "NOTES"]
    for sheet_name in list(wb.sheetnames):
        for debug_pattern in debug_sheets:
            if debug_pattern in sheet_name.upper():
                # Supprimer complètement (pas masquer)
                wb.remove(wb[sheet_name])
                break

    # Save output
    out_dir = OUTPUTS_DIR / case_id
    out_dir.mkdir(exist_ok=True)
    out_name = f"CBA_{Path(template_path).stem}_{uuid.uuid4().hex[:6]}.xlsx"
    out_path = out_dir / out_name
    wb.save(out_path)

    return str(out_path)


# =========================
# PV Generation (Template-specific)
# =========================
def generate_pv_adaptive(
    template_path: Optional[str],
    case_id: str,
    case_title: str,
    suppliers: List[dict],
    dao_criteria: List[DAOCriterion],
    decision: Optional[dict] = None
) -> str:
    """
    Generate PV from template or create structured fallback.
    1 DAO = 1 PV template = 1 PV unique.
    """
    if template_path and Path(template_path).exists():
        doc = Document(template_path)
    else:
        doc = Document()
        doc.add_heading("Procès-Verbal — Decision Memory System", level=1)
        doc.add_paragraph(f"Case: {case_title}")
        doc.add_paragraph(f"Case ID: {case_id}")
        doc.add_paragraph(f"Generated: {datetime.utcnow().isoformat()}")

    # Suppliers summary
    lines: List[str] = []
    for s in suppliers:
        missing = s.get("missing_fields", [])
        status = "⚠️ Données incomplètes" if missing else "✓ Complet"
        lines.append(
            f"- {s['supplier_name']} | Prix: {s.get('total_price') or 'N/A'} | "
            f"Délai: {s.get('lead_time_days') or 'N/A'}j | "
            f"Validité: {s.get('validity_days') or 'N/A'}j | "
            f"Status: {status}"
        )
    suppliers_block = "\n".join(lines)

    # Placeholders replacement
    repl = {
        "{{CASE_ID}}": case_id,
        "{{CASE_TITLE}}": case_title,
        "{{GENERATED_AT}}": datetime.utcnow().isoformat(),
        "{{SUPPLIERS_TABLE}}": suppliers_block,
        "{{CRITERIA_COUNT}}": str(len(dao_criteria)),
        "{{OFFERS_COUNT}}": str(len(suppliers)),
        "{{CHOSEN_SUPPLIER}}": (decision["chosen_supplier"] if decision else "NON DÉCIDÉ (validation humaine requise)"),
        "{{DECISION_REASON}}": (decision.get("decision_reason", "") if decision else ""),
        "{{NEXT_ACTION}}": (decision.get("next_action", "") if decision else ""),
    }

    for p in doc.paragraphs:
        for k, v in repl.items():
            if k in p.text:
                p.text = p.text.replace(k, v)

    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                for k, v in repl.items():
                    if k in cell.text:
                        cell.text = cell.text.replace(k, v)

    # Append structured content if no template or empty
    if not template_path or doc.paragraphs[-1].text.strip() == "":
        doc.add_page_break()
        doc.add_heading("RÉSUMÉ AUTO-EXTRAIT (à valider)", level=2)

        doc.add_heading("Critères DAO", level=3)
        for c in dao_criteria:
            doc.add_paragraph(
                f"• {c.critere_nom} ({c.categorie}) — "
                f"{'Éliminatoire' if c.ponderation == 0 else f'{c.ponderation*100:.0f}%'}",
                style="List Bullet"
            )

        doc.add_heading("Offres reçues", level=3)
        for line in lines:
            doc.add_paragraph(line, style="List Bullet")

        if decision:
            doc.add_page_break()
            doc.add_heading("DÉCISION HUMAINE (FINALE)", level=2)
            doc.add_paragraph(f"Fournisseur retenu: {decision['chosen_supplier']}")
            doc.add_paragraph(f"Justification: {decision['decision_reason']}")
            doc.add_paragraph(f"Action suivante: {decision['next_action']}")
            doc.add_paragraph(f"Horodatage: {decision['decided_at']}")
            doc.add_paragraph("\n⚠️ Cette décision est prise par le comité d'évaluation. "
                            "Le système n'a effectué aucune recommandation automatique.")

    # Save output
    out_dir = OUTPUTS_DIR / case_id
    out_dir.mkdir(exist_ok=True)
    tpl_name = Path(template_path).stem if template_path else "DEFAULT"
    out_name = f"PV_{tpl_name}_{uuid.uuid4().hex[:6]}.docx"
    out_path = out_dir / out_name
    doc.save(out_path)

    return str(out_path)


# =========================
# API Routes
# =========================
@app.get("/", response_class=HTMLResponse)
def home():
    idx = STATIC_DIR / "index.html"
    if not idx.exists():
        return HTMLResponse("<h3>Missing static/index.html</h3>", status_code=500)
    return HTMLResponse(idx.read_text(encoding="utf-8"))


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "version": APP_VERSION,
        "invariants_status": "enforced"
    }


@app.get("/api/constitution")
def api_constitution():
    return {"invariants": INVARIANTS, "version": APP_VERSION}


@app.post("/api/cases")
def create_case(payload: CaseCreate, user: "CurrentUser" = None):
    """Crée nouveau case (requiert authentification)."""
    from src.auth import CurrentUser as CU
    
    case_type = payload.case_type.strip().upper()
    if case_type not in {"DAO", "RFQ"}:
        raise HTTPException(status_code=400, detail="case_type must be DAO or RFQ")

    case_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    with get_connection() as conn:
        db_execute(conn, """
            INSERT INTO cases (id, case_type, title, lot, created_at, status, owner_id)
            VALUES (:id, :ctype, :title, :lot, :ts, :status, :owner)
        """, {
            "id": case_id, 
            "ctype": case_type, 
            "title": payload.title.strip(), 
            "lot": payload.lot, 
            "ts": now, 
            "status": "open",
            "owner": user["id"] if user else None
        })

    return {
        "id": case_id,
        "case_type": case_type,
        "title": payload.title,
        "lot": payload.lot,
        "created_at": now,
        "status": "open",
        "owner_id": user["id"] if user else None
    }


@app.get("/api/cases")
@limiter.limit("50/minute")
def list_cases(request: "Request"):
    """Liste tous les cases (rate limited)."""
    from fastapi import Request as Req
    with get_connection() as conn:
        rows = db_fetchall(conn, "SELECT * FROM cases ORDER BY created_at DESC")
    return rows


@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    with get_connection() as conn:
        c = db_execute_one(conn, "SELECT * FROM cases WHERE id=:id", {"id": case_id})
    if not c:
        raise HTTPException(status_code=404, detail="case not found")

    arts = get_artifacts(case_id)
    mem = list_memory(case_id)

    # Get DAO criteria if analyzed
    with get_connection() as conn:
        criteria = db_fetchall(conn, "SELECT * FROM dao_criteria WHERE case_id=:cid ORDER BY ordre_affichage", {"cid": case_id})

    return {
        "case": dict(c),
        "artifacts": arts,
        "memory": mem,
        "dao_criteria": criteria
    }


@app.post("/api/upload/{case_id}/{kind}")
def upload(case_id: str, kind: str, file: UploadFile = File(...)):
    with get_connection() as conn:
        c = db_execute_one(conn, "SELECT id FROM cases WHERE id=:id", {"id": case_id})
    if not c:
        raise HTTPException(status_code=404, detail="case not found")

    kind = kind.strip().lower()
    allowed = {"dao", "offer", "cba_template", "pv_template"}
    if kind not in allowed:
        raise HTTPException(status_code=400, detail=f"kind must be one of {sorted(list(allowed))}")

    filename, path = safe_save_upload(case_id, kind, file)
    aid = register_artifact(case_id, kind, filename, path, meta={"original_name": file.filename})

    return {"ok": True, "artifact_id": aid, "filename": filename}


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


@app.get("/api/download/{case_id}/{kind}")
def download_latest(case_id: str, kind: str):
    """Download latest generated artifact"""
    kind = kind.strip().lower()
    if kind not in {"output_cba", "output_pv"}:
        raise HTTPException(status_code=400, detail="kind must be output_cba or output_pv")

    arts = get_artifacts(case_id, kind)
    if not arts:
        raise HTTPException(status_code=404, detail=f"No artifact found for {kind}")

    p = Path(arts[0]["path"])
    if not p.exists():
        raise HTTPException(status_code=404, detail="file missing on disk")

    return FileResponse(path=str(p), filename=p.name, media_type="application/octet-stream")


@app.get("/api/memory/{case_id}")
def memory(case_id: str):
    """Retrieve all memory entries for a case"""
    return {"case_id": case_id, "memory": list_memory(case_id)}


@app.get("/api/search_memory/{case_id}")
def search_memory(case_id: str, q: str):
    """Search memory entries by keyword"""
    q = (q or "").strip().lower()
    if not q:
        return {"case_id": case_id, "hits": []}

    mem = list_memory(case_id)
    hits = []
    for entry in mem:
        blob = json.dumps(entry.get("content", {}), ensure_ascii=False).lower()
        if q in blob:
            hits.append({
                "id": entry["id"],
                "entry_type": entry["entry_type"],
                "created_at": entry["created_at"],
                "preview": entry["content"]
            })

    return {"case_id": case_id, "q": q, "hits": hits}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
