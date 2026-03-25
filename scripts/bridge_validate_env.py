#!/usr/bin/env python3
"""
BRIDGE_FIX_01 — Valide les variables d'environnement requises pour l'ingestion OCR.

Usage:
  python scripts/bridge_validate_env.py
  python scripts/bridge_validate_env.py --strict

--strict : code de sortie 1 si Mistral ou Llama manque (bloque un run bridge cloud).
Sans --strict : affiche l'état de chaque clé ; code 0 (préparation / audit seul).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _load_dotenv_local() -> None:
    for name in (".env.local", ".env"):
        p = _PROJECT_ROOT / name
        if not p.is_file():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate OCR / bridge API keys.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if Mistral or Llama key is missing.",
    )
    parser.add_argument(
        "--no-dotenv",
        action="store_true",
        help="Do not load .env / .env.local from project root.",
    )
    args = parser.parse_args()
    if not args.no_dotenv:
        _load_dotenv_local()

    from src.core.api_keys import (  # noqa: WPS433
        APIKeyMissingError,
        get_llama_cloud_api_key,
        get_mistral_api_key,
    )

    results: list[tuple[str, bool, str]] = []

    def check_mistral() -> None:
        try:
            get_mistral_api_key()
            results.append(("MISTRAL_API_KEY", True, "OK"))
        except APIKeyMissingError as e:
            results.append(("MISTRAL_API_KEY", False, str(e)))

    def check_llama() -> None:
        try:
            get_llama_cloud_api_key()
            results.append(("LLAMADMS / LLAMA_CLOUD_API_KEY", True, "OK"))
        except APIKeyMissingError as e:
            results.append(("LLAMADMS / LLAMA_CLOUD_API_KEY", False, str(e)))

    check_mistral()
    check_llama()

    az_end = bool(os.environ.get("AZURE_FORM_RECOGNIZER_ENDPOINT", "").strip())
    az_key = bool(os.environ.get("AZURE_FORM_RECOGNIZER_KEY", "").strip())
    if az_end and az_key:
        results.append(("AZURE_FORM_RECOGNIZER_*", True, "OK (fallback MIME)"))
    else:
        results.append(
            (
                "AZURE_FORM_RECOGNIZER_*",
                False,
                "optional: enables Azure Read when MIME is not PDF/image",
            )
        )

    for name, ok, msg in results:
        status = "OK " if ok else "MISS"
        print(f"[{status}] {name}: {msg}")

    if args.strict:
        need = [r for r in results[:2] if not r[1]]
        if need:
            print(
                "\nStrict mode: set MISTRAL_API_KEY and at least one Llama key "
                "(LLAMADMS or LLAMA_CLOUD_API_KEY). See docs/freeze/BRIDGE_FIX_01_FREEZE.md.",
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
