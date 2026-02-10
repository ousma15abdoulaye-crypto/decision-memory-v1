"""PV generation services for Couche A."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

from docx import Document
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from ..models import (
    audits_table,
    documents_table,
    ensure_schema,
    generate_id,
    get_engine,
    lots_table,
    offers_table,
    analyses_table,
    serialize_json,
)


def _build_pv_doc(kind: str, lot_name: str, offers: list[dict]) -> Document:
    doc = Document()
    doc.add_heading(f"PV {kind}", level=1)
    doc.add_paragraph(f"Lot: {lot_name}")
    doc.add_paragraph("Synthèse des offres:")
    for offer in offers:
        doc.add_paragraph(
            f"- {offer['supplier_name']} | Montant: {offer.get('amount') or 'N/A'} | Statut: {offer.get('status')}"
        )
    return doc


async def generate_pv_ouverture(lot_id: str, actor: Optional[str] = None) -> Dict[str, Any]:
    """Generate a PV d'ouverture for a lot."""
    return await _generate_pv(lot_id, "OUVERTURE", actor)


async def generate_pv_analyse(lot_id: str, actor: Optional[str] = None) -> Dict[str, Any]:
    """Generate a PV d'analyse for a lot."""
    return await _generate_pv(lot_id, "ANALYSE", actor)


async def _generate_pv(lot_id: str, kind: str, actor: Optional[str]) -> Dict[str, Any]:
    def _process() -> Dict[str, Any]:
        engine = get_engine()
        ensure_schema(engine)
        try:
            with engine.begin() as conn:
                lot = conn.execute(
                    select(lots_table).where(lots_table.c.id == lot_id)
                ).mappings().first()
                if not lot:
                    raise ValueError("Lot introuvable.")

                offers = conn.execute(
                    select(offers_table, analyses_table.c.status.label("analysis_status"))
                    .select_from(
                        offers_table.outerjoin(
                            analyses_table, analyses_table.c.offer_id == offers_table.c.id
                        )
                    )
                    .where(offers_table.c.lot_id == lot_id)
                ).mappings().all()
                if not offers:
                    raise ValueError("Aucune offre disponible pour ce lot.")

                offer_payload = [
                    {
                        "supplier_name": offer["supplier_name"],
                        "amount": offer["amount"],
                        "status": offer.get("analysis_status") or offer.get("status") or "EN_ATTENTE",
                    }
                    for offer in offers
                ]
                doc = _build_pv_doc(kind, lot["name"], offer_payload)

                pv_dir = Path("data") / "couche_a" / "pv" / lot_id
                pv_dir.mkdir(parents=True, exist_ok=True)
                filename = f"pv_{kind.lower()}_{lot_id}.docx"
                pv_path = pv_dir / filename
                doc.save(pv_path)

                doc_id = generate_id()
                conn.execute(
                    documents_table.insert().values(
                        id=doc_id,
                        case_id=lot["case_id"],
                        lot_id=lot_id,
                        offer_id=offers[0]["id"],
                        document_type=f"PV_{kind}",
                        filename=filename,
                        storage_path=str(pv_path),
                        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        metadata_json=serialize_json({"lot_id": lot_id}),
                    )
                )
                conn.execute(
                    audits_table.insert().values(
                        id=generate_id(),
                        entity_type="pv",
                        entity_id=doc_id,
                        action=f"PV_{kind}",
                        actor=actor,
                        details_json=serialize_json({"lot_id": lot_id}),
                    )
                )
                return {"document_id": doc_id, "path": str(pv_path)}
        except (SQLAlchemyError, OSError) as exc:
            raise RuntimeError("Erreur lors de la génération du PV.") from exc

    return await asyncio.to_thread(_process)
