"""Vérifier et restaurer les colonnes d'extractions."""
import os
import psycopg, psycopg.rows
from dotenv import load_dotenv
load_dotenv()
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(url, row_factory=psycopg.rows.dict_row, autocommit=True)
cur = conn.cursor()

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='extractions' ORDER BY ordinal_position")
cols = [r["column_name"] for r in cur.fetchall()]
print("extractions colonnes:", cols)

# Ajouter les colonnes manquantes de migrations 013/014
for col_sql in [
    "ALTER TABLE extractions ADD COLUMN IF NOT EXISTS document_id TEXT",
    "ALTER TABLE extractions ADD COLUMN IF NOT EXISTS raw_text TEXT",
    "ALTER TABLE extractions ADD COLUMN IF NOT EXISTS structured_data JSONB",
    "ALTER TABLE extractions ADD COLUMN IF NOT EXISTS extraction_method TEXT",
    "ALTER TABLE extractions ADD COLUMN IF NOT EXISTS confidence_score REAL",
    "ALTER TABLE extractions ADD COLUMN IF NOT EXISTS extracted_at TIMESTAMPTZ DEFAULT NOW()",
]:
    cur.execute(col_sql)
    print(f"  {col_sql[:50]} OK")

for nullable_col in ["artifact_id", "extraction_type"]:
    try:
        cur.execute(f"ALTER TABLE extractions ALTER COLUMN {nullable_col} DROP NOT NULL")
        print(f"  DROP NOT NULL {nullable_col} OK")
    except Exception as e:
        print(f"  DROP NOT NULL {nullable_col} ignore: {e}")

# Recréer la vue structured_data_effective
cur.execute("""
CREATE OR REPLACE VIEW structured_data_effective AS
SELECT DISTINCT ON (e.document_id)
    e.id AS extraction_id,
    e.document_id,
    COALESCE(ec.structured_data, e.structured_data) AS structured_data,
    COALESCE(ec.confidence_override, e.confidence_score) AS confidence_score,
    e.extraction_method,
    e.extracted_at,
    ec.corrected_at,
    ec.corrected_by,
    ec.correction_reason
FROM extractions e
LEFT JOIN LATERAL (
    SELECT * FROM extraction_corrections ec2
    WHERE ec2.extraction_id = e.id
    ORDER BY ec2.corrected_at DESC, ec2.id DESC
    LIMIT 1
) ec ON true
ORDER BY e.document_id, e.extracted_at DESC NULLS LAST, e.id
""")
print("VIEW structured_data_effective OK")

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='extractions' ORDER BY ordinal_position")
cols2 = [r["column_name"] for r in cur.fetchall()]
print("extractions colonnes apres:", cols2)
conn.close()
print("DONE")
