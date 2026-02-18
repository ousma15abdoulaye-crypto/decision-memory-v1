"""
Couche A – Endpoints d'upload (Manuel SCI §4)
Constitution V2.1 : helpers synchrones src.db, pas de table SQLAlchemy.
"""

import hashlib
import json
import uuid
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)

from src.auth import CurrentUser, check_case_ownership
from src.db import db_execute, db_execute_one, db_fetchall, get_connection
from src.ratelimit import limiter
from src.upload_security import update_case_quota, validate_upload_security

router = APIRouter(prefix="/api/cases", tags=["Couche A Upload"])

UPLOADS_DIR = Path("data/uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class OfferType(StrEnum):
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


def register_artifact(
    case_id: str, kind: str, filename: str, path: str, meta: dict
) -> str:
    artifact_id = str(uuid.uuid4())
    created_by = meta.get("uploaded_by")  # Extract user_id from meta
    with get_connection() as conn:
        db_execute(
            conn,
            """
            INSERT INTO artifacts (id, case_id, kind, filename, path, uploaded_at, meta_json, created_by)
            VALUES (:id, :case_id, :kind, :filename, :path, :ts, :meta, :created_by)
            """,
            {
                "id": artifact_id,
                "case_id": case_id,
                "kind": kind,
                "filename": filename,
                "path": path,
                "ts": datetime.utcnow().isoformat(),
                "meta": json.dumps(meta, ensure_ascii=False),
                "created_by": created_by,
            },
        )
    return artifact_id


@router.post("/{case_id}/upload-dao")
@limiter.limit("5/minute")
async def upload_dao(
    request: Request,
    case_id: str,
    user: CurrentUser,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Upload du DAO – un seul par case (409 si existant). Requiert authentification."""
    # Ownership check
    check_case_ownership(case_id, user)

    with get_connection() as conn:
        case = db_execute_one(
            conn, "SELECT id FROM cases WHERE id=:id", {"id": case_id}
        )
        if not case:
            raise HTTPException(404, "Case not found")

    with get_connection() as conn:
        existing = db_execute_one(
            conn,
            "SELECT id FROM artifacts WHERE case_id=:cid AND kind='dao'",
            {"cid": case_id},
        )
        if existing:
            raise HTTPException(409, "DAO already uploaded. Delete existing DAO first.")

    # Validation sécurité complète (M4F)
    safe_name, mime, size = await validate_upload_security(file, case_id)

    timestamp = datetime.now()
    safe_filename = f"dao_{case_id}_{timestamp.strftime('%Y%m%d%H%M%S')}_{safe_name}"
    file_path = UPLOADS_DIR / safe_filename

    # Read and write full content after validation
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    file_hash = compute_file_hash(file_path)

    meta = {
        "original_filename": file.filename,
        "size_bytes": size,
        "mime_type": mime,
        "hash": file_hash,
        "upload_timestamp": timestamp.isoformat(),
        "uploaded_by": user["id"],
    }
    artifact_id = register_artifact(case_id, "dao", file.filename, str(file_path), meta)

    # Update quota after success
    update_case_quota(case_id, size)

    from src.couche_a.extraction import extract_dao_content

    background_tasks.add_task(extract_dao_content, case_id, artifact_id, str(file_path))

    return {
        "artifact_id": artifact_id,
        "filename": file.filename,
        "status": "uploaded",
        "extraction_status": "pending",
    }


@router.post("/{case_id}/upload-offer")
@limiter.limit("5/minute")
async def upload_offer(
    request: Request,
    case_id: str,
    user: CurrentUser,
    background_tasks: BackgroundTasks,
    supplier_name: str = Form(...),
    offer_type: OfferType = Form(...),
    file: UploadFile = File(...),
    lot_id: str = Form(None),
):
    """Upload offre avec classification obligatoire et lot optionnel. Requiert authentification."""
    # Ownership check
    check_case_ownership(case_id, user)

    with get_connection() as conn:
        case = db_execute_one(
            conn, "SELECT id, closing_date FROM cases WHERE id=:id", {"id": case_id}
        )
        if not case:
            raise HTTPException(404, "Case not found")
        closing_date = case.get("closing_date") if isinstance(case, dict) else None

    # Valider lot_id si fourni
    if lot_id:
        with get_connection() as conn:
            lot = db_execute_one(
                conn, "SELECT id, case_id FROM lots WHERE id=:lid", {"lid": lot_id}
            )
            if not lot:
                raise HTTPException(404, f"Lot '{lot_id}' not found")
            lot_case_id = lot.get("case_id") if isinstance(lot, dict) else lot[1]
            if lot_case_id != case_id:
                raise HTTPException(
                    400, f"Lot '{lot_id}' does not belong to case '{case_id}'"
                )

    with get_connection() as conn:
        dao = db_execute_one(
            conn,
            "SELECT id FROM artifacts WHERE case_id=:cid AND kind='dao'",
            {"cid": case_id},
        )
        if not dao:
            raise HTTPException(400, "Cannot upload offer before DAO is uploaded.")

    with get_connection() as conn:
        existing = db_execute_one(
            conn,
            """
            SELECT id FROM artifacts
            WHERE case_id=:cid AND kind='offer'
              AND meta_json LIKE :supplier_pattern
              AND meta_json LIKE :otype_pattern
            """,
            {
                "cid": case_id,
                "supplier_pattern": f'%"supplier_name": "{supplier_name}"%',
                "otype_pattern": f'%"offer_type": "{offer_type.value}"%',
            },
        )
        if existing:
            raise HTTPException(
                409,
                f"Offer of type '{offer_type.value}' already uploaded for supplier '{supplier_name}'.",
            )

    # Validation sécurité complète (M4F)
    safe_name, mime, size = await validate_upload_security(file, case_id)

    timestamp = datetime.now()
    ext = safe_name.split(".")[-1] if "." in safe_name else "pdf"
    safe_filename = f"offer_{offer_type.value}_{supplier_name.replace(' ', '_')}_{timestamp.strftime('%Y%m%d%H%M%S')}.{ext}"
    file_path = UPLOADS_DIR / safe_filename

    # Read and write full content after validation
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    file_hash = compute_file_hash(file_path)

    # Déterminer si l'offre est hors délai
    is_late = False
    if closing_date:
        try:
            closing_dt = datetime.fromisoformat(closing_date)
            is_late = timestamp > closing_dt
        except (ValueError, TypeError):
            pass  # Si closing_date invalide, on considère not late

    meta = {
        "supplier_name": supplier_name,
        "offer_type": offer_type.value,
        "original_filename": file.filename,
        "size_bytes": size,
        "mime_type": mime,
        "hash": file_hash,
        "upload_timestamp": timestamp.isoformat(),
        "lot_id": lot_id,
        "is_late": is_late,
        "uploaded_by": user["id"],
    }
    artifact_id = register_artifact(
        case_id, "offer", file.filename, str(file_path), meta
    )

    # Update quota after success
    update_case_quota(case_id, size)

    from src.couche_a.extraction import extract_offer_content

    background_tasks.add_task(
        extract_offer_content, case_id, artifact_id, str(file_path), offer_type.value
    )

    return {
        "artifact_id": artifact_id,
        "supplier_name": supplier_name,
        "offer_type": offer_type.value,
        "filename": file.filename,
        "timestamp": timestamp.isoformat(),
        "lot_id": lot_id,
        "is_late": is_late,
        "extraction_status": "pending",
    }


@router.get("/{case_id}/criteria/validation")
@limiter.limit("10/minute")
async def get_criteria_validation(request: Request, case_id: str, user: CurrentUser):
    """Récupère la dernière validation des pondérations pour un case."""
    # Ownership check
    check_case_ownership(case_id, user)

    with get_connection() as conn:
        row = db_execute_one(
            conn,
            """
            SELECT commercial_weight, sustainability_weight, is_valid, validation_errors
            FROM criteria_weighting_validation
            WHERE case_id = :cid
            ORDER BY created_at DESC
            LIMIT 1
            """,
            {"cid": case_id},
        )
    if not row:
        raise HTTPException(404, "Aucune validation trouvée pour ce case")
    return {
        "case_id": case_id,
        "commercial_weight": row["commercial_weight"],
        "sustainability_weight": row["sustainability_weight"],
        "is_valid": row["is_valid"],
        "errors": (
            row["validation_errors"].split("\n") if row["validation_errors"] else []
        ),
    }


@router.get("/{case_id}/criteria/by-category")
@limiter.limit("10/minute")
async def get_criteria_by_category(request: Request, case_id: str, user: CurrentUser):
    """Retourne les critères groupés par catégorie."""
    # Ownership check
    check_case_ownership(case_id, user)

    with get_connection() as conn:
        rows = db_fetchall(
            conn,
            """
            SELECT criterion_category, critere_nom, description, ponderation, is_eliminatory
            FROM dao_criteria
            WHERE case_id = :cid
            ORDER BY criterion_category, ordre_affichage
            """,
            {"cid": case_id},
        )
    grouped = {}
    for r in rows:
        cat = r["criterion_category"]
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(
            {
                "nom": r["critere_nom"],
                "description": r["description"],
                "ponderation": r["ponderation"],
                "is_eliminatory": r["is_eliminatory"],
            }
        )
    return {"case_id": case_id, "criteria_by_category": grouped}
