#!/usr/bin/env python3
"""
Piste B — Fusionne du texte OCR « entreprise » (fichiers sidecar) en tâches Label Studio.

Sans modification du backend : produit un JSON importable (même forme que ingest_to_annotation_bridge).

Convention sidecar (un fichier par PDF) :
  <text_dir>/<basename_sans_pdf>.txt
  ou <text_dir>/<basename_sans_pdf>.ocr.txt

Exemple :
  python scripts/merge_external_ocr_to_ls_tasks.py \\
    --skipped-json path/to/skipped.json \\
    --text-dir path/to/ocr_texts \\
    --output path/to/ls_tasks_external_ocr.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import uuid
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _load_bridge():
    path = _PROJECT_ROOT / "scripts" / "ingest_to_annotation_bridge.py"
    name = "ingest_bridge"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _find_sidecar(text_dir: Path, stem: str) -> Path | None:
    for name in (f"{stem}.txt", f"{stem}.ocr.txt"):
        p = text_dir / name
        if p.is_file():
            return p
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build ls_tasks.json from external OCR text sidecars."
    )
    parser.add_argument(
        "--skipped-json",
        required=True,
        help="skipped.json from ingest_to_annotation_bridge (liste des PDFs sans texte).",
    )
    parser.add_argument(
        "--text-dir",
        required=True,
        type=Path,
        help="Répertoire des fichiers .txt (ou .ocr.txt) par stem de fichier PDF.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Sortie JSON (défaut: stdout ou text-dir/ls_tasks_external_ocr.json).",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Identifiant de run (défaut: UUID court).",
    )
    parser.add_argument(
        "--structured-preview-pages",
        type=int,
        default=0,
        help="Pages pour structured_preview (pdfplumber) ; 0 = désactivé (défaut).",
    )
    parser.add_argument(
        "--default-document-role",
        default="supporting_doc",
        help="Rôle par défaut si l'heuristique nom de fichier ne matche pas.",
    )
    args = parser.parse_args()

    skipped_path = Path(args.skipped_json)
    if not skipped_path.is_file():
        print(f"Missing file: {skipped_path}", file=sys.stderr)
        return 1

    raw = json.loads(skipped_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        print("skipped.json must be a JSON array", file=sys.stderr)
        return 1

    bridge = _load_bridge()

    run_id = args.run_id or f"external-ocr-{uuid.uuid4().hex[:12]}"
    text_dir: Path = args.text_dir

    tasks: list[dict] = []
    missing_sidecars: list[str] = []

    for row in raw:
        if not isinstance(row, dict):
            continue
        reason = row.get("reason", "")
        if reason and reason != "no_text_all_extractors":
            continue
        pdf_path = row.get("path")
        if not pdf_path:
            continue
        p = Path(pdf_path)
        stem = p.stem
        sidecar = _find_sidecar(text_dir, stem)
        if sidecar is None:
            missing_sidecars.append(stem)
            continue
        text = sidecar.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            missing_sidecars.append(f"{stem} (empty)")
            continue

        rec = bridge.PdfRecord(
            path=str(pdf_path),
            process_name=str(row.get("process_name") or p.parent.name or "."),
            classification=str(row.get("classification") or "scanned_pdf"),
            engine_route="external_ocr",
            text=text,
            skip_reason=None,
        )
        tasks.append(
            bridge.build_ls_task(
                rec,
                args.default_document_role,
                run_id,
                structured_preview_pages=args.structured_preview_pages,
            )
        )

    out_payload = {
        "run_id": run_id,
        "tasks": tasks,
        "tasks_built": len(tasks),
        "missing_sidecars": missing_sidecars,
    }

    out_txt = json.dumps(tasks, ensure_ascii=False, indent=2)
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(out_txt, encoding="utf-8")
        summary_path = out_path.with_name(out_path.stem + "_summary.json")
        summary_path.write_text(
            json.dumps(out_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Wrote {out_path} ({len(tasks)} tasks)")
        print(f"Summary: {summary_path}")
    else:
        print(out_txt)

    if missing_sidecars:
        print(
            f"\nWarning: {len(missing_sidecars)} entries without usable sidecar text.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
