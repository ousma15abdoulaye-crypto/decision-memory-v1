"""
ÉTAPE 1 — Probe users.id type (POINT-1 validation Tech Lead).
Confirme si approved_by doit être INTEGER ou UUID.

Usage :
    $env:DATABASE_URL = "<Railway>"
    python scripts/probe_users_id_type.py
"""
from __future__ import annotations

import os
import sys

import psycopg
from psycopg.rows import dict_row


def get_db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        sys.exit("❌ DATABASE_URL manquante")
    if url.startswith("postgresql+psycopg://"):
        url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def main() -> None:
    print("=" * 60)
    print("ÉTAPE 1 — PROBE users.id TYPE")
    print("=" * 60)

    with psycopg.connect(get_db_url(), row_factory=dict_row) as conn:
        r = conn.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name   = 'users'
              AND column_name  = 'id'
        """).fetchone()

    if not r:
        print("  Table users ou colonne id introuvable")
        sys.exit(1)

    print(f"  column_name : {r['column_name']}")
    print(f"  data_type   : {r['data_type']}")
    print()
    if r["data_type"] == "uuid":
        print("  → approved_by doit être UUID REFERENCES users(id)")
        print("  → Adapter migration M7.4 si actuellement INTEGER")
    else:
        print("  → approved_by INTEGER correct (aligné schéma actuel)")
    print("=" * 60)


if __name__ == "__main__":
    main()
