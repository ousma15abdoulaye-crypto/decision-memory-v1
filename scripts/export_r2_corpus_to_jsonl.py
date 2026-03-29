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

Usage :
  set S3_BUCKET=...
  set S3_ENDPOINT=...
  set S3_ACCESS_KEY_ID=...
  set S3_SECRET_ACCESS_KEY=...
  # Sortie par défaut (sans -o) : data/annotations/m12_corpus_authoritative.jsonl
  # Surcharge : variable d'environnement M12_R2_EXPORT_JSONL ou R2_EXPORT_JSONL
  python scripts/export_r2_corpus_to_jsonl.py --no-status-filter

  python scripts/export_r2_corpus_to_jsonl.py -o data/annotations/m12_corpus_50.jsonl

  # Filtrer comme le gate webhook (défaut : annotated_validated)
  python scripts/export_r2_corpus_to_jsonl.py --status annotated_validated

  # Limiter (ex. test)
  python scripts/export_r2_corpus_to_jsonl.py --limit 50

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

from botocore.exceptions import ClientError
from dotenv import load_dotenv

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_ANNOTATION_BACKEND = _PROJECT_ROOT / "services" / "annotation-backend"


def _ensure_annotation_path() -> None:
    p = str(_ANNOTATION_BACKEND)
    if p not in sys.path:
        sys.path.insert(0, p)


def _default_r2_export_jsonl_path() -> Path:
    """
    Chemin JSONL canonique local pour l'export R2 (aligné data/annotations/README.md).

    Priorité : ``M12_R2_EXPORT_JSONL``, puis ``R2_EXPORT_JSONL``, sinon
    ``data/annotations/m12_corpus_authoritative.jsonl`` sous la racine du dépôt.
    """
    env = (
        os.environ.get("M12_R2_EXPORT_JSONL") or os.environ.get("R2_EXPORT_JSONL") or ""
    ).strip()
    if env:
        return Path(env)
    return _PROJECT_ROOT / "data" / "annotations" / "m12_corpus_authoritative.jsonl"


def main() -> int:
    load_dotenv(_PROJECT_ROOT / ".env")
    load_dotenv(_PROJECT_ROOT / ".env.local")

    parser = argparse.ArgumentParser(
        description="Export corpus m12-v2 depuis R2/S3 → un fichier JSONL (une ligne JSON par objet)"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help=(
            "Fichier JSONL de sortie (defaut : data/annotations/m12_corpus_authoritative.jsonl "
            "ou M12_R2_EXPORT_JSONL / R2_EXPORT_JSONL)"
        ),
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
        help="Ne garder que ls_meta.annotation_status == cette valeur si --accepted-statuses absent",
    )
    parser.add_argument(
        "--accepted-statuses",
        type=str,
        default=None,
        help=(
            "Liste CSV de statuts LS acceptés (ex. annotated_validated,annotated). "
            "Si défini, remplace le filtre --status unique."
        ),
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
    args = parser.parse_args()

    accepted: set[str] | None = None
    if args.accepted_statuses is not None and args.accepted_statuses.strip():
        accepted = {s.strip() for s in args.accepted_statuses.split(",") if s.strip()}

    _ensure_annotation_path()
    from corpus_sink import iter_corpus_m12_lines_from_s3

    out_path = (
        args.output
        if args.output and str(args.output).strip()
        else str(_default_r2_export_jsonl_path().resolve())
    )
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped_status = 0
    skipped_project = 0
    missing_source_text = 0

    with open(out_path, "w", encoding="utf-8") as f:
        try:
            for line in iter_corpus_m12_lines_from_s3(prefix=args.prefix):
                ls_meta = (
                    line.get("ls_meta") if isinstance(line.get("ls_meta"), dict) else {}
                )
                if not args.no_status_filter:
                    st = (ls_meta.get("annotation_status") or "").strip()
                    if accepted is not None:
                        if st not in accepted:
                            skipped_status += 1
                            continue
                    elif st != args.status:
                        skipped_status += 1
                        continue
                if args.project_id is not None:
                    pid = ls_meta.get("project_id")
                    if pid is None or int(pid) != args.project_id:
                        skipped_project += 1
                        continue

                stxt = line.get("source_text")
                if not (isinstance(stxt, str) and stxt.strip()):
                    if args.require_source_text:
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
        f"Ecrit {written} ligne(s) -> {out_path} "
        f"(ignores statut={skipped_status}, projet={skipped_project}, "
        f"sans source_text comptes={missing_source_text})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
