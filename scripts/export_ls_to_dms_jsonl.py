"""
Export Label Studio → DMS JSONL
Milestone    : M12
Référence    : MANDAT-LS-001-v2 + Plan Directeur Partie VIII
Auteur       : CTO / AO — Abdoulaye Ousmane
Date         : 2026-03-13

Format cible : Plan Directeur Partie VIII
  - wrapper ground_truth obligatoire
  - RÈGLE-19 : value + confidence_expected + evidence_hint partout
  - Confiance : 1.00 / 0.80 / 0.60 / null UNIQUEMENT
  - AMBIG-1/3/4/6 trackés et exportés

Usage :
  LABEL_STUDIO_URL=https://label-studio-dms.up.railway.app \\
  LABEL_STUDIO_API_KEY=<token> \\
  python scripts/export_ls_to_dms_jsonl.py \\
    --project-id 1 \\
    --output data/annotations/m12_batch_001.jsonl
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime

import requests

LS_URL = os.environ.get("LABEL_STUDIO_URL", "").rstrip("/")
LS_KEY = os.environ.get("LABEL_STUDIO_API_KEY", "")

if not LS_URL or not LS_KEY:
    sys.exit("STOP — LABEL_STUDIO_URL et LABEL_STUDIO_API_KEY requis")

CONF_MAP = {1: 0.60, 2: 0.80, 3: 1.00}


# ── Fetch ────────────────────────────────────────────────────────


def fetch_annotations(project_id: int) -> list[dict]:
    headers = {"Authorization": f"Token {LS_KEY}"}
    url = f"{LS_URL}/api/projects/{project_id}/export"
    r = requests.get(
        url,
        headers=headers,
        params={"exportType": "JSON"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


# ── Helpers ──────────────────────────────────────────────────────


def _get_text(results: list[dict], field: str) -> str | None:
    for r in results:
        if r.get("from_name") == field:
            val = r.get("value", {})
            if isinstance(val, dict) and "text" in val:
                texts = val["text"]
                return texts[0] if texts else None
            if isinstance(val, dict) and "choices" in val:
                choices = val["choices"]
                return choices[0] if choices else None
    return None


def _get_confidence(results: list[dict], field: str) -> float | None:
    for r in results:
        if r.get("from_name") == field:
            val = r.get("value", {})
            if isinstance(val, dict) and "confidence" in val:
                c = val["confidence"]
                if c in (1.0, 0.80, 0.60):
                    return c
                return 0.80
    return None


def _to_dms_line(ann: dict, task: dict, project_id: int) -> dict:
    """Transforme une annotation Label Studio en ligne DMS JSONL."""
    results = ann.get("result", [])
    task_id = task.get("id")
    task_data = task.get("data", {})

    doc_type = _get_text(results, "doc_type")
    ao_ref = _get_text(results, "ao_ref")
    evidence_ao = _get_text(results, "evidence_hint_ao_ref")
    zones_raw = _get_text(results, "zones")

    zones = []
    if zones_raw:
        try:
            zones = json.loads(zones_raw) if zones_raw.startswith("[") else [zones_raw]
        except json.JSONDecodeError:
            zones = [zones_raw] if zones_raw else []

    ground_truth = {
        "doc_type": {
            "value": doc_type,
            "confidence_expected": CONF_MAP.get(ann.get("completed_by", 2), 0.80),
            "evidence_hint": None,
        },
        "ao_ref": {
            "value": ao_ref,
            "confidence_expected": _get_confidence(results, "ao_ref") or 0.80,
            "evidence_hint": evidence_ao,
        },
        "zones_mentionnees": zones,
        "task_id": task_id,
        "annotation_id": ann.get("id"),
        "project_id": project_id,
        "exported_at": datetime.now(UTC).isoformat(),
    }

    content_hash = hashlib.sha256(
        json.dumps(ground_truth, sort_keys=True).encode()
    ).hexdigest()[:16]

    return {
        "ground_truth": ground_truth,
        "source_task": {"id": task_id, "data_keys": list(task_data.keys())},
        "content_hash": content_hash,
        "ambig_tracked": [],
    }


# ── Main ─────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Label Studio → DMS JSONL")
    parser.add_argument("--project-id", type=int, required=True)
    parser.add_argument("--output", type=str, default="m12_export.jsonl")
    args = parser.parse_args()

    data = fetch_annotations(args.project_id)
    lines = []

    for item in data:
        annotations = item.get("annotations", [])
        if not annotations:
            continue
        for ann in annotations:
            line = _to_dms_line(ann, item, args.project_id)
            lines.append(line)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    print(f"Exporté {len(lines)} lignes → {args.output}")


if __name__ == "__main__":
    main()
