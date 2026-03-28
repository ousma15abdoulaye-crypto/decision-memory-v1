"""
Export corpus M12 depuis le bucket S3-compatible (Cloudflare R2) → JSONL local.

En production, les lignes m12-v2 validées sont stockées dans R2 par le webhook
annotation-backend (S3CorpusSink). Label Studio sert d’interface de correction ;
**R2 est la vérité de stockage** pour le corpus calibration (N≥50, derive, F1).

**Format dans R2 :** chaque objet est un **fichier JSON** (clé ``…/*.json``) — un seul
document JSON UTF-8 par objet, ``Content-Type: application/json``. Ce script les
lit et produit en local un **JSONL** (une ligne = un objet JSON), format attendu
par ``derive_pass_0_5_thresholds.py`` et ``m12_calibrate_classifier_metrics.py``.

Prérequis (alignés sur ``services/annotation-backend/ENVIRONMENT.md``) :
  - S3_BUCKET
  - S3_ENDPOINT (ex. https://<ACCOUNT_ID>.r2.cloudflarestorage.com)
  - S3_ACCESS_KEY_ID / S3_SECRET_ACCESS_KEY (ou AWS_*)
  - S3_CORPUS_PREFIX optionnel (défaut : m12-v2)

  Ce script **ne lit pas** ``LABEL_STUDIO_URL`` / ``LABEL_STUDIO_API_KEY`` : c’est l’API S3 R2.
  Les variables peuvent être dans ``.env.local`` ou ``data/annotations/.r2_export_env``
  (voir ``data/annotations/r2_export.env.example``).

Usage :
  set S3_BUCKET=...
  set S3_ENDPOINT=...
  set S3_ACCESS_KEY_ID=...
  set S3_SECRET_ACCESS_KEY=...
  python scripts/export_r2_corpus_to_jsonl.py --output data/annotations/m12_corpus_50.jsonl

  # Filtrer comme le gate webhook (défaut : annotated_validated)
  python scripts/export_r2_corpus_to_jsonl.py --output out.jsonl --status annotated_validated

  # Toutes les lignes du préfixe (sans filtre statut)
  python scripts/export_r2_corpus_to_jsonl.py --output out.jsonl --no-status-filter

  # Limiter (ex. test)
  python scripts/export_r2_corpus_to_jsonl.py --output out.jsonl --limit 50

  # Nouvelles lignes R2 uniquement (exclure task/annotation déjà dans un JSONL local) +
  # une révision par (projet, tâche, annotation) = la plus récente (LastModified S3)
  python scripts/export_r2_corpus_to_jsonl.py -o data/annotations/m12_r2_delta.jsonl \\
    --exclude-jsonl data/annotations/m12_corpus_from_ls.jsonl --only-export-ok

  # Réalignement : R2 prioritaire + JSONL LS pour les tâches absentes du bucket
  python scripts/export_r2_corpus_to_jsonl.py \\
    -o data/annotations/m12_corpus_realigned.jsonl --project-id 1 \\
    --backfill-from-jsonl data/annotations/m12_corpus_from_ls.jsonl

En cas d’erreur ``RequestTimeTooSkewed`` : par défaut le backend ajuste l’heure de
signature via HTTP (``S3_CLOCK_SKEW_AUTO``, voir ``ENVIRONMENT.md``). Si ça persiste :
synchroniser l’horloge Windows ou mettre ``S3_CLOCK_SKEW_AUTO=0`` après correction NTP.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from botocore.exceptions import ClientError

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_ANNOTATION_BACKEND = _PROJECT_ROOT / "services" / "annotation-backend"


def _ensure_annotation_path() -> None:
    p = str(_ANNOTATION_BACKEND)
    if p not in sys.path:
        sys.path.insert(0, p)


def _ensure_src_path() -> None:
    r = str(_PROJECT_ROOT)
    if r not in sys.path:
        sys.path.insert(0, r)


def _load_dotenv_repo() -> None:
    """Charge ``.env``, ``.env.local``, puis ``data/annotations/.r2_export_env`` (override)."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    root = _PROJECT_ROOT
    env_f = root / ".env"
    local_f = root / ".env.local"
    r2_export = root / "data" / "annotations" / ".r2_export_env"
    if env_f.is_file():
        load_dotenv(env_f)
    if local_f.is_file():
        load_dotenv(local_f, override=True)
    if r2_export.is_file():
        load_dotenv(r2_export, override=True)


