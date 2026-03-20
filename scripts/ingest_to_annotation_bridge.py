#!/usr/bin/env python3
"""
M-INGEST-TO-ANNOTATION-BRIDGE-00 — PDFs externes → JSON type Label Studio.

- Pas de copie des PDF dans le dépôt, pas d’écriture DB.
- Texte final depuis extracteurs réels (local pypdf/pdfminer, LlamaParse, Mistral OCR).
- Classification PDF : sonde locale uniquement (``extract_pdf_text_local_only``), sans LlamaParse.
- Mesure des changements Git : uniquement par rapport au commit baseline figé au démarrage du mandat.

Run 1 (défaut CTO) :
  SOURCE_ROOT  = C:\\Users\\...\\Desktop\\test mistral
  OUTPUT_ROOT  = C:\\Users\\...\\Desktop\\DMS_ANNOTATION_OUTPUT
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# Projet racine
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.core.api_keys import APIKeyMissingError  # noqa: E402
from src.couche_a.extraction import extract_pdf_text_local_only  # noqa: E402
from src.extraction.engine import (  # noqa: E402
    _extract_llamaparse,
    _extract_mistral_ocr,
)

logger = logging.getLogger(__name__)

DEFAULT_SOURCE_ROOTS = [
    os.path.join(os.path.expanduser("~"), "Desktop", "test mistral"),
]
DEFAULT_OUTPUT_ROOT = os.path.join(
    os.path.expanduser("~"), "Desktop", "DMS_ANNOTATION_OUTPUT"
)

# Seuils heuristiques (fichier uniquement — pas de routage par nom de dossier)
_MIN_NATIVE_CHARS = 100
_MIN_SCAN_CHARS = 50
_PDF_MAGIC = b"%PDF"
_PDF_SNIFF_BYTES = 256 * 1024


@dataclass
class PdfRecord:
    path: str
    process_name: str
    classification: str  # native_pdf | scanned_pdf | mixed_pdf | rejected
    engine_route: str  # local | llamaparse | mistral_ocr | blocked
    text: str
    skip_reason: str | None = None


def _is_pdf_magic(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            return fh.read(4) == _PDF_MAGIC
    except OSError:
        return False


def _image_marker_density(path: Path) -> float:
    """Part approximative du fichier occupée par des marqueurs /Image (heuristique)."""
    try:
        raw = path.read_bytes()[:_PDF_SNIFF_BYTES]
    except OSError:
        return 0.0
    if not raw:
        return 0.0
    return raw.count(b"/Image") / max(len(raw), 1)


def classify_pdf(path: Path, text_probe: str) -> str:
    """Classification à partir du fichier + texte issu d'extracteurs locaux (pypdf/pdfminer)."""
    if path.suffix.lower() != ".pdf":
        return "rejected"
    if not _is_pdf_magic(path):
        return "rejected"
    stripped = text_probe.strip()
    img_d = _image_marker_density(path)
    if len(stripped) >= _MIN_NATIVE_CHARS and img_d < 0.002:
        return "native_pdf"
    if len(stripped) >= _MIN_NATIVE_CHARS and img_d >= 0.002:
        return "mixed_pdf"
    if len(stripped) < _MIN_SCAN_CHARS:
        return "scanned_pdf"
    return "mixed_pdf"


def extract_with_route(
    path: str,
    classification: str,
    text_after_local_extract: str,
) -> tuple[str, str, str | None]:
    """
    Retourne (texte, engine_route, skip_reason).
    Ne fabrique jamais de texte : chaîne vide si aucun extracteur ne produit de contenu.
    ``text_after_local_extract`` : texte pypdf/pdfminer (même source que la classification).
    """
    p = Path(path)
    real = str(p.resolve())

    if classification == "rejected":
        return "", "blocked", "not_pdf_or_corrupt"

    stripped = text_after_local_extract.strip()

    # PDF majoritairement lisible en local
    if classification == "native_pdf" and len(stripped) >= _MIN_NATIVE_CHARS:
        return text_after_local_extract, "local", None

    if classification == "mixed_pdf" and len(stripped) >= _MIN_NATIVE_CHARS:
        return text_after_local_extract, "local", None

    # STORAGE_BASE_PATH : positionné au démarrage de run_ingest() (première racine).

    # Besoin d’un moteur cloud
    if (
        classification in ("scanned_pdf", "mixed_pdf")
        or len(stripped) < _MIN_NATIVE_CHARS
    ):
        try:
            raw, _ = _extract_mistral_ocr(real)
            if raw and raw.strip():
                return raw, "mistral_ocr", None
        except (
            APIKeyMissingError,
            ImportError,
            ValueError,
            OSError,
            RuntimeError,
        ) as e:
            logger.info("[BRIDGE] mistral_ocr indisponible ou échec — %s", e)

        try:
            raw, _ = _extract_llamaparse(real)
            if raw and raw.strip():
                return raw, "llamaparse", None
        except (
            APIKeyMissingError,
            ImportError,
            ValueError,
            OSError,
            RuntimeError,
        ) as e:
            logger.info("[BRIDGE] llamaparse indisponible ou échec — %s", e)

    if stripped:
        return text_after_local_extract, "local", None

    return "", "blocked", "no_text_all_extractors"


