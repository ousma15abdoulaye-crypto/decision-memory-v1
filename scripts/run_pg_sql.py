#!/usr/bin/env python3
"""Exécute une requête SQL PostgreSQL en ligne de commande (ops / pilotes BLOC4–BLOC6).

Lit ``RAILWAY_DATABASE_URL`` puis ``DATABASE_URL`` (ou ``--db-url``). Utilise
``scripts/dms_pg_connect.py`` (psycopg v3), aligné sur ``diagnose_railway_migrations.py``.

Usage ::
    python scripts/run_pg_sql.py -c "SELECT version();"
    python scripts/run_pg_sql.py --db-url "postgresql://..." -c "SELECT 1"

Variables :
    RAILWAY_DATABASE_URL, DATABASE_URL — fichier ``.env.railway.local`` chargé si présent.
"""

from __future__ import annotations

import argparse
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


def _print_rows(cur) -> None:
    if cur.description is None:
        return
    cols = [d.name for d in cur.description]
    print(" | ".join(cols))
    print("-" * min(120, sum(max(8, len(c)) for c in cols) + 3 * len(cols)))
    for row in cur.fetchall():
        print(" | ".join("" if x is None else str(x) for x in row))


def main() -> int:
    parser = argparse.ArgumentParser(description="Exécuter du SQL PostgreSQL (CLI ops)")
    parser.add_argument(
        "-c",
        "--command",
        dest="sql",
        metavar="SQL",
        help="Une instruction SQL (guillemets PowerShell / bash)",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        metavar="PATH",
        help="Fichier contenant du SQL (UTF-8)",
    )
    parser.add_argument(
        "--db-url",
        dest="db_url",
        default=None,
        help="URL PostgreSQL (prime sur RAILWAY_DATABASE_URL / DATABASE_URL)",
    )
    args = parser.parse_args()

    if bool(args.sql) == bool(args.file):
        print(
            'STOP — fournir exactement l’un des arguments : -c "SQL" ou -f fichier.sql',
            file=sys.stderr,
        )
        return 2

    try:
        raw = get_raw_database_url(args.db_url)
    except ValueError as exc:
        print(f"ERREUR : {exc}", file=sys.stderr)
        return 1

    if args.file is not None:
        if not args.file.is_file():
            print(f"STOP — fichier introuvable : {args.file}", file=sys.stderr)
            return 2
        sql_text = args.file.read_text(encoding="utf-8")
    else:
        sql_text = (args.sql or "").strip()

    try:
        import psycopg
    except ImportError:
        print("ERREUR : psycopg requis (pip install psycopg[binary])", file=sys.stderr)
        return 1

    hint = safe_target_hint(raw)
    print(f"[run_pg_sql] Cible : {hint}", file=sys.stderr)

    kw = psycopg_connect_kwargs(raw)
    try:
        with psycopg.connect(**kw) as conn:
            with conn.cursor() as cur:
                cur.execute(sql_text)
                if cur.description:
                    _print_rows(cur)
                else:
                    rc = cur.rowcount
                    if rc is not None and rc >= 0:
                        print(f"(lignes affectées : {rc})")
            conn.commit()
    except Exception as exc:
        print(f"ERREUR SQL : {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