def _m12_identity(line: dict[str, Any]) -> tuple[str, str, str] | None:
    ls_meta = line.get("ls_meta") if isinstance(line.get("ls_meta"), dict) else {}
    pid = ls_meta.get("project_id")
    tid = ls_meta.get("task_id")
    aid = ls_meta.get("annotation_id")
    if pid is None or tid is None or aid is None:
        return None
    return str(pid), str(tid), str(aid)


def _load_excluded_identities(paths: list[Path]) -> set[tuple[str, str, str]]:
    _ensure_src_path()
    from src.annotation.m12_export_io import iter_m12_jsonl_lines

    out: set[tuple[str, str, str]] = set()
    for p in paths:
        if not p.is_file():
            continue
        for line in iter_m12_jsonl_lines(p):
            k = _m12_identity(line)
            if k:
                out.add(k)
    return out


def _last_modified_ts(lm: Any) -> float:
    if lm is None:
        return 0.0
    try:
        return float(lm.timestamp())
    except Exception:
        return 0.0


def _annotation_status_matches(raw: str, expected: str) -> bool:
    """Aligne LS / inventaires où le libellé peut être ``validated`` ou ``annotated_validated``."""
    st = (raw or "").strip()
    exp = (expected or "").strip()
    if st == exp:
        return True
    if exp == "annotated_validated" and st == "validated":
        return True
    if exp == "validated" and st == "annotated_validated":
        return True
    return False


def _task_sort_tuple(line: dict[str, Any]) -> tuple[int, int]:
    ls_meta = line.get("ls_meta") if isinstance(line.get("ls_meta"), dict) else {}
    tid = ls_meta.get("task_id")
    aid = ls_meta.get("annotation_id")
    try:
        ti = int(tid) if tid is not None else 0
    except (TypeError, ValueError):
        ti = 0
    try:
        ai = int(aid) if aid is not None else 0
    except (TypeError, ValueError):
        ai = 0
    return ti, ai


