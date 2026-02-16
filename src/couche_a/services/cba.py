"""CBA export and review services for Couche A."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import UploadFile
from openpyxl import Workbook
from openpyxl.styles import PatternFill
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from ..models import (
    analyses_table,
    audits_table,
    deserialize_json,
    documents_table,
    ensure_schema,
    extractions_table,
    generate_id,
    get_engine,
    offers_table,
    serialize_json,
)

ORANGE_FILL = PatternFill(start_color="FFA500", end_color="FFA500", fill_type="solid")


def _fill_manual_review(cell) -> None:
    cell.fill = ORANGE_FILL


def _build_workbook(payload: Dict[str, Any]) -> Workbook:
    wb = Workbook()
    summary = wb.active
    summary.title = "Summary"
    summary.append(["Offre", payload.get("supplier_name", "Inconnu")])
    summary.append(["Montant", payload.get("amount")])
    summary.append(["Statut", payload.get("status")])

    for sheet_name in ["Essentiels", "Capacité", "Durabilité", "Commercial"]:
        ws = wb.create_sheet(sheet_name)
        ws.append(["Critère", "Valeur"])
        for key, value in payload.get(sheet_name.lower(), {}).items():
            row = ws.max_row + 1
            ws.cell(row=row, column=1, value=key)
            cell = ws.cell(row=row, column=2, value=value)
            if payload.get("manual_review"):
                _fill_manual_review(cell)
    return wb


async def export_cba(offer_id: str, actor: Optional[str] = None) -> Dict[str, Any]:
    """Generate and store a CBA export for an offer."""
    def _process() -> Dict[str, Any]:
        engine = get_engine()
        ensure_schema(engine)
        try:
            with engine.begin() as conn:
                offer = conn.execute(
                    select(offers_table).where(offers_table.c.id == offer_id)
                ).mappings().first()
                if not offer:
                    raise ValueError("Offre introuvable.")
                extraction = conn.execute(
                    select(extractions_table)
                    .where(extractions_table.c.offer_id == offer_id)
                    .order_by(extractions_table.c.created_at.desc())
                ).mappings().first()
                analysis = conn.execute(
                    select(analyses_table)
                    .where(analyses_table.c.offer_id == offer_id)
                    .order_by(analyses_table.c.created_at.desc())
                ).mappings().first()

                missing_fields = []
                if extraction:
                    missing_fields = deserialize_json(extraction["missing_json"])
                    if not isinstance(missing_fields, list):
                        missing_fields = []
                manual_review = not extraction or bool(missing_fields)

                existing_exports = conn.execute(
                    select(func.count())
                    .select_from(documents_table)
                    .where(
                        (documents_table.c.offer_id == offer_id)
                        & (documents_table.c.document_type == "CBA_EXPORT")
                    )
                ).scalar_one()
                version = int(existing_exports) + 1

                payload = {
                    "supplier_name": offer["supplier_name"],
                    "amount": offer["amount"],
                    "status": analysis["status"] if analysis else "EN_ATTENTE",
                    "essentiels": {"fournisseur": offer["supplier_name"]},
                    "capacité": {},
                    "durabilité": {},
                    "commercial": {"montant": offer["amount"]},
                    "manual_review": manual_review,
                }
                wb = _build_workbook(payload)

                export_dir = Path("data") / "couche_a" / "exports" / offer_id
                export_dir.mkdir(parents=True, exist_ok=True)
                filename = f"cba_{offer_id}_v{version}.xlsx"
                export_path = export_dir / filename
                wb.save(export_path)

                doc_id = generate_id()
                metadata = {"version": version, "manual_review": manual_review}
                conn.execute(
                    documents_table.insert().values(
                        id=doc_id,
                        case_id=offer["case_id"],
                        lot_id=offer["lot_id"],
                        offer_id=offer_id,
                        document_type="CBA_EXPORT",
                        filename=filename,
                        storage_path=str(export_path),
                        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        metadata_json=serialize_json(metadata),
                    )
                )
                conn.execute(
                    audits_table.insert().values(
                        id=generate_id(),
                        entity_type="cba",
                        entity_id=doc_id,
                        action="EXPORT",
                        actor=actor,
                        details_json=serialize_json(metadata),
                    )
                )
                return {
                    "document_id": doc_id,
                    "offer_id": offer_id,
                    "version": version,
                    "path": str(export_path),
                }
        except (SQLAlchemyError, OSError) as exc:
            raise RuntimeError("Erreur lors de l'export CBA.") from exc

    return await asyncio.to_thread(_process)


async def upload_cba_review(
    offer_id: str, upload: UploadFile, reviewer: Optional[str] = None
) -> Dict[str, Any]:
    """Store a completed CBA upload for committee review."""
    if not upload.filename:
        raise ValueError("Le fichier fourni est invalide.")

    file_bytes = await upload.read()
    filename = Path(upload.filename).name
    review_dir = Path("data") / "couche_a" / "cba_reviews" / offer_id
    review_dir.mkdir(parents=True, exist_ok=True)
    review_path = review_dir / filename

    def _persist() -> Dict[str, Any]:
        engine = get_engine()
        ensure_schema(engine)
        try:
            review_path.write_bytes(file_bytes)
            with engine.begin() as conn:
                offer = conn.execute(
                    select(offers_table).where(offers_table.c.id == offer_id)
                ).mappings().first()
                if not offer:
                    raise ValueError("Offre introuvable.")
                doc_id = generate_id()
                conn.execute(
                    documents_table.insert().values(
                        id=doc_id,
                        case_id=offer["case_id"],
                        lot_id=offer["lot_id"],
                        offer_id=offer_id,
                        document_type="CBA_REVIEW",
                        filename=filename,
                        storage_path=str(review_path),
                        mime_type=upload.content_type or "application/octet-stream",
                        metadata_json=serialize_json({"reviewer": reviewer}),
                    )
                )
                conn.execute(
                    audits_table.insert().values(
                        id=generate_id(),
                        entity_type="cba",
                        entity_id=doc_id,
                        action="REVIEW_UPLOAD",
                        actor=reviewer,
                        details_json=serialize_json({"filename": filename}),
                    )
                )
            return {"document_id": doc_id, "path": str(review_path)}
        except (SQLAlchemyError, OSError) as exc:
            raise RuntimeError("Erreur lors du dépôt CBA.") from exc

    return await asyncio.to_thread(_persist)
