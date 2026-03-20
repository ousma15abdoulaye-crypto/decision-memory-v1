#!/usr/bin/env python3
"""
Smoke M12 — annotation-backend health + /predict minimal.
Usage : définir ANNOTATION_BACKEND_URL (sans slash final).

Exit 0 : succès ou skip si URL non définie (CI / poste sans prod).
Exit 1 : health KO ou /predict structure invalide.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    base = os.environ.get("ANNOTATION_BACKEND_URL", "").strip().rstrip("/")
    if not base:
        print("[SKIP] ANNOTATION_BACKEND_URL non défini — smoke non exécuté")
        return 0

    # Health
    try:
        req = urllib.request.Request(
            f"{base}/health",
            method="GET",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        print(f"[FAIL] GET /health : {e}")
        return 1

    if body.get("status") != "ok":
        print(f"[FAIL] /health inattendu : {body}")
        return 1
    print(f"[OK] /health — schema={body.get('schema')} model={body.get('model')}")

    # Setup
    try:
        req = urllib.request.Request(
            f"{base}/setup",
            data=b"{}",
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            setup = json.loads(resp.read().decode())
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        print(f"[FAIL] POST /setup : {e}")
        return 1

    if setup.get("status") != "ready":
        print(f"[WARN] /setup : {setup}")

    # Predict — texte minimal (sans appel Mistral réel si clé absente : attendre fallback JSON)
    payload = {
        "tasks": [
            {
                "id": 1,
                "data": {
                    "text": "Smoke M12 — document test minimal pour pipeline.",
                    "document_role": "supporting_doc",
                },
            }
        ],
        "document_role": "supporting_doc",
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{base}/predict",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            pred = json.loads(resp.read().decode())
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        print(f"[FAIL] POST /predict : {e}")
        return 1

    results = pred.get("results") or []
    if not results:
        print(f"[FAIL] /predict sans results : {pred}")
        return 1

    r0 = results[0]
    res_list = r0.get("result") or []
    if not res_list:
        print(f"[FAIL] result vide : {r0}")
        return 1

    block = res_list[0]
    if block.get("to_name") != "document_text":
        print(
            f"[FAIL] to_name doit être document_text (E-66), got {block.get('to_name')}"
        )
        return 1

    texts = (block.get("value") or {}).get("text") or []
    if not texts or not str(texts[0]).strip():
        print("[FAIL] value.text doit contenir au moins une string non vide")
        return 1

    print("[OK] /predict — to_name=document_text, textarea JSON non vide")
    return 0


if __name__ == "__main__":
    sys.exit(main())
