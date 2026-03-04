# scripts/_probe_m9b.py  <- NE PAS COMMITTER
import psycopg
from psycopg.rows import dict_row

url = None
with open(".env") as f:
    for line in f:
        line = line.strip()
        if line.startswith("DATABASE_URL="):
            url = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

if url and url.startswith("postgresql+psycopg://"):
    url = url.replace("postgresql+psycopg://", "postgresql://", 1)

with psycopg.connect(url, row_factory=dict_row) as conn:
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS cnt FROM score_runs")
    print("0-G score_runs count =", cur.fetchone()["cnt"])

    cur.execute(
        "SELECT schemaname, tablename FROM pg_tables "
        "WHERE tablename IN ('corrections','suppliers','proposals','scoring_meta') "
        "ORDER BY schemaname, tablename"
    )
    rows = cur.fetchall()
    print("0-G extra tables:", rows if rows else "none found in any schema")

print("Done.")
