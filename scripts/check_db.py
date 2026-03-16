"""Quick DB state check for M-EXTRACTION-CORRECTIONS."""
import os
from dotenv import load_dotenv
load_dotenv()
url = os.environ.get("DATABASE_URL", "")
if not url:
    print("DATABASE_URL not set")
    exit(1)
# Redact password for debug
safe_url = url.split("@")[-1] if "@" in url else url[:50]
print("DB (redacted):", safe_url)
import psycopg
conn = psycopg.connect(url.replace("postgresql+psycopg://", "postgresql://"), autocommit=True)
cur = conn.cursor()
cur.execute("SELECT version_num FROM alembic_version")
versions = cur.fetchall()
print("alembic_version:", [v[0] for v in versions])
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name='extraction_corrections'")
r = cur.fetchone()
print("extraction_corrections exists:", r is not None)
if r:
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='extraction_corrections' ORDER BY ordinal_position")
    for row in cur.fetchall():
        print(" ", row[0], row[1])
cur.execute("SELECT table_name FROM information_schema.views WHERE table_schema='public' AND table_name='structured_data_effective'")
print("structured_data_effective view exists:", cur.fetchone() is not None)
cur.execute("SELECT trigger_name FROM information_schema.triggers WHERE event_object_table='extraction_corrections'")
triggers = cur.fetchall()
print("Triggers:", [t[0] for t in triggers])
conn.close()
