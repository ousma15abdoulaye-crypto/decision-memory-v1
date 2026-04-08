#!/usr/bin/env python3
"""Crée un compte admin (superuser) — users + user_tenants, même logique métier que l’API.

À exécuter uniquement dans un environnement **Python** (service FastAPI / Railway avec Python),
jamais dans un conteneur Bun-only (« python3: not found »).

  # Railway (service API)
  railway run --service=<api> python scripts/seed_admin.py

  # Local
  python scripts/seed_admin.py

Variables (obligatoires sauf mention) :
  ADMIN_EMAIL, ADMIN_PASSWORD
  ADMIN_USERNAME (défaut: admin)
  ADMIN_FULLNAME (défaut: DMS Admin)
  ADMIN_ROLE_ID (défaut: 1 — rôle admin en base)

Ne jamais committer de secrets. Voir scripts/README.md.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(REPO_ROOT / ".env.local")
except ImportError:
    pass

from fastapi import HTTPException  # noqa: E402

from src.api.auth_helpers import create_user  # noqa: E402


def main() -> int:
    email = os.environ.get("ADMIN_EMAIL", "").strip()
    username = os.environ.get("ADMIN_USERNAME", "admin").strip() or "admin"
    password = os.environ.get("ADMIN_PASSWORD", "")
    full_name = os.environ.get("ADMIN_FULLNAME", "DMS Admin").strip() or None
    role_id = int(os.environ.get("ADMIN_ROLE_ID", "1"))

    if not email or not password:
        print(
            "Variables requises : ADMIN_EMAIL, ADMIN_PASSWORD "
            "(optionnel : ADMIN_USERNAME, ADMIN_FULLNAME, ADMIN_ROLE_ID)",
            file=sys.stderr,
        )
        return 1

    if not os.environ.get("DATABASE_URL"):
        print(
            "DATABASE_URL absent — utilisez railway run sur le service API "
            "ou un .env local.",
            file=sys.stderr,
        )
        return 1

    try:
        user = create_user(
            email=email,
            username=username,
            password=password,
            role_id=role_id,
            full_name=full_name,
            is_superuser=True,
        )
    except HTTPException as exc:
        if exc.status_code == 409:
            print(
                f"Utilisateur déjà présent (email ou username) : {email} / {username}"
            )
            return 0
        print(f"Erreur HTTP {exc.status_code}: {exc.detail}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        return 1

    print(
        "Admin créé : "
        f"id={user.get('id')} email={user.get('email')} "
        f"username={user.get('username')} superuser=True"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
