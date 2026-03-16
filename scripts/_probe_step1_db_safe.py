#!/usr/bin/env python3
"""
STEP 1 — Afficher infos SAFE (host, dbname, port, alembic_version).
Zéro exposition credentials.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass

import psycopg
from psycopg.rows import dict_row


def _safe_url(url: str) -> dict:
    """Extrait host, dbname, port sans credentials."""
    u = urlparse(url.replace("postgresql+psycopg://", "postgresql://"))
    return {
        "host": u.hostname or "?",
        "dbname": u.path.lstrip("/") if u.path else "?",
        "port": u.port or 5432,
    }


def _probe(url: str, label: str) -> None:
    url_clean = url.replace("postgresql+psycopg://", "postgresql://")
    safe = _safe_url(url_clean)
    print(f"\n--- {label} ---")
    print(f"  host   : {safe['host']}")
    print(f"  dbname : {safe['dbname']}")
    print(f"  port   : {safe['port']}")
    try:
        with psycopg.connect(url_clean, row_factory=dict_row, connect_timeout=5) as conn:
            r = conn.execute("SELECT version_num FROM alembic_version").fetchone()
            print(f"  alembic_version : {r['version_num']}")
    except Exception as e:
        print(f"  alembic_version : ERROR {e}")


def main():
    local = os.environ.get("DATABASE_URL", "")
    prod = os.environ.get("DATABASE_URL_PROD") or os.environ.get("PROD_DATABASE_URL") or os.environ.get("RAILWAY_DATABASE_URL", "")

    print("=" * 60)
    print("STEP 1 — DB SAFE INFO")
    print("=" * 60)

    if local:
        _probe(local, "LOCAL (DATABASE_URL)")
    else:
        print("\n--- LOCAL ---")
        print("  DATABASE_URL manquante")

    if prod:
        _probe(prod, "RAILWAY PROD (DATABASE_URL_PROD/PROD/RAILWAY)")
    else:
        print("\n--- RAILWAY PROD ---")
        print("  DATABASE_URL_PROD / PROD_DATABASE_URL / RAILWAY_DATABASE_URL manquante")
        print("  STOP : definir une de ces variables pour sonder prod")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
