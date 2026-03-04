"""Force le retour à l'état 036_db_hardening.

- Vérifie que documents/offers/extractions/etc. existent (recreate via 002 si absent)
- Stamp alembic_version = 036_db_hardening
- Réapplique sha256, uq_documents_case_sha256, idx_documents_case_id si absents
"""
import os
import subprocess
from importlib import util
from pathlib import Path

import psycopg
import psycopg.rows
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(url, row_factory=psycopg.rows.dict_row, autocommit=True)
cur = conn.cursor()

# ── 1. Vérifier tables essentielles
for table in ["documents", "offers", "extractions"]:
    cur.execute(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
        f"WHERE table_name = '{table}' AND table_schema = 'public') AS ex"
    )
    row = cur.fetchone()
    if not row["ex"]:
        print(f"TABLE {table} ABSENTE — reconstruction via migration 002...")
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "alembic" / "versions" / "002_add_couche_a.py"
        )
        spec = util.spec_from_file_location("migration_002", str(migration_path))
        mod = util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        from sqlalchemy import create_engine
        engine_url = os.environ["DATABASE_URL"]
        if not engine_url.startswith("postgresql+psycopg"):
            engine_url = engine_url.replace("postgresql://", "postgresql+psycopg://", 1)
        eng = create_engine(engine_url)
        mod.upgrade(eng)
        print(f"  -> 002.upgrade() executed")
    else:
        print(f"TABLE {table} : present OK")

# ── 2. Stamp alembic_version = 036_db_hardening
cur.execute("DELETE FROM alembic_version")
cur.execute("INSERT INTO alembic_version (version_num) VALUES ('036_db_hardening')")
print("alembic_version = 036_db_hardening ✓")

# ── 3. Réappliquer sha256 + index + contrainte
cur.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS sha256 TEXT")
print("sha256 column OK")

cur.execute("CREATE INDEX IF NOT EXISTS idx_documents_case_id ON documents(case_id)")
print("idx_documents_case_id OK")

cur.execute("""
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'uq_documents_case_sha256'
      AND table_name = 'documents'
  ) THEN
    ALTER TABLE documents ADD CONSTRAINT uq_documents_case_sha256 UNIQUE (case_id, sha256);
  END IF;
END $$;
""")
print("uq_documents_case_sha256 OK")

# ── 4. Vérification finale
cur.execute("SELECT version_num FROM alembic_version")
print("alembic_version final :", cur.fetchone())

cur.execute(
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_name='documents' AND column_name='sha256'"
)
print("sha256 présent :", cur.fetchone())

conn.close()
print("DONE")
