import os
import psycopg
from psycopg.rows import dict_row

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(url, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type, column_default, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'cases'
            ORDER BY ordinal_position
        """)
        for r in cur.fetchall():
            print(r)
