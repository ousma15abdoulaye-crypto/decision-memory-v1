"""Appliquer la contrainte UNIQUE uq_documents_case_sha256 directement en DB."""
import os

import psycopg
import psycopg.rows
from dotenv import load_dotenv

load_dotenv()
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(url, row_factory=psycopg.rows.dict_row, autocommit=True)
cur = conn.cursor()

cur.execute("""
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'uq_documents_case_sha256'
      AND table_name = 'documents'
  ) THEN
    ALTER TABLE documents
      ADD CONSTRAINT uq_documents_case_sha256
      UNIQUE (case_id, sha256);
  END IF;
END $$;
""")
print("DO block OK")

cur.execute(
    "SELECT 1 FROM information_schema.table_constraints "
    "WHERE constraint_name='uq_documents_case_sha256' AND table_name='documents'"
)
row = cur.fetchone()
print("Contrainte uq_documents_case_sha256:", row)

conn.close()
print("DONE")
