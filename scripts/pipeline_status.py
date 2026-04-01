#!/usr/bin/env python3
"""Dashboard console du pipeline DMS — etat Label Studio + corpus JSONL.

Usage :
    python scripts/pipeline_status.py
    python scripts/pipeline_status.py --json

Requis (optionnel — affiche ce qui est disponible) :
    LABEL_STUDIO_URL + LABEL_STUDIO_API_KEY (ou .env.local)
"""

import argparse
import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(REPO_ROOT / ".env.local")
except ImportError:
    pass


def _ls_status() -> dict | None:
    """Interroge Label Studio pour obtenir les stats du projet."""
    url = os.environ.get("LABEL_STUDIO_URL") or os.environ.get("LS_URL", "")
    token = os.environ.get("LABEL_STUDIO_API_KEY") or os.environ.get("LS_API_KEY", "")
    project_id = os.environ.get("LABEL_STUDIO_PROJECT_ID", "1")

    if not url or not token:
        return None

    try:
        import requests

        verify = os.environ.get("LABEL_STUDIO_SSL_VERIFY", "1") != "0"
        headers = {"Authorization": f"Token {token}"}

        resp = requests.get(
            f"{url.rstrip('/')}/api/projects/{project_id}",
            headers=headers,
            verify=verify,
            timeout=15,
        )
        resp.raise_for_status()
        project = resp.json()

        return {
            "project_id": project_id,
            "title": project.get("title", ""),
            "total_tasks": project.get("task_number", 0),
            "total_annotations": project.get("num_tasks_with_annotations", 0),
            "skipped": project.get("skipped_annotations_number", 0),
        }
    except Exception as exc:
        return {"error": str(exc)}


def _corpus_status() -> dict:
    """Analyse les fichiers JSONL du corpus local."""
    corpus_dir = REPO_ROOT / "data" / "annotations"
    result = {"files": {}, "total_lines": 0, "export_ok_count": 0, "by_kind": {}}

    for jsonl_file in sorted(corpus_dir.glob("*.jsonl")):
        lines = 0
        export_ok = 0
        kinds: dict[str, int] = {}

        try:
            with open(jsonl_file, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    lines += 1
                    try:
                        obj = json.loads(line)
                        if obj.get("export_ok") is True:
                            export_ok += 1
                        kind = (
                            obj.get("dms_annotation", {})
                            .get("couche_1_routing", {})
                            .get("taxonomy_core", "unknown")
                        )
                        kinds[kind] = kinds.get(kind, 0) + 1
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass

        result["files"][jsonl_file.name] = {
            "lines": lines,
            "export_ok": export_ok,
        }
        result["total_lines"] += lines
        result["export_ok_count"] += export_ok
        for k, v in kinds.items():
            result["by_kind"][k] = result["by_kind"].get(k, 0) + v

    return result


def _pipeline_runs_status() -> dict:
    """Analyse les pipeline runs persistes."""
    runs_dir = REPO_ROOT / "data" / "annotation_pipeline_runs"
    if not runs_dir.is_dir():
        return {"runs_dir_exists": False}

    total = 0
    by_state: dict[str, int] = {}

    for json_file in runs_dir.glob("*.json"):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            state = data.get("state", "unknown")
            by_state[state] = by_state.get(state, 0) + 1
            total += 1
        except Exception:
            pass

    return {"total_runs": total, "by_state": by_state}


def main():
    parser = argparse.ArgumentParser(description="DMS Pipeline Status Dashboard")
    parser.add_argument(
        "--json", action="store_true", help="Sortie JSON au lieu du tableau"
    )
    args = parser.parse_args()

    report = {
        "label_studio": _ls_status(),
        "corpus": _corpus_status(),
        "pipeline_runs": _pipeline_runs_status(),
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    print("=" * 60)
    print("  DMS PIPELINE STATUS DASHBOARD")
    print("=" * 60)

    # Label Studio
    ls = report["label_studio"]
    print("\n-- Label Studio --")
    if ls is None:
        print("  Non configure (LABEL_STUDIO_URL / LABEL_STUDIO_API_KEY manquants)")
    elif "error" in ls:
        print(f"  Erreur : {ls['error']}")
    else:
        print(f"  Projet   : {ls.get('title', 'N/A')} (id={ls['project_id']})")
        print(f"  Tasks    : {ls['total_tasks']}")
        print(f"  Annotees : {ls['total_annotations']}")
        print(f"  Skipped  : {ls['skipped']}")

    # Corpus
    corpus = report["corpus"]
    print("\n-- Corpus JSONL --")
    print(f"  Lignes totales   : {corpus['total_lines']}")
    print(f"  export_ok=true   : {corpus['export_ok_count']}")
    if corpus["files"]:
        print("  Fichiers :")
        for fname, info in corpus["files"].items():
            print(
                f"    {fname} : {info['lines']} lignes, {info['export_ok']} export_ok"
            )
    if corpus["by_kind"]:
        print("  Par document_kind :")
        for kind, count in sorted(corpus["by_kind"].items(), key=lambda x: -x[1]):
            print(f"    {kind:30s} : {count}")

    # Pipeline runs
    runs = report["pipeline_runs"]
    print("\n-- Pipeline Runs --")
    if not runs.get("runs_dir_exists", True):
        print("  Repertoire data/annotation_pipeline_runs/ absent")
    else:
        print(f"  Total runs : {runs.get('total_runs', 0)}")
        for state, count in sorted(runs.get("by_state", {}).items()):
            print(f"    {state:30s} : {count}")

    # M15 Gate progress
    target = 50
    current = corpus["export_ok_count"]
    remaining = max(0, target - current)
    pct = min(100, int(current / target * 100)) if target > 0 else 0
    print("\n-- M15 Gate Progress --")
    print(f"  Objectif : {target} annotated_validated")
    print(f"  Actuel   : {current} ({pct}%)")
    print(f"  Restant  : {remaining}")
    bar_len = 40
    filled = int(bar_len * pct / 100)
    bar = "#" * filled + "-" * (bar_len - filled)
    print(f"  [{bar}] {pct}%")
    print()


if __name__ == "__main__":
    main()
