#!/usr/bin/env python3
"""Charge `.env.railway.local` puis exécute une commande avec ces variables d'environnement.

Contourne le blocage PowerShell « exécution de scripts désactivée » (pas besoin de .ps1).

Usage (à la racine du dépôt) :
    python scripts/with_railway_env.py python scripts/diagnose_railway_migrations.py
    python scripts/with_railway_env.py python scripts/apply_railway_migrations_safe.py --apply
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = REPO_ROOT / ".env.railway.local"


def main() -> int:
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("Installez python-dotenv : pip install python-dotenv", file=sys.stderr)
        return 1

    if not ENV_FILE.is_file():
        print(
            f"Fichier absent : {ENV_FILE}\n"
            "Copiez .env.railway.local.example vers .env.railway.local et remplissez les secrets.",
            file=sys.stderr,
        )
        return 1

    load_dotenv(ENV_FILE, override=True)

    # ETL et src/db/core.get_connection() lisent DATABASE_URL ; les scripts
    # Alembic utilisent RAILWAY_DATABASE_URL via dms_pg_connect. Aligner ici
    # pour que les commandes lancées via ce fichier ciblent Railway.
    _rail = os.environ.get("RAILWAY_DATABASE_URL", "").strip()
    if _rail:
        os.environ["DATABASE_URL"] = _rail

    if len(sys.argv) < 2:
        print(
            "Usage: python scripts/with_railway_env.py <commande> [args...]\n"
            "Exemple: python scripts/with_railway_env.py python scripts/diagnose_railway_migrations.py",
            file=sys.stderr,
        )
        return 1

    cmd = sys.argv[1:]
    return subprocess.call(cmd, env=os.environ.copy(), cwd=str(REPO_ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
