"""
Backfill corpus R2/S3 — annotations déjà dans Label Studio avant branchement du sink.

Réutilise la même chaîne que le webhook : ``process_label_studio_webhook_for_corpus``
(m12-v2 + PutObject idempotent par content_hash).

Prérequis (alignés sur le service Railway annotation-backend) :
  - LABEL_STUDIO_URL, LABEL_STUDIO_API_KEY (ou LS_URL / LS_API_KEY)
  - PSEUDONYM_SALT
  - CORPUS_WEBHOOK_ENABLED=1
  - CORPUS_SINK=s3 + S3_* (bucket, endpoint, clés) pour un run réel

Usage :
  # Simulation (aucune écriture R2)
  set LABEL_STUDIO_URL=...
  set LABEL_STUDIO_API_KEY=...
  set PSEUDONYM_SALT=...
  python scripts/backfill_corpus_from_label_studio.py --project-id 1 --dry-run

  # Envoi réel vers R2 (mêmes variables + CORPUS_WEBHOOK_ENABLED=1 + S3_*)
  python scripts/backfill_corpus_from_label_studio.py --project-id 1 --limit 20

  # Tout le projet
  python scripts/backfill_corpus_from_label_studio.py --project-id 1

  # Sans appel API : fichier export JSON Label Studio
  python scripts/backfill_corpus_from_label_studio.py --from-export-json export.json --project-id 1 --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_ANNOTATION_BACKEND = _PROJECT_ROOT / "services" / "annotation-backend"


def _ensure_annotation_path() -> None:
    p = str(_ANNOTATION_BACKEND)
    if p not in sys.path:
        sys.path.insert(0, p)


def main() -> None:
    load_dotenv(_PROJECT_ROOT / ".env")
    load_dotenv(_PROJECT_ROOT / ".env.local")

    parser = argparse.ArgumentParser(
        description="Backfill corpus m12-v2 depuis Label Studio (annotations historiques)"
    )
    parser.add_argument("--project-id", type=int, required=True, help="ID projet LS")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Nombre max d'annotations à pousser (ex. 20)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ne pas écrire sur S3/R2 ; simule CORPUS_WEBHOOK + sink noop",
    )
    parser.add_argument(
        "--from-export-json",
        type=str,
        default=None,
        help="JSON export LS (évite l'API)",
    )
    args = parser.parse_args()

    _ensure_annotation_path()

    from corpus_sink import CorpusSink, NoopCorpusSink
    from corpus_webhook import process_label_studio_webhook_for_corpus

    project_id = args.project_id

    if args.from_export_json:
        with open(args.from_export_json, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            data = [data]
    else:
        from ls_client import fetch_annotations

        ls_url = os.environ.get("LABEL_STUDIO_URL", "").strip().rstrip(
            "/"
        ) or os.environ.get("LS_URL", "").strip().rstrip("/")
        ls_key = (
            os.environ.get("LABEL_STUDIO_API_KEY", "").strip()
            or os.environ.get("LS_API_KEY", "").strip()
        )
        if not ls_url or not ls_key:
            sys.exit(
                "STOP — LABEL_STUDIO_URL + LABEL_STUDIO_API_KEY "
                "(ou LS_URL + LS_API_KEY) requis sans --from-export-json"
            )
        print(f"Fetch export projet {project_id} …")
        data = fetch_annotations(project_id, ls_url, ls_key)

    if not os.environ.get("PSEUDONYM_SALT", "").strip():
        sys.exit("STOP — PSEUDONYM_SALT requis (identique au backend)")

    saved_corpus_wh: str | None = None
    sink: CorpusSink | None
    if args.dry_run:
        saved_corpus_wh = os.environ.get("CORPUS_WEBHOOK_ENABLED")
        os.environ["CORPUS_WEBHOOK_ENABLED"] = "1"
        sink = NoopCorpusSink()
    else:
        if os.environ.get("CORPUS_WEBHOOK_ENABLED", "").strip().lower() not in (
            "1",
            "true",
            "yes",
            "on",
        ):
            sys.exit(
                "STOP — pour un run réel : CORPUS_WEBHOOK_ENABLED=1 "
                "+ CORPUS_SINK=s3 et variables S3_* (voir services/annotation-backend/ENVIRONMENT.md)"
            )
        sink = None

    processed = 0
    skipped_empty = 0

    try:
        for item in data:
            annotations = item.get("annotations") or []
            if not annotations:
                skipped_empty += 1
                continue
            for ann in annotations:
                if args.limit is not None and processed >= args.limit:
                    break
                payload = {
                    "action": "ANNOTATION_UPDATED",
                    "project": {"id": project_id},
                    "task": item,
                    "annotation": ann,
                }
                if args.dry_run:
                    print(
                        f"  [dry-run] task_id={item.get('id')} "
                        f"ann_id={ann.get('id')}"
                    )
                process_label_studio_webhook_for_corpus(payload, sink=sink)  # type: ignore[arg-type]
                processed += 1
            if args.limit is not None and processed >= args.limit:
                break
    finally:
        if args.dry_run:
            if saved_corpus_wh is None:
                os.environ.pop("CORPUS_WEBHOOK_ENABLED", None)
            else:
                os.environ["CORPUS_WEBHOOK_ENABLED"] = saved_corpus_wh

    mode = "dry-run (0 écriture R2)" if args.dry_run else "corpus"
    print(
        f"Terminé [{mode}] : {processed} annotation(s) traitées, "
        f"{skipped_empty} tâche(s) sans annotation ignorée(s)."
    )
    print(
        "Les clés R2 sont idempotentes (task/ann/hash) : "
        "relancer le script ne duplique pas les objets, il réécrit la même clé."
    )


if __name__ == "__main__":
    main()
