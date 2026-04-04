#!/usr/bin/env python3
"""
export_labelstudio_to_registry.py — V1 fallback Activation Wartime M15.

Exporte les annotations depuis Label Studio et les insere dans
public.annotation_registry sur Railway.

Ce script est le fallback V1 quand la DB locale Docker est inaccessible.

Pre-requis :
  - LABEL_STUDIO_URL : URL Label Studio (Railway)
  - LABEL_STUDIO_API_KEY : token API valide (regenerer si expire 401)
  - LABEL_STUDIO_PROJECT_ID : ID du projet (defaut: 1)
  - RAILWAY_DATABASE_URL : URL Railway (via with_railway_env.py)

Usage :
  python scripts/with_railway_env.py python scripts/export_labelstudio_to_registry.py --dry-run
  python scripts/with_railway_env.py python scripts/export_labelstudio_to_registry.py --apply

Pour regenerer le token Label Studio :
  1. Aller sur https://label-studio-production-1f72.up.railway.app
  2. Account > Access Token
  3. Regenerer et mettre a jour LABEL_STUDIO_API_KEY dans .env.local

Gate de sortie V1 :
  SELECT COUNT(*) FROM public.annotation_registry WHERE is_validated = true >= 50
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("[ERR] requests non installe. pip install requests", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

GATE_MIN_VALIDATED = 50


def _get_ls_config() -> dict:
    """Recupere la config Label Studio depuis les variables d'env."""
    url = os.environ.get("LABEL_STUDIO_URL", "").rstrip("/")
    api_key = os.environ.get("LABEL_STUDIO_API_KEY", "")
    project_id = int(os.environ.get("LABEL_STUDIO_PROJECT_ID", "1"))

    missing = []
    if not url:
        missing.append("LABEL_STUDIO_URL")
    if not api_key:
        missing.append("LABEL_STUDIO_API_KEY")

    if missing:
        print(
            f"{RED}[ERR]{RESET} Variables manquantes : {', '.join(missing)}\n"
            "  Definir dans .env.local ou en variables d'env.",
            file=sys.stderr,
        )
        sys.exit(2)

    return {"url": url, "api_key": api_key, "project_id": project_id}


def _ls_headers(api_key: str) -> dict:
    return {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}


def _ls_verify_tls() -> bool:
    """TLS verification on by default; set LABEL_STUDIO_SSL_VERIFY=0 if needed (E-68)."""
    return os.environ.get("LABEL_STUDIO_SSL_VERIFY", "1") != "0"


def probe_label_studio(config: dict) -> dict:
    """Verifie la connexion LS et retourne les stats du projet."""
    url = config["url"]
    api_key = config["api_key"]
    project_id = config["project_id"]

    try:
        resp = requests.get(
            f"{url}/api/projects/{project_id}/",
            headers=_ls_headers(api_key),
            timeout=15,
            verify=_ls_verify_tls(),
        )
        if resp.status_code == 401:
            print(
                f"{RED}[ERR 401]{RESET} Token Label Studio expire ou invalide.\n"
                "  -> Regenerer le token sur l'interface LS : Account > Access Token\n"
                "  -> Mettre a jour LABEL_STUDIO_API_KEY dans .env.local",
                file=sys.stderr,
            )
            sys.exit(3)
        resp.raise_for_status()
        data = resp.json()
        return {
            "title": data.get("title", "?"),
            "task_count": data.get("task_number", 0),
            "annotation_count": data.get("total_annotations_number", 0),
            "tasks_with_annotations": data.get("num_tasks_with_annotations", 0),
        }
    except requests.RequestException as exc:
        print(f"{RED}[ERR]{RESET} Label Studio inaccessible : {exc}", file=sys.stderr)
        sys.exit(4)


