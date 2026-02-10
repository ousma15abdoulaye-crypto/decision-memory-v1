"""Depot service for ingesting procurement documents."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from ..models import (
    audits_table,
    cases_table,
    documents_table,
    ensure_schema,
    generate_id,
    get_engine,
    lots_table,
    offers_table,
    serialize_json,
)

ALLOWED_TYPES = {"DAO", "OFFRE_TECHNIQUE", "OFFRE_FINANCIERE", "AUTRE"}


@dataclass(frozen=True)
class DetectionResult:
    document_type: str
    confirmation_required: bool
    confidence: str


def _normalize_document_type(raw_type: Optional[str]) -> Optional[str]:
    if not raw_type:
        return None
    normalized = raw_type.strip().upper()
    if normalized in ALLOWED_TYPES:
        return normalized
    return None


def detect_document_type(filename: str, text_sample: str) -> DetectionResult:
    """Detect the document type using filename and text heuristics."""
    lower_name = filename.lower()
    lower_text = text_sample.lower()
    if "dao" in lower_name or "dao" in lower_text:
        return DetectionResult("DAO", False, "HIGH")
    if "tech" in lower_name or "technique" in lower_text:
        return DetectionResult("OFFRE_TECHNIQUE", False, "MEDIUM")
    if "fin" in lower_name or "finance" in lower_text:
        return DetectionResult("OFFRE_FINANCIERE", False, "MEDIUM")
    return DetectionResult("AUTRE", True, "LOW")


def guess_supplier_name(filename: str) -> str:
    """Guess supplier name from the filename."""
    stem = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
    if not stem:
        return "FOURNISSEUR_INCONNU"
    return stem.upper()


async def _write_file(path: Path, data: bytes) -> None:
    await asyncio.to_thread(path.write_bytes, data)


async def save_depot(
    upload: UploadFile,
    case_id: str,
    lot_id: str,
    document_type: Optional[str] = None,
    offer_id: Optional[str] = None,
    sender_email: Optional[str] = None,
    subject: Optional[str] = None,
    received_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Save an uploaded document and its metadata."""
    if not upload.filename:
        raise ValueError("Le fichier fourni est invalide.")

    file_bytes = await upload.read()
    text_sample = file_bytes[:2000].decode(errors="replace")
    normalized = _normalize_document_type(document_type)
    detection = detect_document_type(upload.filename, text_sample)
    final_type = normalized or detection.document_type

    if final_type not in ALLOWED_TYPES:
        raise ValueError("Type de document non supporté.")

    doc_id = generate_id()
    offer_identifier = offer_id or generate_id()
    filename = Path(upload.filename).name

    storage_dir = Path("data") / "couche_a" / "uploads" / case_id / lot_id
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_path = storage_dir / f"{doc_id}_{filename}"
    await _write_file(storage_path, file_bytes)

    metadata = {
        "confidence": detection.confidence,
        "confirmation_required": detection.confirmation_required,
        "sender_email": sender_email,
        "subject": subject,
        "received_at": received_at,
    }

    def _persist() -> Dict[str, Any]:
        engine = get_engine()
        ensure_schema(engine)
        supplier_name = guess_supplier_name(filename)
        try:
            with engine.begin() as conn:
                if not conn.execute(select(cases_table.c.id).where(cases_table.c.id == case_id)).first():
                    conn.execute(
                        cases_table.insert().values(
                            id=case_id,
                            title=f"Dossier {case_id}",
                            buyer_name="Acheteur",
                            status="OUVERT",
                        )
                    )
                if not conn.execute(select(lots_table.c.id).where(lots_table.c.id == lot_id)).first():
                    conn.execute(
                        lots_table.insert().values(
                            id=lot_id,
                            case_id=case_id,
                            name=f"Lot {lot_id}",
                            description="",
                        )
                    )
                if offer_id:
                    existing_offer = conn.execute(
                        select(offers_table.c.id).where(offers_table.c.id == offer_id)
                    ).first()
                else:
                    existing_offer = None
                if not existing_offer:
                    conn.execute(
                        offers_table.insert().values(
                            id=offer_identifier,
                            case_id=case_id,
                            lot_id=lot_id,
                            supplier_name=supplier_name,
                            offer_type=final_type,
                            status="EN_ATTENTE",
                        )
                    )
                conn.execute(
                    documents_table.insert().values(
                        id=doc_id,
                        case_id=case_id,
                        lot_id=lot_id,
                        offer_id=offer_identifier,
                        document_type=final_type,
                        filename=filename,
                        storage_path=str(storage_path),
                        mime_type=upload.content_type or "application/octet-stream",
                        metadata_json=serialize_json(metadata),
                    )
                )
                conn.execute(
                    audits_table.insert().values(
                        id=generate_id(),
                        entity_type="document",
                        entity_id=doc_id,
                        action="DEPOT",
                        actor=sender_email,
                        details_json=serialize_json(metadata),
                    )
                )
        except SQLAlchemyError as exc:
            raise RuntimeError("Erreur lors de la sauvegarde du dépôt.") from exc
        return {
            "document_id": doc_id,
            "offer_id": offer_identifier,
            "document_type": final_type,
            "confirmation_required": detection.confirmation_required and not normalized,
            "storage_path": str(storage_path),
        }

    return await asyncio.to_thread(_persist)
