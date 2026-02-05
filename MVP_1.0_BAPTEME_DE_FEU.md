from __future__ import annotations

import json
import re
import sqlite3
import uuid
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


# =========================================================
# Decision Memory System — MVP A++ FINAL
# Version: 1.0.0
# DAO-driven extraction + Template-adaptive CBA + Active Memory
# =========================================================

APP_TITLE = "Decision Memory System — MVP A++ (Production)"
APP_VERSION = "1.0.0"

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
OUTPUTS_DIR = DATA_DIR / "outputs"
DB_PATH = DATA_DIR / "dms.sqlite3"

DATA_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

app = FastAPI(title=APP_TITLE, version=APP_VERSION)

STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# =========================
# CONSTITUTION
# =========================
INVARIANTS = {
    "cognitive_load_never_increase": True,
    "human_decision_final": True,
    "no_scoring_no_ranking_no_recommendations": True,
    "memory_is_byproduct_never_a_task": True,
    "erp_agnostic": True,
    "offline_first": True,
    "traceability_keep_sources": True,
    "one_dao_one_cba_one_pv": True,
}


# =========================
# Database
# =========================
def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db() as conn:
        cur = conn.cursor()

        # Cases (unchanged)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id TEXT PRIMARY KEY,
            case_type TEXT NOT NULL,
            title TEXT NOT NULL,
            lot TEXT,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL
        )
        """)

        # Artifacts (unchanged)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS artifacts (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            filename TEXT NOT NULL,
            path TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            meta_json TEXT,
            FOREIGN KEY(case_id) REFERENCES cases(id)
        )
        """)

        # Memory entries (unchanged)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS memory_entries (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            entry_type TEXT NOT NULL,
            content_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(case_id) REFERENCES cases(id)
        )
        """)

        # NEW: DAO Criteria (structured extraction)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS dao_criteria (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            categorie TEXT NOT NULL,
            critere_nom TEXT NOT NULL,
            description TEXT,
            ponderation REAL NOT NULL,
            type_reponse TEXT NOT NULL,
            seuil_elimination REAL,
            ordre_affichage INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(case_id) REFERENCES cases(id)
        )
        """)

        # NEW: CBA Template Schemas (template learning)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS cba_template_schemas (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            template_name TEXT NOT NULL,
            structure_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            reused_count INTEGER DEFAULT 0,
            FOREIGN KEY(case_id) REFERENCES cases(id)
        )
        """)

        # NEW: Offer Extractions (DAO-guided data)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS offer_extractions (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            artifact_id TEXT NOT NULL,
            supplier_name TEXT NOT NULL,
            extracted_data_json TEXT NOT NULL,
            missing_fields_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(case_id) REFERENCES cases(id),
            FOREIGN KEY(artifact_id) REFERENCES artifacts(id)
        )
        """)

        conn.commit()


init_db()


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
    with db() as conn:
        conn.execute("""
            INSERT INTO artifacts (id, case_id, kind, filename, path, uploaded_at, meta_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            artifact_id, case_id, kind, filename, path,
            datetime.utcnow().isoformat(),
            json.dumps(meta or {}, ensure_ascii=False),
        ))
        conn.commit()
    return artifact_id


def get_artifacts(case_id: str, kind: Optional[str] = None) -> List[sqlite3.Row]:
    with db() as conn:
        if kind:
            return conn.execute(
                "SELECT * FROM artifacts WHERE case_id=? AND kind=? ORDER BY uploaded_at DESC",
                (case_id, kind),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM artifacts WHERE case_id=? ORDER BY uploaded_at DESC",
            (case_id,),
        ).fetchall()


def add_memory(case_id: str, entry_type: str, content: dict) -> str:
    mem_id = str(uuid.uuid4())
    with db() as conn:
        conn.execute("""
            INSERT INTO memory_entries (id, case_id, entry_type, content_json, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            mem_id, case_id, entry_type,
            json.dumps(content, ensure_ascii=False),
            datetime.utcnow().isoformat(),
        ))
        conn.commit()
    return mem_id


