"""Applique fn_workspace_sealed_final v2 (sealed -> closed autorisé) sur la DB cible — une instruction."""

from __future__ import annotations

import sys
from pathlib import Path

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


def main() -> None:
    raw = get_raw_database_url(None)
    with psycopg.connect(**psycopg_connect_kwargs(raw)) as conn:
        conn.execute(SQL)
    print("OK: fn_workspace_sealed_final v2 applied")


if __name__ == "__main__":
    main()
