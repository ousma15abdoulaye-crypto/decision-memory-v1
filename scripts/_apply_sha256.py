"""ÉTAPE C — Réappliquer documents.sha256 et idx_documents_case_id directement en DB."""
import os

import psycopg
import psycopg.rows
from dotenv import load_dotenv

load_dotenv()
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(url, row_factory=psycopg.rows.dict_row, autocommit=True)
cur = conn.cursor()

# État avant
cur.execute(
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_name='documents' ORDER BY ordinal_position"
)
cols = [r["column_name"] for r in cur.fetchall()]
print("COLONNES documents avant:", cols)

# Réappliquer sha256
cur.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS sha256 TEXT;")
print("ALTER sha256 OK")

# Réappliquer index
cur.execute("CREATE INDEX IF NOT EXISTS idx_documents_case_id ON documents(case_id);")
print("CREATE INDEX idx_documents_case_id OK")

# Vérifier sha256
cur.execute(
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_name='documents' AND column_name='sha256'"
)
row = cur.fetchone()
print("SHA256 présent:", row)

# Vérifier index
cur.execute(
    "SELECT indexname FROM pg_indexes "
    "WHERE tablename='documents' AND indexname='idx_documents_case_id'"
)
idx = cur.fetchone()
print("IDX idx_documents_case_id:", idx)

conn.close()
print("DONE")