def discover_pdfs(source_roots: list[str]) -> list[Path]:
    out: list[Path] = []
    for root in source_roots:
        r = Path(root)
        if not r.is_dir():
            logger.warning("[BRIDGE] source ignorée (pas un dossier) : %s", root)
            continue
        out.extend(sorted(r.rglob("*.pdf")))
        out.extend(sorted(r.rglob("*.PDF")))
    # dédoublonne casse
    seen: set[str] = set()
    unique: list[Path] = []
    for p in out:
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def build_ls_task(
    rec: PdfRecord,
    default_document_role: str,
    run_id: str,
) -> dict:
    rel = rec.path
    source_tag = f"{rec.process_name}:{Path(rec.path).name}"
    return {
        "data": {
            "text": rec.text,
            "document_role": default_document_role,
            "source": source_tag,
            "process_name": rec.process_name,
            "source_path": rel,
            "ingest_run_id": run_id,
            "pdf_classification": rec.classification,
            "engine_route": rec.engine_route,
        }
    }


def run_ingest(
    source_roots: list[str],
    output_root: str,
    default_document_role: str,
    run_id: str | None = None,
    ingest_limit: int | None = None,
) -> dict:
    if not source_roots:
        raise ValueError(
            "source_roots ne peut pas être vide — fournir au moins une racine dossier."
        )
    run_id = run_id or f"bridge-{uuid.uuid4().hex[:12]}"
    out_dir = Path(output_root)
    out_dir.mkdir(parents=True, exist_ok=True)

    # DETTE TECHNIQUE : mutation globale confinée à ce seul point.
    # Découplage réel = mandat ultérieur dédié.
    storage_base = str(source_roots[0]) if source_roots else ""
    os.environ["STORAGE_BASE_PATH"] = storage_base
    logger.info("[BRIDGE] STORAGE_BASE_PATH=%s", storage_base)

    all_pdfs = discover_pdfs(source_roots)
    pdfs = (
        all_pdfs[:ingest_limit]
        if ingest_limit is not None and ingest_limit >= 0
        else all_pdfs
    )
    records: list[PdfRecord] = []
    skipped: list[dict] = []

    for pdf in pdfs:
        path_str = str(pdf.resolve())
        process_name = pdf.parent.name or "."
        text_probe = (
            extract_pdf_text_local_only(path_str)
            if pdf.suffix.lower() == ".pdf"
            else ""
        )
        klass = classify_pdf(pdf, text_probe)

        if klass == "rejected":
            skipped.append(
                {
                    "path": path_str,
                    "process_name": process_name,
                    "reason": "rejected_classification",
                    "classification": klass,
                }
            )
            continue

        text, route, skip_reason = extract_with_route(path_str, klass, text_probe)
        if not text.strip():
            skipped.append(
                {
                    "path": path_str,
                    "process_name": process_name,
                    "reason": skip_reason or "empty_text",
                    "classification": klass,
                    "engine_route": route,
                }
            )
            continue

        records.append(
            PdfRecord(
                path=path_str,
                process_name=process_name,
                classification=klass,
                engine_route=route,
                text=text,
                skip_reason=None,
            )
        )

    skip_by_classification: dict[str, int] = {}
    skip_by_reason: dict[str, int] = {}
    for s in skipped:
        cls = s.get("classification", "unknown")
        reason = s.get("reason", "unknown")
        skip_by_classification[cls] = skip_by_classification.get(cls, 0) + 1
        skip_by_reason[reason] = skip_by_reason.get(reason, 0) + 1

    manifest = {
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "source_roots": source_roots,
        "output_root": str(out_dir.resolve()),
        "default_document_role": default_document_role,
        "ingest_limit": ingest_limit,
        "pdf_files_discovered": len(all_pdfs),
        "pdf_files_seen": len(pdfs),
        "tasks_emitted": len(records),
        "tasks_skipped": len(skipped),
    }

    ls_tasks = [build_ls_task(r, default_document_role, run_id) for r in records]

    report = {
        **manifest,
        "by_classification": {},
        "by_engine": {},
        "skip_by_classification": skip_by_classification,
        "skip_by_reason": skip_by_reason,
    }
    for r in records:
        report["by_classification"][r.classification] = (
            report["by_classification"].get(r.classification, 0) + 1
        )
        report["by_engine"][r.engine_route] = (
            report["by_engine"].get(r.engine_route, 0) + 1
        )

    (out_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "ls_tasks.json").write_text(
        json.dumps(ls_tasks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "skipped.json").write_text(
        json.dumps(skipped, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "ingest_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return report


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Ingestion PDF → ls_tasks.json (Label Studio / predict DMS)."
    )
    parser.add_argument(
        "--source-root",
        action="append",
        dest="source_roots",
        help="Dossier source (répéter l’option pour plusieurs racines). "
        "Défaut : ~/Desktop/test mistral",
    )
    parser.add_argument(
        "--output-root",
        default=DEFAULT_OUTPUT_ROOT,
        help=f"Dossier sortie (défaut : {DEFAULT_OUTPUT_ROOT})",
    )
    parser.add_argument(
        "--default-document-role",
        default=os.environ.get("BRIDGE_DEFAULT_DOCUMENT_ROLE", "supporting_doc"),
        help="Valeur data.document_role pour chaque tâche (défaut : supporting_doc).",
    )
    parser.add_argument("--run-id", default=None, help="Identifiant de run explicite.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Nombre max de PDFs à traiter (ordre rglob), ex. 100 pour un batch offres.",
    )
    args = parser.parse_args()

    roots = args.source_roots if args.source_roots else DEFAULT_SOURCE_ROOTS
    report = run_ingest(
        source_roots=roots,
        output_root=args.output_root,
        default_document_role=args.default_document_role,
        run_id=args.run_id,
        ingest_limit=args.limit,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
