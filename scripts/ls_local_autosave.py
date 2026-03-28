"""
Auto-sauvegarde locale des annotations Label Studio — protection anti-perte enterprise.

Problème résolu :
  Label Studio (Railway) peut se déconnecter sans préavis. Sans ce script, les
  annotations non sauvegardées dans R2 (webhook désactivé ou erreurs réseau) sont
  définitivement perdues. 2 semaines de travail = 0 lignes exploitables.

Solution :
  Ce script poll l'API LS à intervalle régulier et écrit TOUTES les annotations
  dans un fichier JSONL local. Il est idempotent : une annotation déjà enregistrée
  n'est pas dupliquée (basé sur annotation_id).

Usage one-shot :
  python scripts/ls_local_autosave.py --project-id 2 --output data/annotations/ls_autosave.jsonl

  Copie miroir 100 % Label Studio (JSON API brut, sans conversion M12) :
  python scripts/ls_local_autosave.py --project-id 2 --write-raw-ls-json

  Uniquement le travail terminé (revue qualité sans tout le backlog) :
  python scripts/ls_local_autosave.py --project-id 2 --only-finished --output data/annotations/ls_finished.jsonl

  Seulement les annotations marquées « validées » dans LS :
  python scripts/ls_local_autosave.py --project-id 2 --only-finished --only-if-status annotated_validated ...

Usage daemon (boucle) :
  python scripts/ls_local_autosave.py --project-id 2 --output data/annotations/ls_autosave.jsonl --loop --interval 300

Par défaut, la QA stricte sur ``annotated_validated`` est désactivée : tout ce qui est
sur LS est sérialisé (``export_ok`` peut rester false si JSON/schéma KO ; ``raw_json_text``
et le fallback brut restent). Activez ``--enforce-validated-qa`` pour l'ancien comportement.

Prérequis :
  LABEL_STUDIO_URL  (ou LS_URL)
  LABEL_STUDIO_API_KEY  (ou LS_API_KEY)
  PSEUDONYM_SALT + ALLOW_WEAK_PSEUDONYMIZATION=1  (pour imports annotation-backend)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from ls_export_filters import filter_export_tasks

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_ANNOTATION_BACKEND = _PROJECT_ROOT / "services" / "annotation-backend"

for _p in (str(_ANNOTATION_BACKEND), str(_PROJECT_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _ls_url() -> str:
    u = os.environ.get("LABEL_STUDIO_URL", "").strip().rstrip("/")
    return u or os.environ.get("LS_URL", "").strip().rstrip("/")


def _ls_key() -> str:
    k = os.environ.get("LABEL_STUDIO_API_KEY", "").strip()
    return k or os.environ.get("LS_API_KEY", "").strip()


def _load_seen_ids(output_path: Path) -> set[int]:
    """Charge l'ensemble des annotation_id déjà sauvegardés (idempotence)."""
    if not output_path.exists():
        return set()
    seen: set[int] = set()
    try:
        for raw in output_path.read_text("utf-8").splitlines():
            if not raw.strip():
                continue
            try:
                obj = json.loads(raw)
                ann_id = obj.get("ls_meta", {}).get("annotation_id")
                if ann_id is not None:
                    seen.add(int(ann_id))
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
    except OSError as exc:
        logger.warning("Impossible de lire %s : %s", output_path, exc)
    return seen