def main() -> int:
    _load_dotenv_repo()
    parser = argparse.ArgumentParser(
        description="Export corpus m12-v2 depuis R2/S3 → un fichier JSONL (une ligne JSON par objet)"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        required=True,
        help="Chemin fichier JSONL de sortie",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default=None,
        help="Surcharge S3_CORPUS_PREFIX (défaut env ou m12-v2)",
    )
    parser.add_argument(
        "--status",
        type=str,
        default="annotated_validated",
        help="Ne garder que ls_meta.annotation_status == cette valeur (défaut : annotated_validated)",
    )
    parser.add_argument(
        "--no-status-filter",
        action="store_true",
        help="Écrire toutes les lignes lues depuis R2 (ignore --status)",
    )
    parser.add_argument(
        "--project-id",
        type=int,
        default=None,
        help="Si défini : ne garder que ls_meta.project_id == cette valeur",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Nombre max de lignes écrites après filtres",
    )
    parser.add_argument(
        "--require-source-text",
        action="store_true",
        help="Exit≠0 si une ligne écrite n'a pas source_text non vide (calibration stricte)",
    )
    parser.add_argument(
        "--exclude-jsonl",
        action="append",
        default=[],
        metavar="PATH",
        help=(
            "JSONL de référence (répéter l’option pour plusieurs fichiers). "
            "Exclut les (project_id, task_id, annotation_id) déjà présents."
        ),
    )
    parser.add_argument(
        "--no-r2-dedupe",
        action="store_true",
        help=(
            "Conserver toutes les révisions R2 (plusieurs content_hash par tâche). "
            "Par défaut : une ligne par (projet, tâche, annotation) = révision au LastModified S3 le plus récent."
        ),
    )
    parser.add_argument(
        "--only-export-ok",
        action="store_true",
        help="Ne garder que les lignes avec export_ok == true (qualité export)",
    )
    parser.add_argument(
        "--backfill-from-jsonl",
        type=str,
        default=None,
        metavar="PATH",
        help=(
            "Après fusion R2 (une révision par tâche/annotation), ajoute depuis ce JSONL "
            "les lignes dont l’identité (projet, tâche, annotation) n’est pas encore dans R2. "
            "Incompatible avec --no-r2-dedupe."
        ),
    )
    args = parser.parse_args()

    if args.backfill_from_jsonl and args.no_r2_dedupe:
        print(
            "STOP — --backfill-from-jsonl exige la dédup R2 par défaut "
            "(retirez --no-r2-dedupe).",
            file=sys.stderr,
        )
        return 2

    _ensure_annotation_path()
    from corpus_sink import iter_corpus_m12_objects_from_s3

    out_path = args.output
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    exclude_paths = [Path(p) for p in (args.exclude_jsonl or [])]
    for p in exclude_paths:
        if not p.is_file():
            print(f"Avertissement — exclude-jsonl introuvable, ignoré : {p}", file=sys.stderr)
    excluded = _load_excluded_identities(exclude_paths)

    written = 0
    skipped_status = 0
    skipped_project = 0
    missing_source_text = 0
    skipped_excluded = 0
    skipped_identity = 0
    skipped_export_ok = 0
    skipped_r2_superseded = 0
    backfilled_from_ls = 0
    backfill_skipped_identity = 0
    backfill_skipped_already_r2 = 0

    def passes_common_filters(line: dict[str, Any]) -> bool:
        nonlocal skipped_status, skipped_project, skipped_export_ok
        ls_meta = line.get("ls_meta") if isinstance(line.get("ls_meta"), dict) else {}
        if not args.no_status_filter:
            st = (ls_meta.get("annotation_status") or "").strip()
            if not _annotation_status_matches(st, args.status):
                skipped_status += 1
                return False
        if args.project_id is not None:
            pid = ls_meta.get("project_id")
            if pid is None or int(pid) != args.project_id:
                skipped_project += 1
                return False
        if args.only_export_ok and line.get("export_ok") is not True:
            skipped_export_ok += 1
            return False
        return True

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            if args.no_r2_dedupe:
                for line, _s3_key, _lm in iter_corpus_m12_objects_from_s3(
                    prefix=args.prefix
                ):
                    if not passes_common_filters(line):
                        continue
                    ident = _m12_identity(line)
                    if ident is None:
                        skipped_identity += 1
                        continue
                    if ident in excluded:
                        skipped_excluded += 1
                        continue
                    stxt = line.get("source_text")
                    if not (isinstance(stxt, str) and stxt.strip()):
                        if args.require_source_text:
                            ls_meta = (
                                line.get("ls_meta")
                                if isinstance(line.get("ls_meta"), dict)
                                else {}
                            )
                            print(
                                f"STOP — source_text manquant pour task_id={ls_meta.get('task_id')}",
                                file=sys.stderr,
                            )
                            return 2
                        missing_source_text += 1
                    f.write(json.dumps(line, ensure_ascii=False) + "\n")
                    written += 1
                    if args.limit is not None and written >= args.limit:
                        break
            else:
                best: dict[
                    tuple[str, str, str], tuple[dict[str, Any], float, str]
                ] = {}
                for line, s3_key, lm in iter_corpus_m12_objects_from_s3(
                    prefix=args.prefix
                ):
                    if not passes_common_filters(line):
                        continue
                    ident = _m12_identity(line)
                    if ident is None:
                        skipped_identity += 1
                        continue
                    if ident in excluded:
                        skipped_excluded += 1
                        continue
                    stxt = line.get("source_text")
                    if not (isinstance(stxt, str) and stxt.strip()):
                        if args.require_source_text:
                            ls_meta = (
                                line.get("ls_meta")
                                if isinstance(line.get("ls_meta"), dict)
                                else {}
                            )
                            print(
                                f"STOP — source_text manquant pour task_id={ls_meta.get('task_id')}",
                                file=sys.stderr,
                            )
                            return 2
                        missing_source_text += 1
                    ts = _last_modified_ts(lm)
                    prev = best.get(ident)
                    if prev is not None:
                        if ts < prev[1]:
                            skipped_r2_superseded += 1
                            continue
                        skipped_r2_superseded += 1
                    best[ident] = (line, ts, s3_key)

                if args.backfill_from_jsonl:
                    _ensure_src_path()
                    from src.annotation.m12_export_io import iter_m12_jsonl_lines

                    bf_path = Path(args.backfill_from_jsonl)
                    if not bf_path.is_file():
                        print(
                            f"Avertissement — backfill-from-jsonl introuvable : {bf_path}",
                            file=sys.stderr,
                        )
                    else:
                        for line in iter_m12_jsonl_lines(bf_path):
                            if not passes_common_filters(line):
                                continue
                            ident = _m12_identity(line)
                            if ident is None:
                                backfill_skipped_identity += 1
                                continue
                            if ident in best:
                                backfill_skipped_already_r2 += 1
                                continue
                            stxt = line.get("source_text")
                            if not (isinstance(stxt, str) and stxt.strip()):
                                if args.require_source_text:
                                    ls_meta = (
                                        line.get("ls_meta")
                                        if isinstance(line.get("ls_meta"), dict)
                                        else {}
                                    )
                                    print(
                                        f"STOP — source_text manquant (backfill) "
                                        f"task_id={ls_meta.get('task_id')}",
                                        file=sys.stderr,
                                    )
                                    return 2
                                missing_source_text += 1
                            best[ident] = (line, -1.0, "backfill:ls")
                            backfilled_from_ls += 1

                rows = sorted(best.values(), key=lambda t: _task_sort_tuple(t[0]))
                if args.limit is not None:
                    rows = rows[: args.limit]
                for line, _ts, _sk in rows:
                    f.write(json.dumps(line, ensure_ascii=False) + "\n")
                    written += 1
    except ValueError as e:
        if "S3_BUCKET" in str(e):
            print(
                "STOP — Export R2 : variables S3 / Cloudflare R2 requises "
                "(pas Label Studio).\n"
                "  Définir au minimum : S3_BUCKET, S3_ENDPOINT, "
                "S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY\n"
                "  (ou AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY).\n"
                "  Fichiers lus automatiquement : .env, .env.local, "
                "data/annotations/.r2_export_env\n"
                "  Modèle : data/annotations/r2_export.env.example\n"
                "  Doc : services/annotation-backend/ENVIRONMENT.md",
                file=sys.stderr,
            )
            return 4
        raise
    except ClientError as e:
        code = (e.response.get("Error") or {}).get("Code", "")
        if code == "RequestTimeTooSkewed":
            print(
                "STOP — RequestTimeTooSkewed : l’heure système Windows est trop décalée "
                "par rapport aux serveurs R2 (signature AWS).\n"
                "  Paramètres → Date et heure → Synchroniser maintenant.\n"
                "  Ou PowerShell admin : w32tm /resync",
                file=sys.stderr,
            )
            return 3
        raise

    print(
        f"Écrit {written} ligne(s) → {out_path} "
        f"(ignorés statut={skipped_status}, projet={skipped_project}, "
        f"exclu_ref={skipped_excluded}, sans_identité={skipped_identity}, "
        f"export_ok_filtré={skipped_export_ok}, révisions_R2_écrasées={skipped_r2_superseded}, "
        f"sans source_text comptés={missing_source_text}"
        + (
            f", backfill_LS_ajoutés={backfilled_from_ls}, "
            f"backfill_déjà_R2={backfill_skipped_already_r2}, "
            f"backfill_sans_identité={backfill_skipped_identity}"
            if args.backfill_from_jsonl
            else ""
        )
        + ")"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
