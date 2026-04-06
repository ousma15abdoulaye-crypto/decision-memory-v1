#!/usr/bin/env python3
"""Sondes lecture seule sur PostgreSQL Railway / prod (aucune écriture).

Exécute uniquement des ``SELECT`` codés en dur — pour validation CTO avant migration
ou après déploiement.

Usage ::
    python scripts/preflight_cto_railway_readonly.py
    python scripts/preflight_cto_railway_readonly.py --db-url "postgresql://..."

Variables : ``RAILWAY_DATABASE_URL`` ou ``DATABASE_URL`` (voir ``.env.railway.local``).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(REPO_ROOT / ".env.local", override=True)
    load_dotenv(REPO_ROOT / ".env.railway.local", override=True)
except ImportError:
    pass

from dms_pg_connect import (  # noqa: E402
    get_raw_database_url,
    psycopg_connect_kwargs,
    safe_target_hint,
)

_QUERIES: list[tuple[str, str]] = [
    (
        "identité",
        "SELECT current_database() AS db, current_user AS role, version() AS pg_version",
    ),
    (
        "alembic",
        "SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 8",
    ),
    (
        "tables_core",
        """
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name IN (
            'process_workspaces', 'committee_sessions', 'vendors', 'supplier_bundles'
          )
        ORDER BY table_name
        """,
    ),
]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Sondes SQL read-only Railway/Postgres"
    )
    parser.add_argument(
        "--db-url",
        default=None,
        help="URL PostgreSQL (sinon RAILWAY_DATABASE_URL / DATABASE_URL)",
    )
    args = parser.parse_args()

    try:
        raw = get_raw_database_url(args.db_url)
    except ValueError as exc:
        print(f"ERREUR : {exc}", file=sys.stderr)
        return 1

    try:
        import psycopg
    except ImportError:
        print("ERREUR : psycopg requis", file=sys.stderr)
        return 1

    print(f"[preflight] Cible : {safe_target_hint(raw)}", file=sys.stderr)
    kw = psycopg_connect_kwargs(raw)

    try:
        with psycopg.connect(**kw) as conn:
            with conn.cursor() as cur:
                for label, sql in _QUERIES:
                    print(f"\n--- {label} ---")
                    cur.execute(sql.strip())
                    if cur.description:
                        cols = [d.name for d in cur.description]
                        print(" | ".join(cols))
                        for row in cur.fetchall():
                            print(" | ".join("" if x is None else str(x) for x in row))
    except Exception as exc:
        print(f"ERREUR : {exc}", file=sys.stderr)
        return 1

    print("\n[preflight] Terminé (lecture seule).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
