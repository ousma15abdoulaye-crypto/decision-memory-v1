#!/usr/bin/env python3
"""Audit « dry-run » d'un export JSONL M12 : inventaire + verdict exploitabilité.

Sans écriture DB ni appel réseau — agrège
``scripts/inventory_m12_corpus_jsonl.py`` et ``scripts/verify_m12_jsonl_corpus.py``.

Usage ::
    python scripts/dry_run_m12_export_audit.py data/annotations/m12_export.jsonl
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module(name: str, filename: str):
    path = REPO_ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Chargement impossible : {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit sec JSONL M12 (inventaire + verdict)"
    )
    parser.add_argument(
        "jsonl",
        type=Path,
        help="Fichier .jsonl",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Sortie JSON unique sur stdout",
    )
    args = parser.parse_args()
    p = args.jsonl
    if not p.is_file():
        print(f"STOP — fichier introuvable : {p}", file=sys.stderr)
        return 2

    sys.path.insert(0, str(REPO_ROOT))
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

    inv_mod = _load_script_module(
        "inventory_m12_corpus_jsonl", "inventory_m12_corpus_jsonl.py"
    )
    ver_mod = _load_script_module(
        "verify_m12_jsonl_corpus", "verify_m12_jsonl_corpus.py"
    )
    inventory_scan = inv_mod._scan_file
    verify_scan = ver_mod._scan
    verdict_fn = ver_mod._verdict

    inv = inventory_scan(p)
    ver = verify_scan(p)
    verdict, notes = verdict_fn(ver)

    if args.json:
        out = {
            "path": str(p.resolve()),
            "inventory": inv,
            "verify": {k: v for k, v in ver.items() if k != "path"},
            "verdict": verdict,
            "verdict_notes": notes,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
        return 0

    print("=== Inventaire (inventory_m12_corpus_jsonl) ===")
    for k, v in inv.items():
        if k == "path":
            continue
        print(f"  {k}: {v}")
    print()
    print("=== Vérification (verify_m12_jsonl_corpus) ===")
    print(f"  Lignes : {ver['lines']}")
    print(f"  Verdict : {verdict}")
    for line in notes:
        print(f"    — {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
