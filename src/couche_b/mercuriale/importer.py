"""
Importer mercuriale PDF → DB — DMS V4.1.0

RÈGLE-29 : ingestion brute
RÈGLE-21 : _extract_markdown_llamacloud est le point de mock pour les tests
API     : llama_cloud.AsyncLlamaCloud · variable LLAMADMS (Railway)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from pathlib import Path
from typing import Any

from src.couche_b.mercuriale import ingest_parser as merc_parser
from src.couche_b.mercuriale import repository as merc_repo
from src.couche_b.mercuriale.models import ImportReport, MercurialLineCreate

logger = logging.getLogger(__name__)

CONFIDENCE_REJECT_THRESHOLD = 0.60


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _get_api_key() -> str:
    """Lit la clé depuis LLAMADMS (Railway) ou LLAMA_CLOUD_API_KEY (fallback local)."""
    return (
        os.environ.get("LLAMADMS", "").strip()
        or os.environ.get("LLAMA_CLOUD_API_KEY", "").strip()
    )


async def _llamacloud_extract(file_path: Path, api_key: str) -> str:
    """Extraction PDF via AsyncLlamaCloud — wrapper async interne."""
    try:
        from llama_cloud import AsyncLlamaCloud  # type: ignore[import]
    except ImportError as e:
        raise RuntimeError(
            f"llama_cloud non installé : {e}. pip install llama-cloud"
        ) from e

    client = AsyncLlamaCloud(api_key=api_key)

    with open(file_path, "rb") as f:
        file_obj = await client.files.create(file=f, purpose="parse")

    result = await client.parsing.parse(
        file_id=file_obj.id,
        tier="agentic",
        version="latest",
        expand=["markdown_full"],
    )

    if not result.markdown_full:
        raise ValueError(f"LlamaCloud : markdown_full vide pour {file_path.name}")

    logger.info(
        "LlamaCloud · %s · %d chars extraits",
        file_path.name,
        len(result.markdown_full),
    )
    return result.markdown_full


def _extract_markdown_llamacloud(file_path: Path, api_key: str) -> tuple[str, float]:
    """
    Extrait le texte d'un PDF via LlamaCloud API (AsyncLlamaCloud).

    POINT DE MOCK OBLIGATOIRE dans les tests (RÈGLE-21).
    Mock target : src.couche_b.mercuriale.importer._extract_markdown_llamacloud

    Retourne (markdown_text, confidence_globale).
    """
    markdown = asyncio.run(_llamacloud_extract(file_path, api_key))
    return markdown, 0.90


def import_mercuriale(
    filepath: Path,
    year: int,
    source_type: str = "official_dgmp",
    default_zone_raw: str | None = None,
    dry_run: bool = False,
) -> ImportReport:
    """
    Import complet d'un fichier mercuriale PDF.

    dry_run = True :
      Appelle LlamaCloud ET parse les données
      mais ZÉRO INSERT en DB.
      Permet de valider la qualité avant commit.
      Dans les tests : mocker _extract_markdown_llamacloud.
    """
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError(
            "Clé API absente. "
            "Exporter $env:LLAMADMS localement ou vérifier Railway Dashboard."
        )

    report = ImportReport(
        filename=filepath.name,
        year=year,
        sha256=_sha256_file(filepath),
        dry_run=dry_run,
    )

    # Idempotence SHA256 (skip si déjà importé · dry_run ne vérifie pas)
    if not dry_run and merc_repo.source_exists_by_sha256(report.sha256):
        logger.info("%s déjà importé · skip", filepath.name)
        report.already_imported = True
        return report

    # Extraction
    try:
        markdown, _ = _extract_markdown_llamacloud(filepath, api_key)
    except Exception as e:
        report.errors.append(f"Extraction échouée : {e}")
        logger.error("Extraction échouée : %s", e)
        return report

    # Parsing
    raw_lines = merc_parser.parse_markdown_to_lines(
        markdown=markdown,
        year=year,
        default_zone_raw=default_zone_raw,
    )
    report.total_rows_parsed = len(raw_lines)

    # Validation + résolution zones
    valid_lines: list[dict[str, Any]] = []
    for raw in raw_lines:
        if not raw.get("item_canonical", "").strip():
            report.skipped_empty += 1
            continue

        if raw.get("price_avg") is None:
            report.skipped_price_invalid += 1
            continue

        if raw.get("confidence", 1.0) < CONFIDENCE_REJECT_THRESHOLD:
            report.skipped_low_confidence += 1
            continue

        # Résolution zone
        zone_raw = raw.get("zone_raw")
        if zone_raw:
            zone_id = merc_repo.resolve_zone_id(zone_raw)
            if zone_id:
                report.zones_resolved += 1
                raw["zone_id"] = zone_id
            else:
                report.zones_unresolved += 1
                raw["zone_id"] = None
                raw.setdefault("extraction_metadata", {})["zone_unresolved"] = True
        else:
            report.zones_unresolved += 1
            raw["zone_id"] = None

        # Validation Pydantic
        try:
            validated = MercurialLineCreate(
                source_id="00000000-0000-0000-0000-000000000000",
                **{k: v for k, v in raw.items() if k != "source_id"},
            )
            if validated.review_required:
                report.review_required += 1
        except Exception as e:
            report.errors.append(f"Validation : {raw.get('item_canonical')} → {e}")
            continue

        valid_lines.append(raw)

    if dry_run:
        report.inserted = len(valid_lines)
        logger.info(
            "DRY-RUN · %d lignes valides · coverage=%.1f%%",
            len(valid_lines),
            report.coverage_pct,
        )
        return report

    # INSERT source
    source = merc_repo.insert_source(
        {
            "filename": filepath.name,
            "sha256": report.sha256,
            "year": year,
            "source_type": source_type,
            "extraction_engine": "llamacloud",
            "notes": None,
        }
    )
    if not source:
        report.errors.append("INSERT source échoué")
        return report

    source_id = str(source["id"])
    for line in valid_lines:
        line["source_id"] = source_id

    # INSERT batch
    try:
        report.inserted = merc_repo.insert_mercurial_lines_batch(valid_lines)
    except Exception as e:
        report.errors.append(f"INSERT batch : {e}")
        merc_repo.update_source_status(source_id, "failed")
        return report

    status = "done" if not report.errors else "partial"
    merc_repo.update_source_status(source_id, status, report.inserted)

    logger.info(
        "Import · %s · %d insérées · coverage=%.1f%%",
        filepath.name,
        report.inserted,
        report.coverage_pct,
    )
    return report
