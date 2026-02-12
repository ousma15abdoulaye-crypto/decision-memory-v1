"""
Couche A – Endpoints d'upload (Manuel SCI §4)
Utilise exclusivement les helpers synchrones de src.db (Constitution V2.1)
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from src.db import db_execute, db_execute_one, get_connection

router = APIRouter(prefix="/api/cases", tags=["Couche A Upload"])

UPLOADS_DIR = Path("data/uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class OfferType(str, Enum):
    TECHNIQUE = "technique"
    FINANCIERE = "financiere"
    ADMINISTRATIVE = "administrative"
    REGISTRE = "registre"


def compute_file_hash(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def register_artifact(case_id: str, kind: str, filename: str, path: str, meta: dict) -> str:
    """Insère un artifact et retourne son ID (UUID)."""
    artifact_id = str(uuid.uuid4())
    with get_connection() as conn:
        db_execute(
            conn,
            """
            INSERT INTO artifacts (id, case_id, kind, filename, path, uploaded_at, meta_json)
            VALUES (:id, :case_id, :kind, :filename, :path, :ts, :meta)
            """,
            {
                "id": artifact_id,
                "case_id": case_id,
                "kind": kind,
                "filename": filename,
                "path": path,
                "ts": datetime.utcnow().isoformat(),
                "meta": json.dumps(meta, ensure_ascii=False),
            },
        )
    return artifact_id


@router.post("/{case_id}/upload-dao")
async def upload_dao(
    case_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Upload du DAO – un seul par case (409 si existant)."""
    # 1. Vérifier que la case existe
    with get_connection() as conn:
        case = db_execute_one(conn, "SELECT id FROM cases WHERE id=:id", {"id": case_id})
        if not case:
            raise HTTPException(404, "Case not found")

    # 2. Vérifier qu'aucun DAO n'existe déjà
    with get_connection() as conn:
        existing = db_execute_one(
            conn,
            "SELECT id FROM artifacts WHERE case_id=:cid AND kind='dao'",
            {"cid": case_id},
        )
        if existing:
            raise HTTPException(409, "DAO already uploaded. Delete existing DAO first.")

    # 3. Validation type/taille
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, "Invalid file type. Allowed: PDF, DOCX, XLSX")
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large (max 50 MB)")

    # 4. Sauvegarde fichier
    timestamp = datetime.now()
    safe_filename = f"dao_{case_id}_{timestamp.strftime('%Y%m%d%H%M%S')}_{file.filename}"
    file_path = UPLOADS_DIR / safe_filename
    with open(file_path, "wb") as f:
        f.write(content)

    # 5. Hash
    file_hash = compute_file_hash(file_path)

    # 6. Enregistrement artifact
    meta = {
        "original_filename": file.filename,
        "size_bytes": len(content),
        "mime_type": file.content_type,
        "hash": file_hash,
        "upload_timestamp": timestamp.isoformat(),
    }
    artifact_id = register_artifact(case_id, "dao", file.filename, str(file_path), meta)

    # 7. Extraction async (stub)
    from src.couche_a.extraction import extract_dao_content

    background_tasks.add_task(extract_dao_content, case_id, artifact_id, str(file_path))

    return {
        "artifact_id": artifact_id,
        "filename": file.filename,
        "status": "uploaded",
        "extraction_status": "pending",
    }


@router.post("/{case_id}/upload-offer")
async def upload_offer(
    case_id: str,
    background_tasks: BackgroundTasks,
    supplier_name: str = Form(...),
    offer_type: OfferType = Form(...),
    file: UploadFile = File(...),
):
    """Upload offre avec classification obligatoire."""
    # 1. Vérifier case existe
    with get_connection() as conn:
        case = db_execute_one(conn, "SELECT id FROM cases WHERE id=:id", {"id": case_id})
        if not case:
            raise HTTPException(404, "Case not found")

    # 2. Vérifier qu'un DAO existe déjà (logique métier)
    with get_connection() as conn:
        dao = db_execute_one(
            conn,
            "SELECT id FROM artifacts WHERE case_id=:cid AND kind='dao'",
            {"cid": case_id},
        )
        if not dao:
            raise HTTPException(400, "Cannot upload offer before DAO is uploaded.")

    # 3. Vérifier doublon fournisseur + type (PostgreSQL)
    with get_connection() as conn:
        existing = db_execute_one(
            conn,
            """
            SELECT id FROM artifacts
            WHERE case_id=:cid AND kind='offer'
              AND (meta_json::json)->>'supplier_name' = :supplier
              AND (meta_json::json)->>'offer_type' = :otype
            """,
            {"cid": case_id, "supplier": supplier_name, "otype": offer_type.value},
        )
        if existing:
            raise HTTPException(
                409,
                f"Offer of type '{offer_type.value}' already uploaded for supplier '{supplier_name}'.",
            )

    # 4. Validation type/taille
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, "Invalid file type. Allowed: PDF, DOCX, XLSX")
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large (max 50 MB)")

    # 5. Sauvegarde
    timestamp = datetime.now()
    ext = file.filename.split(".")[-1] if "." in file.filename else "pdf"
    safe_filename = (
        f"offer_{offer_type.value}_{supplier_name.replace(' ', '_')}_"
        f"{timestamp.strftime('%Y%m%d%H%M%S')}.{ext}"
    )
    file_path = UPLOADS_DIR / safe_filename
    with open(file_path, "wb") as f:
        f.write(content)

    # 6. Hash
    file_hash = compute_file_hash(file_path)

    # 7. Enregistrement artifact
    meta = {
        "supplier_name": supplier_name,
        "offer_type": offer_type.value,
        "original_filename": file.filename,
        "size_bytes": len(content),
        "mime_type": file.content_type,
        "hash": file_hash,
        "upload_timestamp": timestamp.isoformat(),
    }
    artifact_id = register_artifact(case_id, "offer", file.filename, str(file_path), meta)

    # 8. Extraction async (stub)
    from src.couche_a.extraction import extract_offer_content

    background_tasks.add_task(
        extract_offer_content,
        case_id,
        artifact_id,
        str(file_path),
        offer_type.value,
    )

    return {
        "artifact_id": artifact_id,
        "supplier_name": supplier_name,
        "offer_type": offer_type.value,
        "filename": file.filename,
        "timestamp": timestamp.isoformat(),
        "extraction_status": "pending",
    }