def _run_once(
    project_id: int,
    output_path: Path,
    enforce_qa: bool,
    ls_url: str,
    ls_key: str,
    *,
    raw_ls_json_path: Path | None = None,
    only_finished: bool = False,
    only_if_status: str | None = None,
) -> int:
    """
    Exporte toutes les annotations du projet, écrit les nouvelles dans output_path.

    Retourne le nombre de nouvelles annotations écrites.
    """
    from ls_client import fetch_annotations
    from m12_export_line import ls_annotation_to_m12_v2_line

    seen = _load_seen_ids(output_path)
    logger.info(
        "Export projet %d — %d annotation(s) déjà sauvegardées", project_id, len(seen)
    )

    narrow_api = only_finished or bool((only_if_status or "").strip())
    try:
        tasks = fetch_annotations(
            project_id,
            ls_url,
            ls_key,
            download_all_tasks=False if narrow_api else None,
        )
    except Exception as exc:
        logger.error("Échec export LS projet %d : %s", project_id, exc)
        return 0

    n_before = len(tasks) if isinstance(tasks, list) else 0
    tasks = filter_export_tasks(
        tasks,
        only_finished=only_finished,
        require_annotation_status=only_if_status,
    )
    n_after = len(tasks)
    if narrow_api or only_finished or (only_if_status or "").strip():
        logger.info(
            "Filtre export : %d tâche(s) API → %d après only_finished=%s only_if_status=%r",
            n_before,
            n_after,
            only_finished,
            only_if_status or "",
        )

    if raw_ls_json_path is not None:
        raw_ls_json_path = raw_ls_json_path.resolve()
        raw_ls_json_path.parent.mkdir(parents=True, exist_ok=True)
        _fd, _tmp = tempfile.mkstemp(
            dir=raw_ls_json_path.parent,
            prefix=".tmp_raw_ls_",
            suffix=".json",
        )
        try:
            with os.fdopen(_fd, "w", encoding="utf-8") as rf:
                json.dump(tasks, rf, ensure_ascii=False, separators=(",", ":"))
            Path(_tmp).replace(raw_ls_json_path)
        except Exception:
            try:
                os.unlink(_tmp)
            except OSError:
                pass
            raise
        logger.info(
            "Miroir brut LS (API) → %s | %d tâche(s)",
            raw_ls_json_path,
            len(tasks) if isinstance(tasks, list) else -1,
        )

    # Validation explicite du format retourné par fetch_annotations
    if not isinstance(tasks, list) or not all(isinstance(task, dict) for task in tasks):
        logger.error(
            "Réponse inattendue de fetch_annotations pour le projet %d : "
            "attendu une liste de tâches (dict), reçu %r",
            project_id,
            type(tasks).__name__,
        )
        return 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    new_count = 0

    with output_path.open("a", encoding="utf-8") as fh:
        for task in tasks:
            for ann in task.get("annotations", []):
                ann_id = ann.get("id")
                if ann_id is not None and int(ann_id) in seen:
                    continue
                try:
                    line = ls_annotation_to_m12_v2_line(
                        ann,
                        task,
                        project_id,
                        enforce_validated_qa=enforce_qa,
                    )
                except Exception as exc:
                    logger.warning(
                        "Erreur conversion ann_id=%s task=%s : %s",
                        ann_id,
                        task.get("id"),
                        exc,
                    )
                    # Sauvegarder quand même sous forme brute pour ne rien perdre
                    line = {
                        "export_schema_version": "m12-v2-raw-fallback",
                        "export_ok": False,
                        "export_errors": [f"conversion_error:{exc!s}"[:120]],
                        "ls_meta": {
                            "task_id": task.get("id"),
                            "annotation_id": ann_id,
                            "project_id": project_id,
                            "exported_at": datetime.now(UTC).isoformat(),
                        },
                        "raw_annotation": ann,
                        "raw_task_data_keys": list((task.get("data") or {}).keys()),
                    }
                fh.write(json.dumps(line, ensure_ascii=False) + "\n")
                if ann_id is not None:
                    seen.add(int(ann_id))
                new_count += 1

    return new_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Auto-sauvegarde locale Label Studio → JSONL (anti-perte enterprise)"
    )
    parser.add_argument(
        "--project-id",
        type=int,
        required=True,
        help="ID du projet Label Studio",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/annotations/ls_autosave.jsonl",
        help="Chemin JSONL de sortie (défaut : data/annotations/ls_autosave.jsonl)",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Mode daemon : boucle infinie avec --interval secondes entre exports",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Intervalle en secondes entre exports (mode --loop, défaut 300 = 5 min)",
    )
    parser.add_argument(
        "--enforce-validated-qa",
        action="store_true",
        help=(
            "Si annotated_validated : marquer export_ok=false sur écarts schéma / "
            "finance / evidence (comportement strict). Par défaut : désactivé pour tout garder depuis LS."
        ),
    )
    parser.add_argument(
        "--write-raw-ls-json",
        nargs="?",
        const="__auto__",
        default=None,
        metavar="PATH",
        help=(
            "Après l'export API, écrit le JSON brut complet des tâches (miroir Label Studio). "
            "Sans PATH : data/annotations/ls_raw_project_<id>.json"
        ),
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Appelle seulement GET /api/projects/<id>/ (vérifie URL + token Access Token LS)",
    )
    parser.add_argument(
        "--only-finished",
        action="store_true",
        help=(
            "Exclut les annotations annulées et sans ``result`` ; API sans tâches vides "
            "(download_all_tasks=false). Idéal pour contrôler le travail déjà soumis."
        ),
    )
    parser.add_argument(
        "--only-if-status",
        type=str,
        default=None,
        metavar="STATUS",
        help=(
            "N'exporter que les annotations dont le choix LS ``annotation_status`` "
            "vaut exactement cette valeur (ex. annotated_validated). "
            "Peut se combiner avec --only-finished."
        ),
    )
    args = parser.parse_args()

    ls_url = _ls_url()
    ls_key = _ls_key()
    if not ls_url or not ls_key:
        sys.exit(
            "STOP — LABEL_STUDIO_URL (ou LS_URL) et LABEL_STUDIO_API_KEY (ou LS_API_KEY) requis"
        )

    if args.verify_only:
        from ls_client import fetch_project_meta

        try:
            meta = fetch_project_meta(args.project_id, ls_url, ls_key)
        except Exception as exc:
            sys.exit(f"VERIFY FAIL — {type(exc).__name__}: {exc}")
        title = meta.get("title", "?")
        ntasks = meta.get("task_count", meta.get("num_tasks", "?"))
        print(
            f"VERIFY OK — project_id={args.project_id} title={title!r} task_count={ntasks}"
        )
        return

    output_path = Path(args.output)
    enforce_qa = args.enforce_validated_qa

    raw_ls_path: Path | None = None
    if args.write_raw_ls_json == "__auto__":
        raw_ls_path = (
            _PROJECT_ROOT
            / "data"
            / "annotations"
            / f"ls_raw_project_{args.project_id}.json"
        )
    elif args.write_raw_ls_json:
        raw_ls_path = Path(args.write_raw_ls_json)

    only_if_status = (args.only_if_status or "").strip() or None

    logger.info(
        "=== ls_local_autosave | projet=%d | output=%s | loop=%s | interval=%ds | "
        "enforce_validated_qa=%s | raw_ls_json=%s | only_finished=%s | only_if_status=%r ===",
        args.project_id,
        output_path,
        args.loop,
        args.interval,
        enforce_qa,
        raw_ls_path or "off",
        args.only_finished,
        only_if_status or "",
    )

    if not args.loop:
        n = _run_once(
            args.project_id,
            output_path,
            enforce_qa,
            ls_url,
            ls_key,
            raw_ls_json_path=raw_ls_path,
            only_finished=args.only_finished,
            only_if_status=only_if_status,
        )
        logger.info("Terminé — %d nouvelle(s) annotation(s) sauvegardée(s)", n)
        return

    while True:
        try:
            n = _run_once(
                args.project_id,
                output_path,
                enforce_qa,
                ls_url,
                ls_key,
                raw_ls_json_path=raw_ls_path,
                only_finished=args.only_finished,
                only_if_status=only_if_status,
            )
            logger.info(
                "[LOOP] %d nouvelle(s) | prochain export dans %ds",
                n,
                args.interval,
            )
        except KeyboardInterrupt:
            logger.info("Arrêt demandé (Ctrl+C)")
            break
        except Exception as exc:
            logger.error(
                "[LOOP] Erreur inattendue : %s — retry dans %ds", exc, args.interval
            )
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
