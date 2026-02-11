"""
Couche A – Endpoints d'upload (Manuel SCI §4)
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from src.couche_a.extraction import extract_dao_content, extract_offer_content
from src.db import db_execute, db_execute_one, get_connection

router = APIRouter(prefix="/api/cases", tags=["Couche A - Upload"])

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
    """Calcule SHA256 du fichier pour détection doublon."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def register_artifact(
    case_id: str, kind: str, filename: str, path: str, meta: dict
) -> str:
    """Insère un artifact dans la base et retourne son ID."""
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
    """
    Upload du DAO/RFQ – Un seul par case.
    - Vérifie existence case
    - Vérifie absence de DAO déjà uploadé → 409
    - Valide type/taille
    - Sauvegarde avec hash
    - Enregistre artifact
    - Lance extraction async
    """
    # 1. Vérifier que la case existe
    case = db_execute_one("SELECT id FROM cases WHERE id=:id", {"id": case_id})
    if not case:
        raise HTTPException(404, "Case not found")

    # 2. Vérifier qu'aucun DAO n'est déjà uploadé pour cette case
    existing = db_execute_one(
        "SELECT id FROM artifacts WHERE case_id=:cid AND kind='dao'",
        {"cid": case_id},
    )
    if existing:
        raise HTTPException(
            409,
            "DAO already uploaded for this case. Delete existing DAO first.",
        )

    # 3. Valider le type MIME
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            400,
            f"Invalid file type. Allowed: PDF, DOCX, XLSX. Got: {file.content_type}",
        )

    # 4. Valider la taille
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_FILE_SIZE:
        raise HTTPException(
            413, f"File too large (max {MAX_FILE_SIZE/1024/1024} MB)"
        )

    # 5. Sauvegarder le fichier
    timestamp = datetime.now()
    safe_filename = (
        f"dao_{case_id}_{timestamp.strftime('%Y%m%d%H%M%S')}_{file.filename}"
    )
    file_path = UPLOADS_DIR / safe_filename
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # 6. Calculer le hash
    file_hash = compute_file_hash(file_path)

    # 7. Enregistrer l'artifact
    meta = {
        "original_filename": file.filename,
        "size_bytes": size,
        "mime_type": file.content_type,
        "hash": file_hash,
        "upload_timestamp": timestamp.isoformat(),
    }
    artifact_id = register_artifact(case_id, "dao", file.filename, str(file_path), meta)

    # 8. Lancer l'extraction en arrière‑plan
    background_tasks.add_task(
            extract_dao_content, case_id, artifact_id, str(file_path)
        )

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
    """
    Upload d'une offre avec classification obligatoire.
    - Vérifie existence case
    - Vérifie doublon (même fournisseur + même type) → 409
    - Valide type/taille
    - Sauvegarde avec métadonnées enrichies
    - Lance extraction async selon le type
    """
    # 1. Vérifier que la case existe
    case = db_execute_one("SELECT id FROM cases WHERE id=:id", {"id": case_id})
    if not case:
        raise HTTPException(404, "Case not found")

    # 2. Vérifier doublon (même fournisseur, même type)
    # PostgreSQL: meta_json is TEXT, cast to json for extraction
    existing = db_execute_one(
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
            f"Offre {offer_type.value} déjà uploadée pour {supplier_name}. "
            "Veuillez supprimer l'offre existante d'abord.",
        )

    # 3. Valider le type MIME
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            400,
            f"Invalid file type. Allowed: PDF, DOCX, XLSX. Got: {file.content_type}",
        )

    # 4. Valider la taille
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_FILE_SIZE:
        raise HTTPException(
            413, f"File too large (max {MAX_FILE_SIZE/1024/1024} MB)"
        )

    # 5. Sauvegarder le fichier
    timestamp = datetime.now()
    safe_filename = (
        f"offer_{offer_type.value}_{supplier_name.replace(' ', '_')}_"
        f"{timestamp.strftime('%Y%m%d%H%M%S')}.pdf"
    )
    if file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        safe_filename = safe_filename.replace(".pdf", ".docx")
    elif file.content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        safe_filename = safe_filename.replace(".pdf", ".xlsx")

    file_path = UPLOADS_DIR / safe_filename
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # 6. Calculer le hash
    file_hash = compute_file_hash(file_path)

    # 7. Enregistrer l'artifact avec métadonnées complètes
    meta = {
        "supplier_name": supplier_name,
        "offer_type": offer_type.value,
        "original_filename": file.filename,
        "size_bytes": size,
        "mime_type": file.content_type,
        "hash": file_hash,
        "upload_timestamp": timestamp.isoformat(),
    }
    artifact_id = register_artifact(case_id, "offer", file.filename, str(file_path), meta)

    # 8. Lancer l'extraction en arrière‑plan selon le type
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
