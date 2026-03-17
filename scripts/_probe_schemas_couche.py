"""Probe schemas couche* - CTO decision M10B."""
import os
import psycopg

db_url = os.environ.get("DATABASE_URL", "")
if not db_url:
    print("STOP - DATABASE_URL absente")
    exit(1)
# Normaliser pour psycopg (postgresql+psycopg:// -> postgresql://)
if "://" in db_url:
    scheme_part, rest = db_url.split("://", 1)
    base_scheme = scheme_part.split("+")[0]
    db_url = f"{base_scheme}://{rest}"
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

conn = psycopg.connect(db_url)
cur = conn.cursor()
cur.execute("SELECT nspname FROM pg_namespace WHERE nspname LIKE %s ORDER BY nspname", ("couche%",))
rows = cur.fetchall()
print("SCHEMAS couche*:", rows)
conn.close()