def fetch_annotations_from_ls(config: dict, page_size: int = 100) -> list[dict]:
    """Exporte toutes les annotations depuis l'API Label Studio."""
    url = config["url"]
    api_key = config["api_key"]
    project_id = config["project_id"]

    all_tasks = []
    page = 1

    while True:
        resp = requests.get(
            f"{url}/api/tasks/",
            headers=_ls_headers(api_key),
            params={
                "project": project_id,
                "page": page,
                "page_size": page_size,
                "fields": "all",
            },
            timeout=30,
            verify=_ls_verify_tls(),
        )
        resp.raise_for_status()
        data = resp.json()

        tasks = data.get("tasks", data) if isinstance(data, dict) else data
        if not tasks:
            break

        all_tasks.extend(tasks)
        logger.info(
            "Page %d : %d taches chargees (total: %d)", page, len(tasks), len(all_tasks)
        )

        if isinstance(data, dict) and not data.get("next"):
            break
        if len(tasks) < page_size:
            break

        page += 1

    return all_tasks


def _extract_doc_reference(task: dict) -> str | None:
    """Extrait la reference du document depuis la tache LS."""
    data = task.get("data", {})
    for field in ("document_id", "doc_id", "file_name", "text", "url"):
        if field in data and data[field]:
            return str(data[field])[:255]
    return str(task.get("id"))


def _build_registry_row(task: dict) -> dict | None:
    """Construit une ligne annotation_registry depuis une tache LS."""
    annotations = task.get("annotations", [])
    if not annotations:
        return None

    annotation = annotations[0]
    annotated_by = annotation.get("completed_by", {})
    if isinstance(annotated_by, dict):
        annotated_by = annotated_by.get(
            "username", annotated_by.get("email", "label_studio")
        )

    created_at_raw = annotation.get("created_at") or task.get("created_at")
    updated_at_raw = annotation.get("updated_at") or created_at_raw

    is_validated = annotation.get("was_cancelled", False) is False
    doc_ref = _extract_doc_reference(task)

    # FK documents(id) : utiliser l'ID metier dans task.data, pas l'ID tache LS (Copilot)
    data = task.get("data") or {}
    document_id_fk: str | None = None
    for key in ("document_id", "doc_id"):
        raw = data.get(key)
        if raw is not None and str(raw).strip():
            document_id_fk = str(raw).strip()[:255]
            break

    row_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"ls_task_{task['id']}"))
    sha256 = hashlib.sha256(
        json.dumps(annotation.get("result", []), sort_keys=True).encode()
    ).hexdigest()

    return {
        "id": row_id,
        "document_id": document_id_fk,
        "annotation_file": doc_ref,
        "sha256": sha256,
        "document_type": "label_studio_export",
        "annotated_by": str(annotated_by)[:100],
        "annotated_at": updated_at_raw,
        "duration_min": annotation.get("lead_time"),
        "field_count": len(annotation.get("result", [])),
        "criteria_count": None,
        "is_validated": is_validated,
        "validated_at": updated_at_raw if is_validated else None,
        "created_at": created_at_raw or datetime.now(UTC).isoformat(),
    }


