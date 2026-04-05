"""Applique fn_workspace_sealed_final v2 (sealed -> closed autorisé) sur la DB cible — une instruction."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(REPO_ROOT / ".env.local", override=True)
    load_dotenv(REPO_ROOT / ".env.railway.local", override=True)
except ImportError:
    pass

import psycopg  # noqa: E402
from dms_pg_connect import get_raw_database_url, psycopg_connect_kwargs  # noqa: E402

SQL = """
CREATE OR REPLACE FUNCTION fn_workspace_sealed_final()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.status = 'sealed'
     AND NEW.status IS DISTINCT FROM 'closed' THEN
    RAISE EXCEPTION
      'Workspace % est sealed. Seule transition autorisée : closed.',
      OLD.id;
  END IF;
  IF OLD.status = 'closed' THEN
    RAISE EXCEPTION
      'Workspace % est closed. Aucune transition autorisée.',
      OLD.id;
  END IF;
  RETURN NEW;
END;
$$;
"""


def _connection_summary(raw_url: str) -> str:
    u = urlparse(
        raw_url.replace("postgresql+psycopg://", "postgresql://", 1)
        if raw_url.startswith("postgresql+psycopg://")
        else raw_url
    )
    host = u.hostname or "(inconnu)"
    path = (u.path or "").lstrip("/")
    dbname = path.split("/")[0] if path else "(inconnu)"
    return f"host={host} dbname={dbname}"


def main() -> int:
    p = argparse.ArgumentParser(
        description="Applique fn_workspace_sealed_final v2 sur la base pointée par DATABASE_URL."
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Obligatoire pour exécuter le DDL (garde-fou contre exécution accidentelle).",
    )
    args = p.parse_args()

    raw = get_raw_database_url(None)
    print(f"Cible: {_connection_summary(raw)}", flush=True)
    if not args.apply:
        print(
            "Dry-run : aucune modification. Pour appliquer : "
            "python scripts/bloc4_apply_workspace_trigger_v2.py --apply",
            file=sys.stderr,
        )
        return 0

    with psycopg.connect(**psycopg_connect_kwargs(raw)) as conn:
        conn.execute(SQL)
    print("OK: fn_workspace_sealed_final v2 applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
