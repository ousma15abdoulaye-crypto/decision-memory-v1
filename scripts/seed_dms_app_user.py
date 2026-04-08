#!/usr/bin/env python3
"""Crée un utilisateur DMS (users + user_tenants) — même logique que POST /auth/register.

À lancer depuis un environnement **Python** (pas une image Bun-only) :

  # Cible Railway (recommandé)
  set DMS_SEED_USER_EMAIL=...
  set DMS_SEED_USER_USERNAME=...
  set DMS_SEED_USER_PASSWORD=...
  python scripts/with_railway_env.py python scripts/seed_dms_app_user.py

  # Ou local : DATABASE_URL dans .env
  python scripts/seed_dms_app_user.py

Ne jamais committer email/mot de passe. Ne pas utiliser python3 dans un conteneur
où seul Bun/Node est installé (erreur « python3: not found »).

Optionnel : DMS_SEED_FULL_NAME, DMS_SEED_ROLE_ID (défaut 2).
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
    email = os.environ.get("DMS_SEED_USER_EMAIL", "").strip()
    username = os.environ.get("DMS_SEED_USER_USERNAME", "").strip()
    password = os.environ.get("DMS_SEED_USER_PASSWORD", "")
    full_name = os.environ.get("DMS_SEED_FULL_NAME", "").strip() or None
    role_id = int(os.environ.get("DMS_SEED_ROLE_ID", "2"))

    if not email or not username or not password:
        print(
            "Variables requises : DMS_SEED_USER_EMAIL, DMS_SEED_USER_USERNAME, "
            "DMS_SEED_USER_PASSWORD",
            file=sys.stderr,
        )
        return 1

    if not os.environ.get("DATABASE_URL"):
        print(
            "DATABASE_URL absent — utilisez scripts/with_railway_env.py ou un .env local.",
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
        "Utilisateur créé : "
        f"id={user.get('id')} email={user.get('email')} username={user.get('username')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
