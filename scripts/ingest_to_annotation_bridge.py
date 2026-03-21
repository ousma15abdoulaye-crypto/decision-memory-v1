#!/usr/bin/env python3
"""
M-INGEST-TO-ANNOTATION-BRIDGE-00 — PDFs externes → JSON type Label Studio.

- Pas de copie des PDF dans le dépôt, pas d’écriture DB.
- Texte final depuis extracteurs réels (local pypdf/pdfminer, LlamaParse, Mistral OCR).
- Classification PDF : sonde locale uniquement (``extract_pdf_text_local_only``), sans LlamaParse.
- Mesure des changements Git : uniquement par rapport au commit baseline figé au démarrage du mandat.

Chaque tâche inclut ``data.structured_preview`` (tables sur les N premières pages, pdfplumber).
Désactiver : ``--structured-preview-pages 0``.

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

from src.annotation.structured_pdf_preview import (  # noqa: E402
    structured_preview_from_pdf,
)
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

    # STORAGE_BASE_PATH : positionné dans run_ingest() (FIX-01, voir _storage_base_for_bridge).

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


def _classify_to_document_role(classification: str, filename: str) -> str:
    """
    Déduit un document_role initial depuis la classification PDF
    et le nom de fichier. Heuristique — corrigeable par l'annotateur.
    """
    _ = classification  # réservé (alignement API / évolutions futures)
    name_upper = Path(filename).name.upper()
    if any(
        k in name_upper
        for k in (
            "PROPOSITION FINANCIERE",
            "OFFRE FINANCIERE",
            "OFFRE FIN",
            "FINANCIAL",
            "BORDEREAU",
        )
    ):
        return "financial_offer"
    if any(
        k in name_upper
        for k in (
            "OFFRE TECHNIQUE",
            "PROPOSITION TECHNIQUE",
            "OFFER TECH",
            "TECHNIQUE",
        )
    ):
        return "offer_technical"
    if any(
        k in name_upper
        for k in (
            "TDR",
            "TERMES DE REFERENCE",
            "TERMS OF REFERENCE",
        )
    ):
        return "source_rules"
    if any(
        k in name_upper
        for k in (
            "DAO",
            "APPEL D'OFFRES",
            "DOSSIER APPEL",
        )
    ):
        return "source_rules"
    if any(
        k in name_upper
        for k in (
            "RFQ",
            "DEMANDE DE COTATION",
        )
    ):
        return "source_rules"
    return "supporting_doc"


def _storage_base_for_bridge(
    source_roots: list[str], discovered_pdfs: list[Path]
) -> str:
    """
    Répertoire de base pour STORAGE_BASE_PATH : uniquement chemins existants,
    normalisés (resolve). Combine racines source valides et parents des PDF
    découverts, puis commonpath — évite une première racine invalide ou hors lot.
    """
    candidates: list[str] = []
    for raw in source_roots:
        if not raw:
            continue
        rp = Path(raw)
        if rp.is_dir():
            candidates.append(str(rp.resolve()))
    for pdf in discovered_pdfs:
        candidates.append(str(pdf.resolve().parent))
    seen: set[str] = set()
    uniq: list[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    if not uniq:
        return ""
    try:
        return os.path.commonpath(uniq)
    except ValueError:
        # Ex. lecteurs Windows différents : couvrir au moins le premier chemin valide
        return uniq[0]


def build_ls_task(
    rec: PdfRecord,
    default_document_role: str,
    run_id: str,
    *,
    structured_preview_pages: int = 5,
) -> dict:
    rel = rec.path
    filename = Path(rec.path).name
    source_tag = f"{rec.process_name}:{filename}"
    inferred = _classify_to_document_role(rec.classification, rec.path)
    if inferred != "supporting_doc":
        document_role = inferred
    elif default_document_role != "supporting_doc":
        document_role = default_document_role
    else:
        document_role = "supporting_doc"

    structured: dict = {}
    if structured_preview_pages > 0 and Path(rec.path).suffix.lower() == ".pdf":
        structured = structured_preview_from_pdf(
            rec.path, max_pages=structured_preview_pages
        )

    # text = corps document seul (pas de préfixe) : le backend applique MIN_* sur ce
    # champ ; filename + document_role sont des champs séparés (injectés au prompt LS).
    return {
        "data": {
            "text": rec.text,
            "filename": filename,
            "document_role": document_role,
            "classification": rec.classification,
            "source": source_tag,
            "process_name": rec.process_name,
            "source_path": rel,
            "ingest_run_id": run_id,
            "pdf_classification": rec.classification,
            "engine_route": rec.engine_route,
            "structured_preview": structured,
        }
    }


def run_ingest(
    source_roots: list[str],
    output_root: str,
    default_document_role: str,
    run_id: str | None = None,
    ingest_limit: int | None = None,
    include_manifest_tasks: bool = False,
    structured_preview_pages: int = 5,
) -> dict:
    if not source_roots:
        raise ValueError(
            "source_roots ne peut pas être vide — fournir au moins une racine dossier."
        )
    run_id = run_id or f"bridge-{uuid.uuid4().hex[:12]}"
    out_dir = Path(output_root)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_pdfs = discover_pdfs(source_roots)

    # DETTE TECHNIQUE : mutation globale confinée à ce seul point (FIX-01).
    # Découplage réel = mandat ultérieur dédié.
    storage_base = _storage_base_for_bridge(source_roots, all_pdfs)
    os.environ["STORAGE_BASE_PATH"] = storage_base
    logger.info("[BRIDGE] STORAGE_BASE_PATH=%s", storage_base)

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

    ls_tasks: list[dict] = []
    manifest_tasks: list[dict] = []
    for r in records:
        task = build_ls_task(
            r,
            default_document_role,
            run_id,
            structured_preview_pages=structured_preview_pages,
        )
        ls_tasks.append(task)
        dr = task["data"]["document_role"]
        logger.info(
            "[BRIDGE] task=%s document_role=%s engine=%s",
            Path(r.path).name,
            dr,
            r.engine_route,
        )
        if include_manifest_tasks:
            manifest_tasks.append(
                {
                    "path": r.path,
                    "filename": Path(r.path).name,
                    "document_role": dr,
                    "engine_route": r.engine_route,
                    "pdf_classification": r.classification,
                }
            )

    manifest: dict = {
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "source_roots": source_roots,
        "output_root": str(out_dir.resolve()),
        "default_document_role": default_document_role,
        "ingest_limit": ingest_limit,
        "structured_preview_pages": structured_preview_pages,
        "pdf_files_discovered": len(all_pdfs),
        "pdf_files_seen": len(pdfs),
        "tasks_emitted": len(records),
        "tasks_skipped": len(skipped),
    }
    if include_manifest_tasks:
        manifest["tasks"] = manifest_tasks

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
    parser.add_argument(
        "--manifest-tasks",
        action="store_true",
        help="Inclure la liste détaillée tasks dans run_manifest.json "
        "(défaut : non — évite la duplication lourde avec ls_tasks.json).",
    )
    parser.add_argument(
        "--structured-preview-pages",
        type=int,
        default=5,
        metavar="N",
        help="Nombre max de pages PDF pour structured_preview (pdfplumber). 0 = désactivé.",
    )
    args = parser.parse_args()

    roots = args.source_roots if args.source_roots else DEFAULT_SOURCE_ROOTS
    report = run_ingest(
        source_roots=roots,
        output_root=args.output_root,
        default_document_role=args.default_document_role,
        run_id=args.run_id,
        ingest_limit=args.limit,
        include_manifest_tasks=args.manifest_tasks,
        structured_preview_pages=args.structured_preview_pages,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
