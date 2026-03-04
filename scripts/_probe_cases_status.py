# NE PAS COMMITTER
import psycopg
from psycopg.rows import dict_row

with open(".env") as f:
    for line in f:
        line = line.strip()
        if line.startswith("DATABASE_URL="):
            url = line.split("=", 1)[1].strip().strip('"').strip("'")
            break
url = url.replace("postgresql+psycopg://", "postgresql://")

with psycopg.connect(url, row_factory=dict_row) as conn:
    cur = conn.cursor()
    cur.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name='cases'
        ORDER BY ordinal_position
    """)
    for r in cur.fetchall():
        print(r)
