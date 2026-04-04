"""Validation déterministe du ZIP — AVANT tout appel LLM.

Règle : 0 token consommé si le ZIP est invalide (gate S4-S5).
Validation pre-LLM = rapide, pas de coût API.

Checks effectués :
  1. Format ZIP valide (non corrompu)
  2. Taille totale < MAX_ZIP_SIZE_MB
  3. Au moins 1 fichier dans le ZIP
  4. Extensions autorisées uniquement (whitelist ALLOWED_EXTENSIONS)
  5. Pas de path traversal (../ dans les noms de fichiers)

Référence : Plan V4.2.0 Phase 4 — src/assembler/zip_validator.py
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

MAX_ZIP_SIZE_MB = 100
MAX_FILES_PER_ZIP = 200

ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    [
        ".pdf",
        ".docx",
        ".doc",
        ".xlsx",
        ".xls",
        ".jpg",
        ".jpeg",
        ".png",
        ".tiff",
        ".tif",
    ]
)


@dataclass
class ZipValidationResult:
    """Résultat de la validation déterministe."""

    is_valid: bool
    error: str | None
    file_count: int
    total_size_bytes: int
    filenames: list[str]


def validate_zip(zip_path: str | Path) -> ZipValidationResult:
    """Valide un fichier ZIP avant tout appel LLM.

    Returns:
        ZipValidationResult avec is_valid=False + error si invalide.
        Lève 422 (ValueError) en cas de problème critique.
    """
    path = Path(zip_path)

    if not path.exists():
        return ZipValidationResult(
            is_valid=False,
            error=f"Fichier introuvable : {path}",
            file_count=0,
            total_size_bytes=0,
            filenames=[],
        )

    total_size = path.stat().st_size
    if total_size > MAX_ZIP_SIZE_MB * 1024 * 1024:
        return ZipValidationResult(
            is_valid=False,
            error=f"ZIP trop volumineux : {total_size // 1024 // 1024}MB > {MAX_ZIP_SIZE_MB}MB",
            file_count=0,
            total_size_bytes=total_size,
            filenames=[],
        )

    try:
        with zipfile.ZipFile(path, "r") as zf:
            if zf.testzip() is not None:
                return ZipValidationResult(
                    is_valid=False,
                    error="ZIP corrompu — testzip() a détecté une erreur.",
                    file_count=0,
                    total_size_bytes=total_size,
                    filenames=[],
                )

            namelist = zf.namelist()
            if not namelist:
                return ZipValidationResult(
                    is_valid=False,
                    error="ZIP vide — aucun fichier.",
                    file_count=0,
                    total_size_bytes=total_size,
                    filenames=[],
                )

            if len(namelist) > MAX_FILES_PER_ZIP:
                return ZipValidationResult(
                    is_valid=False,
                    error=(
                        f"ZIP contient {len(namelist)} fichiers > "
                        f"limite {MAX_FILES_PER_ZIP}."
                    ),
                    file_count=len(namelist),
                    total_size_bytes=total_size,
                    filenames=[],
                )

            filenames = []
            for name in namelist:
                if ".." in name or name.startswith("/"):
                    return ZipValidationResult(
                        is_valid=False,
                        error=f"Path traversal détecté : {name!r}",
                        file_count=len(namelist),
                        total_size_bytes=total_size,
                        filenames=[],
                    )

                if name.endswith("/"):
                    continue

                ext = Path(name).suffix.lower()
                if ext not in ALLOWED_EXTENSIONS:
                    return ZipValidationResult(
                        is_valid=False,
                        error=(
                            f"Extension non autorisée : {ext!r} ({name}). "
                            f"Autorisées : {sorted(ALLOWED_EXTENSIONS)}"
                        ),
                        file_count=len(namelist),
                        total_size_bytes=total_size,
                        filenames=[],
                    )

                filenames.append(name)

    except zipfile.BadZipFile as exc:
        return ZipValidationResult(
            is_valid=False,
            error=f"Format ZIP invalide : {exc}",
            file_count=0,
            total_size_bytes=total_size,
            filenames=[],
        )

    return ZipValidationResult(
        is_valid=True,
        error=None,
        file_count=len(filenames),
        total_size_bytes=total_size,
        filenames=filenames,
    )
