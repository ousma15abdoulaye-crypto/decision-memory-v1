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

Usage daemon (boucle) :
  python scripts/ls_local_autosave.py --project-id 2 --output data/annotations/ls_autosave.jsonl --loop --interval 300

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
import time
from datetime import UTC, datetime
from pathlib import Path

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

    try:
        tasks = fetch_annotations(project_id, ls_url, ls_key)
    except Exception as exc:
        logger.error("Échec export LS projet %d : %s", project_id, exc)
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
        "--no-enforce-validated-qa",
        action="store_true",
        help="Ne pas exiger QA stricte (utile pour sauvegarder même les partiels)",
    )
    args = parser.parse_args()

    ls_url = _ls_url()
    ls_key = _ls_key()
    if not ls_url or not ls_key:
        sys.exit(
            "STOP — LABEL_STUDIO_URL (ou LS_URL) et LABEL_STUDIO_API_KEY (ou LS_API_KEY) requis"
        )

    output_path = Path(args.output)
    enforce_qa = not args.no_enforce_validated_qa

    logger.info(
        "=== ls_local_autosave | projet=%d | output=%s | loop=%s | interval=%ds ===",
        args.project_id,
        output_path,
        args.loop,
        args.interval,
    )

    if not args.loop:
        n = _run_once(args.project_id, output_path, enforce_qa, ls_url, ls_key)
        logger.info("Terminé — %d nouvelle(s) annotation(s) sauvegardée(s)", n)
        return

    while True:
        try:
            n = _run_once(args.project_id, output_path, enforce_qa, ls_url, ls_key)
            logger.info(
                "[LOOP] %d nouvelle(s) | prochain export dans %ds",
                n,
                args.interval,
            )
        except KeyboardInterrupt:
            logger.info("Arrêt demandé (Ctrl+C)")
            break
        except Exception as exc:
            logger.error("[LOOP] Erreur inattendue : %s — retry dans %ds", exc, args.interval)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
