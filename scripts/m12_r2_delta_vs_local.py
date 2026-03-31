"""
Exporte depuis R2 uniquement les lignes m12-v2 **absentes** des JSONL locaux (delta).

Cas d'usage : le laptop a un export partiel (ex. 57 lignes) alors que R2 en contient
davantage (ex. 73). On récupère **seulement** les objets manquants (clé stable identique
à ``consolidate_m12_corpus.py`` / ``stable_m12_corpus_line_id``), au format JSONL.

Statuts LS : par défaut ``annotated_validated`` et ``annotated`` (libellé ou export
historique — équivalent fonctionnel pour l'inclusion ; la vérité de fond reste le JSON
R2). Affiner avec ``--accepted-statuses`` ou ``--no-status-filter``.

Variables S3 : comme ``export_r2_corpus_to_jsonl.py`` / ``ENVIRONMENT.md``.

Usage :
  set S3_BUCKET=... & set S3_ENDPOINT=... & set S3_ACCESS_KEY_ID=... & set S3_SECRET_ACCESS_KEY=...
  python scripts/m12_r2_delta_vs_local.py \\
    --local-jsonl data/annotations/m12_local.jsonl \\
    --output data/annotations/m12_from_r2_only_missing.jsonl

  # Puis fusion (R2 gagne sur les doublons) :
  python scripts/consolidate_m12_corpus.py \\
    -i data/annotations/m12_local.jsonl \\
    -i data/annotations/m12_from_r2_only_missing.jsonl \\
    --from-r2 \\
    -o data/annotations/m12_consolidated.jsonl \\
    --only-export-ok --manifest data/annotations/m12_consolidate_manifest.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_ANNOTATION_BACKEND = _PROJECT_ROOT / "services" / "annotation-backend"

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.annotation.m12_export_io import (  # noqa: E402
    stable_m12_corpus_ids_from_jsonl_paths,
    stable_m12_corpus_line_id,
)


def _ensure_annotation_backend_path() -> None:
    p = str(_ANNOTATION_BACKEND)
    if p not in sys.path:
        sys.path.insert(0, p)


def _parse_accepted_statuses(s: str) -> set[str]:
    return {x.strip() for x in s.split(",") if x.strip()}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="R2 → JSONL des lignes absentes des JSONL locaux (delta M12)"
    )
    parser.add_argument(
        "--local-jsonl",
        action="append",
        default=[],
        metavar="PATH",
        help="JSONL local déjà présent (répéter pour plusieurs fichiers)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        required=True,
        help="JSONL de sortie (uniquement les lignes R2 dont la clé stable est absente localement)",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default=None,
        help="Surcharge S3_CORPUS_PREFIX (défaut env ou m12-v2)",
    )
    parser.add_argument(
        "--accepted-statuses",
        type=str,
        default="annotated_validated,annotated",
        help="Liste CSV de ls_meta.annotation_status acceptés depuis R2 (défaut : validated + legacy annotated)",
    )
    parser.add_argument(
        "--no-status-filter",
        action="store_true",
        help="Ne pas filtrer sur annotation_status",
    )
    parser.add_argument(
        "--project-id",
        type=int,
        default=None,
        help="Si défini : ne garder que ls_meta.project_id == cette valeur",
    )
    parser.add_argument(
        "--only-m12-v2",
        action="store_true",
        help="Ignorer les lignes R2 sans export_schema_version=m12-v2",
    )
    parser.add_argument(
        "--only-export-ok",
        action="store_true",
        help="Ignorer les lignes R2 avec export_ok=false",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Nombre max de lignes écrites (après filtres)",
    )
    args = parser.parse_args()

    if not args.local_jsonl:
        print("STOP — fournir au moins un --local-jsonl", file=sys.stderr)
        return 2

    local_paths: list[Path] = []
    for raw in args.local_jsonl:
        p = Path(raw)
        if not p.is_file():
            print(f"STOP — fichier local introuvable : {p}", file=sys.stderr)
            return 2
        local_paths.append(p)

    have_local = stable_m12_corpus_ids_from_jsonl_paths(local_paths)
    allowed_statuses = _parse_accepted_statuses(args.accepted_statuses)

    _ensure_annotation_backend_path()
    from corpus_sink import iter_corpus_m12_lines_from_s3

    out_path = args.output
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    written = 0
    skipped_have_local = 0
    skipped_status = 0
    skipped_project = 0
    skipped_filters = 0

    with open(out_path, "w", encoding="utf-8") as f:
        for line in iter_corpus_m12_lines_from_s3(prefix=args.prefix):
            if not isinstance(line, dict):
                continue
            if args.only_m12_v2 and line.get("export_schema_version") != "m12-v2":
                skipped_filters += 1
                continue
            if args.only_export_ok and not line.get("export_ok", False):
                skipped_filters += 1
                continue

            ls_meta = (
                line.get("ls_meta") if isinstance(line.get("ls_meta"), dict) else {}
            )
            if not args.no_status_filter:
                st = (ls_meta.get("annotation_status") or "").strip()
                if st not in allowed_statuses:
                    skipped_status += 1
                    continue
            if args.project_id is not None:
                pid = ls_meta.get("project_id")
                if pid is None or int(pid) != args.project_id:
                    skipped_project += 1
                    continue

            key = stable_m12_corpus_line_id(line)
            if key in have_local:
                skipped_have_local += 1
                continue

            f.write(json.dumps(line, ensure_ascii=False) + "\n")
            written += 1
            have_local.add(key)
            if args.limit is not None and written >= args.limit:
                break

    print(
        f"Delta R2 → {out_path} : {written} ligne(s) écrites "
        f"(déjà en local ignorées={skipped_have_local}, statut={skipped_status}, "
        f"projet={skipped_project}, autres filtres={skipped_filters})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
