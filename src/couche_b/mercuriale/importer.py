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


def _llamacloud_httpx_verify_tls() -> bool:
    """
    Vérification TLS du client httpx vers LlamaCloud (LlamaIndex), pas Mistral.

    Défaut : ``True`` (certificats vérifiés). Pour un proxy d'entreprise / inspection SSL
    qui casse la chaîne de confiance, désactiver **explicitement** avec
    ``LLAMACLOUD_HTTPX_VERIFY_SSL=0`` (ou ``false`` / ``no`` / ``off``).
    """
    raw = (os.environ.get("LLAMACLOUD_HTTPX_VERIFY_SSL") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    return True


_LLAMACLOUD_PAGE_LIMIT = 1000


def _split_pdf(source: Path, max_pages: int, tmp_dir: Path) -> list[Path]:
    """
    Découpe un PDF en chunks de max_pages pages.
    Retourne la liste des fichiers temporaires générés.
    Utilisé quand le PDF dépasse la limite LlamaCloud (1000 pages).
    """
    try:
        from pypdf import PdfReader, PdfWriter  # type: ignore[import]
    except ImportError as e:
        raise RuntimeError("pypdf non installé : pip install pypdf") from e

    reader = PdfReader(str(source))
    total = len(reader.pages)
    chunks: list[Path] = []

    for start in range(0, total, max_pages):
        end = min(start + max_pages, total)
        writer = PdfWriter()
        for i in range(start, end):
            writer.add_page(reader.pages[i])
        chunk_path = tmp_dir / f"{source.stem}_chunk_{start + 1}-{end}.pdf"
        with open(chunk_path, "wb") as f:
            writer.write(f)
        chunks.append(chunk_path)
        logger.info(
            "Split PDF · chunk %d/%d · pages %d-%d → %s",
            len(chunks),
            -(-total // max_pages),
            start + 1,
            end,
            chunk_path.name,
        )

    return chunks


async def _extract_one_chunk(
    file_path: Path,
    client: Any,
) -> str:
    """Upload + parse un chunk PDF via LlamaCloud. Retourne le markdown."""
    with open(file_path, "rb") as f:
        file_obj = await client.files.create(file=f, purpose="parse")

    result = await client.parsing.parse(
        file_id=file_obj.id,
        tier="agentic",
        version="latest",
        expand=["markdown_full"],
    )
    return result.markdown_full or ""


async def _llamacloud_extract(file_path: Path, api_key: str) -> str:
    """
    Extraction PDF via AsyncLlamaCloud.
    Partition automatique si > 1000 pages (limite LlamaCloud agentic).
    """
    import tempfile

    try:
        import httpx
        from llama_cloud import AsyncLlamaCloud  # type: ignore[import]
        from pypdf import PdfReader  # type: ignore[import]
    except ImportError as e:
        raise RuntimeError(
            f"Dépendance manquante : {e}. pip install llama-cloud pypdf"
        ) from e

    verify_tls = _llamacloud_httpx_verify_tls()
    if not verify_tls:
        logger.critical(
            "SECURITY: LLAMACLOUD_HTTPX_VERIFY_SSL désactive la vérification TLS du client "
            "httpx vers LlamaCloud. Risque MITM : la clé LLAMADMS / LLAMA_CLOUD_API_KEY et le "
            "contenu des PDF envoyés peuvent être interceptés. N'activer qu'avec accord explicite "
            "(ex. proxy d’entreprise / inspection SSL documentée)."
        )

    http_client = httpx.AsyncClient(verify=verify_tls)
    try:
        client = AsyncLlamaCloud(api_key=api_key, http_client=http_client)

        # Vérifier le nombre de pages
        reader = PdfReader(str(file_path))
        total_pages = len(reader.pages)
        logger.info("PDF %s · %d pages", file_path.name, total_pages)

        if total_pages <= _LLAMACLOUD_PAGE_LIMIT:
            # Cas standard : upload direct
            markdown = await _extract_one_chunk(file_path, client)
            if not markdown:
                raise ValueError(
                    f"LlamaCloud : markdown_full vide pour {file_path.name}"
                )
            logger.info("LlamaCloud · %s · %d chars", file_path.name, len(markdown))
            return markdown

        # Cas grand PDF : partition côté client
        logger.info(
            "PDF %s trop grand (%d pages > %d) · partition en chunks",
            file_path.name,
            total_pages,
            _LLAMACLOUD_PAGE_LIMIT,
        )
        parts: list[str] = []
        chunks: list[Path] = []
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp_dir = Path(tmp_str)
            chunks = _split_pdf(file_path, _LLAMACLOUD_PAGE_LIMIT, tmp_dir)
            for i, chunk in enumerate(chunks, 1):
                logger.info(
                    "Extraction chunk %d/%d : %s", i, len(chunks), chunk.name
                )
                md = await _extract_one_chunk(chunk, client)
                parts.append(md)

        markdown = "\n\n".join(p for p in parts if p)
        if not markdown:
            raise ValueError(
                f"LlamaCloud : tous les chunks vides pour {file_path.name}"
            )

        logger.info(
            "LlamaCloud · %s · %d chunks · %d chars total",
            file_path.name,
            len(chunks),
            len(markdown),
        )
        return markdown
    finally:
        await http_client.aclose()


_CACHE_DIR = Path("data/imports/m5/cache")


def _cache_path(file_path: Path) -> Path:
    """Chemin cache : data/imports/m5/cache/<sha256>.md"""
    sha = _sha256_file(file_path)
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR / f"{sha}.md"


def _extract_markdown_llamacloud(file_path: Path, api_key: str) -> tuple[str, float]:
    """
    Extrait le texte d'un PDF via LlamaCloud API (AsyncLlamaCloud).

    CACHE LOCAL : vérifie data/imports/m5/cache/<sha256>.md avant tout appel API.
    - CACHE HIT  → lecture locale, coût = 0
    - CACHE MISS → appel LlamaCloud → sauvegarde immédiate → parsing

    POINT DE MOCK OBLIGATOIRE dans les tests (RÈGLE-21).
    Mock target : src.couche_b.mercuriale.importer._extract_markdown_llamacloud

    Retourne (markdown_text, confidence_globale).
    """
    cache = _cache_path(file_path)

    if cache.exists():
        logger.info("CACHE HIT · %s → %s", file_path.name, cache.name)
        return cache.read_text(encoding="utf-8"), 0.90

    logger.info("CACHE MISS · %s · appel LlamaCloud", file_path.name)
    markdown = asyncio.run(_llamacloud_extract(file_path, api_key))

    # Sauvegarde immédiate AVANT parsing — survie garantie même si le parser crashe
    cache.write_text(markdown, encoding="utf-8")
    logger.info("Cache écrit · %s (%d chars)", cache.name, len(markdown))

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
    raw_lines = merc_parser.parse_html_to_lines(
        html_content=markdown,
        year=year,
        default_zone_raw=default_zone_raw,
    )
    report.total_rows_parsed = len(raw_lines)

    # Résolution zones — batch : 1 query par zone unique (anti N+1)
    unique_zones = {raw.get("zone_raw") for raw in raw_lines if raw.get("zone_raw")}
    zone_cache: dict[str, str | None] = {
        z: merc_repo.resolve_zone_id(z) for z in unique_zones
    }
    logger.info(
        "Zones uniques : %d · résolues : %d",
        len(unique_zones),
        sum(1 for v in zone_cache.values() if v),
    )

    # Validation + affectation zone_id depuis cache
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

        # Zone depuis cache — zéro query supplémentaire
        zone_raw = raw.get("zone_raw")
        if zone_raw:
            zone_id = zone_cache.get(zone_raw)
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
