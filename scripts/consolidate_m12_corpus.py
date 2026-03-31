"""
Consolidation corpus M12-v2 : sources locales (JSONL) + Cloudflare R2 (S3).

Architecture (docs/m12/M12_EXPORT.md, ADR-M12-EXPORT-V2) :
  - R2 : un objet = un fichier JSON sous le prefixe m12-v2/ (verite de stockage prod).
  - Local : JSONL produits par export_ls_to_dms_jsonl.py ou deja agreges depuis R2.

Politique par defaut : **r2-wins** — en cas de meme cle stable, la ligne issue de R2
remplace celle des fichiers locaux (aligne "R2 = reference stockage").

Cle stable : voir ``stable_m12_corpus_line_id`` dans ``src/annotation/m12_export_io.py``.

Usage :
  # Locaux puis overlay R2 (R2 gagne les doublons)
  set S3_BUCKET=... & set S3_ENDPOINT=... & set S3_ACCESS_KEY_ID=... & set S3_SECRET_ACCESS_KEY=...
  python scripts/consolidate_m12_corpus.py \\
    --input data/annotations/m12_batch_local.jsonl \\
    --from-r2 \\
    --output data/annotations/m12_consolidated.jsonl \\
    --manifest data/annotations/m12_consolidate_manifest.json

  # Sans R2 : fusionner plusieurs JSONL (dernier fichier gagne)
  python scripts/consolidate_m12_corpus.py -i a.jsonl -i b.jsonl -o out.jsonl

  # R2 d'abord puis locaux (local gagne)
  python scripts/consolidate_m12_corpus.py --from-r2 --r2-first --input local.jsonl -o out.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_ANNOTATION_BACKEND = _PROJECT_ROOT / "services" / "annotation-backend"

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.annotation.m12_export_io import stable_m12_corpus_line_id  # noqa: E402


def _ensure_annotation_backend_path() -> None:
    p = str(_ANNOTATION_BACKEND)
    if p not in sys.path:
        sys.path.insert(0, p)


def _iter_jsonl_lines(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            yield json.loads(raw)


def _merge_ordered(
    ordered_sources: list[tuple[str, Iterator[dict[str, Any]]]],
    *,
    only_m12_v2: bool,
    only_export_ok: bool,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """ordered_sources : derniere source lue gagne pour une meme cle stable."""
    merged: dict[str, dict[str, Any]] = {}
    stats: dict[str, Any] = {
        "sources": [],
        "skipped_non_m12_v2": 0,
        "skipped_export_not_ok": 0,
        "lines_read_total": 0,
    }

    for label, iterator in ordered_sources:
        src_stat: dict[str, Any] = {
            "label": label,
            "lines_read": 0,
            "lines_kept_after_filters": 0,
        }
        for line in iterator:
            stats["lines_read_total"] += 1
            src_stat["lines_read"] += 1
            if not isinstance(line, dict):
                continue
            if only_m12_v2 and line.get("export_schema_version") != "m12-v2":
                stats["skipped_non_m12_v2"] += 1
                continue
            if only_export_ok and not line.get("export_ok", False):
                stats["skipped_export_not_ok"] += 1
                continue
            key = stable_m12_corpus_line_id(line)
            merged[key] = line
            src_stat["lines_kept_after_filters"] += 1
        stats["sources"].append(src_stat)

    return merged, stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consolide corpus M12 (JSONL locaux + option R2) en un JSONL deduplique."
    )
    parser.add_argument(
        "--input",
        "-i",
        action="append",
        default=[],
        metavar="PATH",
        help="Fichier JSONL local (repeter pour plusieurs fichiers, ordre = priorite si --r2-first)",
    )
    parser.add_argument(
        "--from-r2",
        action="store_true",
        help="Inclure le corpus depuis R2/S3 (variables S3_* comme export_r2_corpus_to_jsonl.py)",
    )
    parser.add_argument(
        "--r2-prefix",
        type=str,
        default=None,
        help="Surcharge prefixe S3 (defaut env S3_CORPUS_PREFIX ou m12-v2)",
    )
    parser.add_argument(
        "--r2-first",
        action="store_true",
        help="Lire R2 avant les --input (les fichiers locaux gagnent sur les doublons)",
    )
    parser.add_argument(
        "--r2-status",
        type=str,
        default="annotated_validated",
        help="Ne garder depuis R2 que ce statut si --r2-accepted-statuses absent",
    )
    parser.add_argument(
        "--r2-accepted-statuses",
        type=str,
        default=None,
        help=(
            "Liste CSV de statuts LS acceptes depuis R2 (ex. annotated_validated,annotated). "
            "Si defini, remplace --r2-status."
        ),
    )
    parser.add_argument(
        "--r2-no-status-filter",
        action="store_true",
        help="Desactiver le filtre --r2-status sur le flux R2",
    )
    parser.add_argument(
        "--r2-project-id",
        type=int,
        default=None,
        help="Si defini : ne garder depuis R2 que ls_meta.project_id == cette valeur",
    )
    parser.add_argument(
        "--r2-limit",
        type=int,
        default=None,
        help="Nombre max de lignes gardees depuis R2 apres filtres R2",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        required=True,
        help="JSONL de sortie",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default=None,
        help="Ecrit un JSON de rapport (comptages, politique)",
    )
    parser.add_argument(
        "--only-m12-v2",
        action="store_true",
        help="Ignorer les lignes sans export_schema_version=m12-v2",
    )
    parser.add_argument(
        "--only-export-ok",
        action="store_true",
        help="Ignorer les lignes m12-v2 avec export_ok=false",
    )
    args = parser.parse_args()

    if not args.input and not args.from_r2:
        print(
            "STOP — fournir au moins un --input ou --from-r2",
            file=sys.stderr,
        )
        return 2

    r2_accepted: set[str] | None = None
    if args.r2_accepted_statuses is not None and args.r2_accepted_statuses.strip():
        r2_accepted = {
            s.strip() for s in args.r2_accepted_statuses.split(",") if s.strip()
        }

    def iter_r2_filtered() -> Iterator[dict[str, Any]]:
        _ensure_annotation_backend_path()
        from corpus_sink import iter_corpus_m12_lines_from_s3

        kept = 0
        for line in iter_corpus_m12_lines_from_s3(prefix=args.r2_prefix):
            ls_meta = (
                line.get("ls_meta") if isinstance(line.get("ls_meta"), dict) else {}
            )
            if not args.r2_no_status_filter:
                st = (ls_meta.get("annotation_status") or "").strip()
                if r2_accepted is not None:
                    if st not in r2_accepted:
                        continue
                elif st != args.r2_status:
                    continue
            if args.r2_project_id is not None:
                pid = ls_meta.get("project_id")
                if pid is None or int(pid) != args.r2_project_id:
                    continue
            yield line
            kept += 1
            if args.r2_limit is not None and kept >= args.r2_limit:
                break

    ordered: list[tuple[str, Iterator[dict[str, Any]]]] = []

    if args.r2_first and args.from_r2:
        ordered.append(("r2", iter_r2_filtered()))
    for p in args.input:
        path = Path(p)
        if not path.is_file():
            print(f"STOP — fichier introuvable : {path}", file=sys.stderr)
            return 2
        ordered.append((f"file:{path.name}", _iter_jsonl_lines(path)))
    if not args.r2_first and args.from_r2:
        ordered.append(("r2", iter_r2_filtered()))

    policy = "local-wins-over-r2" if args.r2_first else "r2-wins-over-local"

    try:
        merged, stats = _merge_ordered(
            ordered,
            only_m12_v2=args.only_m12_v2,
            only_export_ok=args.only_export_ok,
        )
    except Exception as e:
        # botocore.ClientError (flux R2) — import lazy pour ne pas exiger boto3 en usage local-only
        if type(e).__name__ == "ClientError":
            resp = getattr(e, "response", None) or {}
            err = resp.get("Error") if isinstance(resp, dict) else {}
            code = (err or {}).get("Code", "") if isinstance(err, dict) else ""
            if code == "RequestTimeTooSkewed":
                print(
                    "STOP — RequestTimeTooSkewed : synchroniser l'horloge systeme "
                    "(voir scripts/export_r2_corpus_to_jsonl.py).",
                    file=sys.stderr,
                )
                return 3
        raise

    out_path = args.output
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for _key, line in sorted(merged.items(), key=lambda x: x[0]):
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    written = len(merged)
    print(
        f"Consolide {written} ligne(s) unique(s) -> {out_path} "
        f"(policy={policy}, lues={stats['lines_read_total']})"
    )

    if args.manifest:
        man = {
            "policy": policy,
            "output": out_path,
            "unique_lines": written,
            "stats": stats,
            "filters": {
                "only_m12_v2": args.only_m12_v2,
                "only_export_ok": args.only_export_ok,
            },
            "r2_filters": {
                "enabled": args.from_r2,
                "r2_first": args.r2_first,
                "status": (
                    None
                    if args.r2_no_status_filter
                    else (
                        sorted(r2_accepted)
                        if r2_accepted is not None
                        else args.r2_status
                    )
                ),
                "project_id": args.r2_project_id,
                "limit": args.r2_limit,
            },
        }
        mp = Path(args.manifest)
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(
            json.dumps(man, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"Manifest -> {mp}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
