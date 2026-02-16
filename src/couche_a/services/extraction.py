"""Document extraction service for Couche A."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from docx import Document as DocxDocument
from openpyxl import load_workbook
from pypdf import PdfReader
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from ..models import (
    audits_table,
    documents_table,
    ensure_schema,
    extractions_table,
    generate_id,
    get_engine,
    offers_table,
    serialize_json,
)


def _extract_text_from_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages[:3]]
    return "\n".join(pages)


def _extract_text_from_docx(path: Path) -> str:
    doc = DocxDocument(str(path))
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)


def _extract_text_from_xlsx(path: Path) -> str:
    workbook = load_workbook(str(path), read_only=True)
    text_lines: List[str] = []
    for sheet in workbook.worksheets[:1]:
        for row in sheet.iter_rows(max_row=20, max_col=10):
            for cell in row:
                if cell.value:
                    text_lines.append(str(cell.value))
    workbook.close()
    return "\n".join(text_lines)


def extract_text(path: Path) -> str:
    """Extract text from supported document types."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_text_from_pdf(path)
    if suffix in {".docx", ".doc"}:
        return _extract_text_from_docx(path)
    if suffix in {".xlsx", ".xls"}:
        return _extract_text_from_xlsx(path)
    return path.read_text(errors="ignore")


def _normalize_amount(raw_amount: str) -> float:
    cleaned = raw_amount.replace(" ", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def extract_fields(text: str) -> Tuple[Dict[str, Any], List[str]]:
    """Extract structured fields from raw text."""
    missing_fields: List[str] = []
    supplier_match = re.search(
        r"(fournisseur|soumissionnaire)\s*[:\-]\s*([^\n]+)", text, re.IGNORECASE
    )
    supplier_name = supplier_match.group(2).strip() if supplier_match else None

    date_match = re.search(r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})", text)
    depot_date = date_match.group(1) if date_match else None

    amount_match = re.search(
        r"(\d{1,3}(?:[\s,.]\d{3})*(?:[,.]\d{2})?)\s?(fcfa|eur|usd)?",
        text,
        re.IGNORECASE,
    )
    amount = _normalize_amount(amount_match.group(1)) if amount_match else None

    zone_match = re.search(r"zone\s*[:\-]\s*([^\n]+)", text, re.IGNORECASE)
    zone = zone_match.group(1).strip() if zone_match else None

    attachments = [
        line.strip() for line in text.splitlines() if "annexe" in line.lower()
    ]

    fields = {
        "fournisseur": supplier_name,
        "date_depot": depot_date,
        "montant": amount,
        "documents_joints": attachments,
        "zone": zone,
    }

    for key, value in fields.items():
        if value in (None, "", []):
            missing_fields.append(key)

    return fields, missing_fields


async def extract_and_store(
    document_id: str, llm_enabled: bool = False
) -> Dict[str, Any]:
    """Extract data from a document and store the results."""

    def _process() -> Dict[str, Any]:
        engine = get_engine()
        ensure_schema(engine)
        try:
            with engine.begin() as conn:
                doc_row = (
                    conn.execute(
                        select(documents_table).where(
                            documents_table.c.id == document_id
                        )
                    )
                    .mappings()
                    .first()
                )
                if not doc_row:
                    raise ValueError("Document introuvable.")

                file_path = Path(doc_row["storage_path"])
                text = extract_text(file_path)
                extracted, missing = extract_fields(text)

                extraction_id = generate_id()
                conn.execute(
                    extractions_table.insert().values(
                        id=extraction_id,
                        document_id=document_id,
                        offer_id=doc_row["offer_id"],
                        extracted_json=serialize_json(extracted),
                        missing_json=serialize_json(missing),
                        used_llm=llm_enabled,
                    )
                )

                update_payload: Dict[str, Any] = {}
                if extracted.get("fournisseur"):
                    update_payload["supplier_name"] = extracted["fournisseur"]
                if extracted.get("montant") is not None:
                    update_payload["amount"] = extracted["montant"]
                if update_payload:
                    conn.execute(
                        update(offers_table)
                        .where(offers_table.c.id == doc_row["offer_id"])
                        .values(**update_payload)
                    )

                conn.execute(
                    audits_table.insert().values(
                        id=generate_id(),
                        entity_type="extraction",
                        entity_id=extraction_id,
                        action="EXTRACTION",
                        actor=None,
                        details_json=serialize_json(
                            {"missing_fields": missing, "llm_enabled": llm_enabled}
                        ),
                    )
                )

            return {
                "extraction_id": extraction_id,
                "document_id": document_id,
                "extracted": extracted,
                "missing_fields": missing,
                "llm_enabled": llm_enabled,
            }
        except (SQLAlchemyError, OSError) as exc:
            raise RuntimeError("Erreur lors de l'extraction.") from exc

    return await asyncio.to_thread(_process)