def list_memory(case_id: str, entry_type: Optional[str] = None) -> List[dict]:
    with db() as conn:
        if entry_type:
            rows = conn.execute("""
                SELECT * FROM memory_entries WHERE case_id=? AND entry_type=? ORDER BY created_at DESC
            """, (case_id, entry_type)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM memory_entries WHERE case_id=? ORDER BY created_at DESC
            """, (case_id,)).fetchall()

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
    """Extract supplier name from filename or document"""
    base = Path(filename).stem
    base = re.sub(r"(?i)\b(offre|lot|dao|rfq|mpt|mopti|2026)\b", " ", base)
    base = re.sub(r"[_\-]+", " ", base).strip()
    if len(base) >= 3:
        return base.upper()[:80]

    # Fallback: first all-caps line
    for line in text.splitlines():
        line = line.strip()
        if 4 <= len(line) <= 100 and line == line.upper() and re.search(r"[A-Z]", line):
            return line[:80]

    return "SUPPLIER_UNKNOWN"


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
    """
    schema = analyze_cba_template(template_path)

    # Save schema to DB for future learning
    with db() as conn:
        conn.execute("""
            INSERT INTO cba_template_schemas (id, case_id, template_name, structure_json, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            schema.template_id,
            case_id,
            schema.template_name,
            json.dumps(asdict(schema), ensure_ascii=False),
            datetime.utcnow().isoformat()
        ))
        conn.commit()

    # Load template
    wb = load_workbook(template_path)
    ws = wb.active

    # Metadata section (top)
    ws["A1"] = "Decision Memory System — CBA Adaptatif"
    ws["A2"] = f"Case ID: {case_id}"
    ws["A3"] = f"Generated: {datetime.utcnow().isoformat()}"
    ws["A4"] = f"Template: {schema.template_name}"

    # Fill supplier names (detected row/cols)
    if schema.supplier_name_row and schema.supplier_cols:
        for idx, supplier in enumerate(suppliers[:len(schema.supplier_cols)]):
            col = schema.supplier_cols[idx]
            ws.cell(schema.supplier_name_row, col, supplier["supplier_name"])

    # Fill commercial data (detected criteria rows)
    for row_idx in range(schema.criteria_start_row, min(schema.criteria_start_row + 50, ws.max_row + 1)):
        label = ws.cell(row_idx, 2).value or ""

        for idx, supplier in enumerate(suppliers[:len(schema.supplier_cols)]):
            col = schema.supplier_cols[idx]

            # Mapping guided by criteria
            if re.search(r"(?i)(prix|price|montant|co[uû]t)", label):
                val = supplier.get("total_price") or "NON TROUVÉ"
                ws.cell(row_idx, col, val)
                # Source in comment (Excel feature)
                if supplier.get("total_price_source"):
                    ws.cell(row_idx, col).comment = supplier["total_price_source"]

            elif re.search(r"(?i)(d[ée]lai|lead.*time|delivery)", label):
                val = supplier.get("lead_time_days")
                ws.cell(row_idx, col, f"{val} jours" if val else "NON TROUVÉ")
                if supplier.get("lead_time_source"):
                    ws.cell(row_idx, col).comment = supplier["lead_time_source"]

            elif re.search(r"(?i)(validit[ée]|validity)", label):
                val = supplier.get("validity_days")
                ws.cell(row_idx, col, f"{val} jours" if val else "NON TROUVÉ")
                if supplier.get("validity_source"):
                    ws.cell(row_idx, col).comment = supplier["validity_source"]

            elif re.search(r"(?i)(r[ée]f[ée]rence|experience)", label):
                refs = supplier.get("technical_refs", [])
                ws.cell(row_idx, col, ", ".join(refs[:3]) if refs else "NON TROUVÉ")

            # Highlight missing data
            if "NON TROUVÉ" in str(ws.cell(row_idx, col).value):
                ws.cell(row_idx, col).fill = PatternFill(
                    start_color="FFF4E6", end_color="FFF4E6", fill_type="solid"
                )

    # Add summary sheet with criteria structure
    if "DMS_SUMMARY" not in wb.sheetnames:
        summary = wb.create_sheet("DMS_SUMMARY")
        summary["A1"] = "CRITÈRES DAO (Structurés)"
        summary["A2"] = "Catégorie"
        summary["B2"] = "Critère"
        summary["C2"] = "Pondération"
        summary["D2"] = "Type"

        row = 3
        for c in dao_criteria:
            summary[f"A{row}"] = c.categorie
            summary[f"B{row}"] = c.critere_nom
            summary[f"C{row}"] = f"{c.ponderation*100:.0f}%" if c.ponderation else "Éliminatoire"
            summary[f"D{row}"] = c.type_reponse
            row += 1

        summary["A" + str(row + 2)] = "DONNÉES MANQUANTES (par fournisseur)"
        row += 3
        summary[f"A{row}"] = "Fournisseur"
        summary[f"B{row}"] = "Champs manquants"
        row += 1

        for s in suppliers:
            summary[f"A{row}"] = s["supplier_name"]
            summary[f"B{row}"] = ", ".join(s.get("missing_fields", [])) or "Complet"
            if s.get("missing_fields"):
                summary[f"B{row}"].fill = PatternFill(
                    start_color="FFE6E6", end_color="FFE6E6", fill_type="solid"
                )
            row += 1

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
def create_case(payload: CaseCreate):
    case_type = payload.case_type.strip().upper()
    if case_type not in {"DAO", "RFQ"}:
        raise HTTPException(status_code=400, detail="case_type must be DAO or RFQ")

    case_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    with db() as conn:
        conn.execute("""
            INSERT INTO cases (id, case_type, title, lot, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (case_id, case_type, payload.title.strip(), payload.lot, now, "open"))
        conn.commit()

    return {
        "id": case_id,
        "case_type": case_type,
        "title": payload.title,
        "lot": payload.lot,
        "created_at": now,
        "status": "open"
    }


@app.get("/api/cases")
def list_cases():
    with db() as conn:
        rows = conn.execute("SELECT * FROM cases ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    with db() as conn:
        c = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    if not c:
        raise HTTPException(status_code=404, detail="case not found")

    arts = [dict(a) for a in get_artifacts(case_id)]
    mem = list_memory(case_id)

    # Get DAO criteria if analyzed
    with db() as conn:
        criteria_rows = conn.execute(
            "SELECT * FROM dao_criteria WHERE case_id=? ORDER BY ordre_affichage",
            (case_id,)
        ).fetchall()
    criteria = [dict(r) for r in criteria_rows]

    return {
        "case": dict(c),
        "artifacts": arts,
        "memory": mem,
        "dao_criteria": criteria
    }


@app.post("/api/upload/{case_id}/{kind}")
def upload(case_id: str, kind: str, file: UploadFile = File(...)):
    with db() as conn:
        c = conn.execute("SELECT id FROM cases WHERE id=?", (case_id,)).fetchone()
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

    with db() as conn:
        case = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
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
    with db() as conn:
        for c in dao_criteria:
            conn.execute("""
                INSERT INTO dao_criteria 
                (id, case_id, categorie, critere_nom, description, ponderation, type_reponse, seuil_elimination, ordre_affichage, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), case_id, c.categorie, c.critere_nom, c.description,
                c.ponderation, c.type_reponse, c.seuil_elimination, c.ordre_affichage,
                datetime.utcnow().isoformat()
            ))
        conn.commit()

    # Step 2: Offers extraction (DAO-guided)
    offer_arts = get_artifacts(case_id, "offer")
    if not offer_arts:
        raise HTTPException(status_code=400, detail="Missing OFFERS (upload kind=offer)")

    suppliers: List[dict] = []
    for off in offer_arts:
        txt = extract_text_any(off["path"])
        supplier_name = guess_supplier_name(txt, off["filename"])
        offer_data = extract_offer_data_guided(txt, dao_criteria)

        suppliers.append({
            "supplier_name": supplier_name,
            **offer_data,
            "source_filename": off["filename"],
            "artifact_id": off["id"]
        })

        # Store extraction in DB
        with db() as conn:
            conn.execute("""
                INSERT INTO offer_extractions (id, case_id, artifact_id, supplier_name, extracted_data_json, missing_fields_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), case_id, off["id"], supplier_name,
                json.dumps(offer_data, ensure_ascii=False),
                json.dumps(offer_data.get("missing_fields", []), ensure_ascii=False),
                datetime.utcnow().isoformat()
            ))
            conn.commit()

    # Memory entry
    add_memory(case_id, "extraction", {
        "dao_source": dao_arts[0]["filename"],
        "offers_sources": [o["filename"] for o in offer_arts],
        "dao_criteria_count": len(dao_criteria),
        "dao_criteria": [asdict(c) for c in dao_criteria],
        "offers_summary": suppliers,
        "note": "DAO-driven extraction. No scoring/ranking. Human validates."
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

    return {
        "ok": True,
        "case_id": case_id,
        "dao_criteria_count": len(dao_criteria),
        "offers_count": len(suppliers),
        "output_cba_generated": bool(cba_out),
        "output_pv_generated": True,
        "downloads": {
            "cba": f"/api/download/{case_id}/output_cba" if cba_out else None,
            "pv": f"/api/download/{case_id}/output_pv",
        },
        "warnings": {
            "missing_data_count": sum(len(s.get("missing_fields", [])) for s in suppliers),
            "suppliers_with_missing_data": [s["supplier_name"] for s in suppliers if s.get("missing_fields")]
        }
    }


@app.post("/api/decide")
def decide(payload: DecideRequest):
    """Record human decision and regenerate PV"""
    case_id = payload.case_id

    with db() as conn:
        case = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
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
    with db() as conn:
        extractions = conn.execute(
            "SELECT * FROM offer_extractions WHERE case_id=?",
            (case_id,)
        ).fetchall()
        criteria_rows = conn.execute(
            "SELECT * FROM dao_criteria WHERE case_id=?",
            (case_id,)
        ).fetchall()

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