def import_rows_to_railway(rows: list[dict], railway_url: str, dry_run: bool) -> dict:
    """Importe les lignes dans public.annotation_registry Railway."""
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        print(f"{RED}[ERR]{RESET} psycopg non installe.", file=sys.stderr)
        sys.exit(1)

    url = railway_url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgres://", "postgresql://", 1
    )
    conn = psycopg.connect(url, row_factory=dict_row, connect_timeout=20)

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id::text FROM public.annotation_registry")
            existing = {r["id"] for r in cur.fetchall()}
            logger.info("Railway : %d entrees existantes", len(existing))

            to_insert = [r for r in rows if r["id"] not in existing]
            logger.info("%d lignes a inserer", len(to_insert))

            if dry_run:
                print(
                    f"  {YELLOW}[DRY-RUN]{RESET} {len(to_insert)} lignes seraient inserees."
                )
                conn.rollback()
                conn.close()
                return {"inserted": 0, "to_insert": len(to_insert), "dry_run": True}

            cols = [
                "id",
                "document_id",
                "annotation_file",
                "sha256",
                "document_type",
                "annotated_by",
                "annotated_at",
                "duration_min",
                "field_count",
                "criteria_count",
                "is_validated",
                "validated_at",
                "created_at",
            ]

            inserted = errors = 0
            for row in to_insert:
                try:
                    placeholders = ", ".join(f"%({c})s" for c in cols)
                    col_list = ", ".join(cols)
                    cur.execute(
                        f"INSERT INTO public.annotation_registry ({col_list}) "
                        f"VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING",
                        {c: row.get(c) for c in cols},
                    )
                    inserted += cur.rowcount
                except Exception as exc:
                    errors += 1
                    logger.error("ERR insert %s: %s", row.get("id"), exc)

            if errors:
                conn.rollback()
                conn.close()
                return {"inserted": 0, "errors": errors, "rolled_back": True}

            cur.execute(
                "SELECT COUNT(*) as cnt FROM public.annotation_registry WHERE is_validated = true"
            )
            validated_count = cur.fetchone()["cnt"]
            conn.commit()
            conn.close()

            return {
                "inserted": inserted,
                "errors": errors,
                "validated_count_post_sync": validated_count,
                "gate_regle23": validated_count >= GATE_MIN_VALIDATED,
            }

    except Exception:
        conn.rollback()
        conn.close()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export Label Studio -> annotation_registry Railway (V1 fallback M15)"
    )
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--export-jsonl",
        type=str,
        default=None,
        help="Sauvegarder les taches LS en JSONL avant import",
    )
    args = parser.parse_args()

    dry_run = not args.apply

    print(
        f"\n{BOLD}EXPORT LABEL STUDIO -> annotation_registry (V1 fallback M15){RESET}"
    )
    print(f"Mode : {'DRY-RUN' if dry_run else 'APPLY'}")
    print()

    config = _get_ls_config()
    railway_url = os.environ.get("RAILWAY_DATABASE_URL", "")
    if not railway_url:
        print(f"{RED}[ERR]{RESET} RAILWAY_DATABASE_URL manquante.", file=sys.stderr)
        return 2

    # Probe LS
    print(f"  {BLUE}[PROBE LS]{RESET} Connexion Label Studio...")
    stats = probe_label_studio(config)
    print(f"  Projet : {stats['title']}")
    print(f"  Taches : {stats['task_count']}")
    print(f"  Annotations : {stats['annotation_count']}")
    print(f"  Taches annotees : {stats['tasks_with_annotations']}")
    print()

    # Export LS
    print(f"  {BLUE}[EXPORT]{RESET} Chargement des taches annotees...")
    tasks = fetch_annotations_from_ls(config)
    annotated_tasks = [t for t in tasks if t.get("annotations")]
    print(f"  Taches avec annotations : {len(annotated_tasks)} / {len(tasks)}")

    # Convertir en lignes registry
    rows = []
    for task in annotated_tasks:
        row = _build_registry_row(task)
        if row:
            rows.append(row)

    validated_rows = [r for r in rows if r.get("is_validated")]
    print(
        f"  Lignes converties : {len(rows)} (is_validated=true: {len(validated_rows)})"
    )

    # Export JSONL optionnel
    if args.export_jsonl:
        path = Path(args.export_jsonl)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        print(f"  JSONL backup : {path}")

    if not rows:
        print(
            f"\n{YELLOW}[WARN]{RESET} Aucune annotation recuperee depuis Label Studio."
        )
        return 0

    # Import Railway
    print(f"\n  {BLUE}[IMPORT]{RESET} Import dans annotation_registry Railway...")
    result = import_rows_to_railway(rows, railway_url, dry_run)

    print(f"\n{BOLD}Resultat :{RESET}")
    for k, v in result.items():
        print(f"  {k:35}: {v}")

    if not dry_run:
        validated = result.get("validated_count_post_sync", 0)
        gate_ok = result.get("gate_regle23", False)
        color = GREEN if gate_ok else RED
        label = "VERT" if gate_ok else "ROUGE"
        print(f"\n{BOLD}Gate REGLE-23{RESET}")
        print(
            f"  {color}[{label}]{RESET} is_validated = {validated} (seuil: {GATE_MIN_VALIDATED})"
        )
        if not gate_ok:
            delta = GATE_MIN_VALIDATED - validated
            print(
                f"  Delta : {delta} annotations manquantes. Annoter {delta} docs de plus dans LS."
            )

    return 0 if result.get("gate_regle23", dry_run) else 3


if __name__ == "__main__":
    raise SystemExit(main())
