"""Restaure la DB de 014 vers 036.

Nettoie les tables avec données orphelines (FK vers extractions/documents
qui ont été recréées vides), puis lance alembic upgrade head.
"""
import os
import subprocess
from pathlib import Path

import psycopg
import psycopg.rows
from dotenv import load_dotenv

load_dotenv()
PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(url, row_factory=psycopg.rows.dict_row, autocommit=True)
cur = conn.cursor()

# Vérifier alembic_version
cur.execute("SELECT version_num FROM alembic_version")
row = cur.fetchone()
print(f"alembic_version actuelle : {row}")

# Nettoyer tables orphelines (TRUNCATE bypass les triggers BEFORE DELETE/UPDATE)
for table in ["extraction_corrections", "extraction_jobs", "extraction_errors"]:
    try:
        cur.execute(f"TRUNCATE TABLE {table}")
        print(f"TRUNCATE {table} OK")
    except Exception as e:
        print(f"TRUNCATE {table} ignoré : {e}")

conn.close()

# Upgrade 015 → 036
print("Lancement alembic upgrade head...")
result = subprocess.run(
    ["alembic", "upgrade", "head"],
    cwd=PROJECT_ROOT,
    capture_output=True,
    text=True,
)
print("STDOUT:", result.stdout[-500:] if result.stdout else "")
print("STDERR:", result.stderr[-500:] if result.stderr else "")
print("Return code:", result.returncode)
