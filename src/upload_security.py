"""Upload security validation (M4F)."""

import filetype
from fastapi import HTTPException, UploadFile
from werkzeug.utils import secure_filename

from src.db import db_execute, db_execute_one, get_connection

# Configuration
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB par fichier
MAX_CASE_TOTAL = 500 * 1024 * 1024  # 500 MB total par case

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/msword",
    "application/vnd.ms-excel",
}


def validate_filename(filename: str) -> str:
    """Sécurise nom de fichier (prévient path traversal)."""
    safe_name = secure_filename(filename)
    if not safe_name or safe_name != filename:
        raise HTTPException(400, f"Invalid filename: {filename}")
    return safe_name


async def validate_mime_type(file: UploadFile) -> str:
    """Valide MIME type réel du fichier (pas juste extension)."""
    # Lire premiers 2048 octets pour détection
    content = await file.read(2048)
    await file.seek(0)  # Reset pour lecture complète après

    kind = filetype.guess(content)
    if kind is None:
        raise HTTPException(400, "Unable to determine file type")

    mime = kind.mime

    if mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, f"Invalid file type: {mime}. Allowed: PDF, Word, Excel")

    return mime


async def validate_file_size(file: UploadFile) -> int:
    """Valide taille fichier."""
    # Read entire file to get size, then reset
    content = await file.read()
    size = len(content)
    await file.seek(0)  # Reset to beginning

    if size > MAX_UPLOAD_SIZE:
        raise HTTPException(413, f"File too large: {size} bytes (max {MAX_UPLOAD_SIZE / 1024 / 1024} MB)")

    return size


def check_case_quota(case_id: str, new_file_size: int):
    """Vérifie quota cumulé du case."""
    with get_connection() as conn:
        case = db_execute_one(conn, "SELECT total_upload_size FROM cases WHERE id = :id", {"id": case_id})

        if not case:
            raise HTTPException(404, "Case not found")

        current_total = case["total_upload_size"] or 0
        new_total = current_total + new_file_size

        if new_total > MAX_CASE_TOTAL:
            raise HTTPException(
                413, f"Case quota exceeded: {new_total / 1024 / 1024:.2f} MB / {MAX_CASE_TOTAL / 1024 / 1024} MB"
            )


def update_case_quota(case_id: str, file_size: int):
    """Met à jour quota cumulé après upload réussi."""
    with get_connection() as conn:
        db_execute(
            conn,
            "UPDATE cases SET total_upload_size = total_upload_size + :size WHERE id = :id",
            {"size": file_size, "id": case_id},
        )


async def validate_upload_security(file: UploadFile, case_id: str) -> tuple[str, str, int]:
    """
    Validation sécurité complète upload (M4F).

    Returns:
        (safe_filename, mime_type, file_size)
    """
    # 1. Filename sécurisé
    safe_name = validate_filename(file.filename)

    # 2. MIME type réel
    mime = await validate_mime_type(file)

    # 3. Taille fichier
    size = await validate_file_size(file)

    # 4. Quota case
    check_case_quota(case_id, size)

    return safe_name, mime, size
