import os

import psycopg
from psycopg.rows import dict_row

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")

with psycopg.connect(url, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name='pipeline_runs'
            ORDER BY ordinal_position
        """
        )
        print("=== pipeline_runs colonnes ===")
        for r in cur.fetchall():
            print(r)

        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name='pipeline_runs'
              AND column_name='force_recompute'
        """
        )
        row = cur.fetchone()
        if row:
            print("STOP — force_recompute deja presente (fantome migration)")
        else:
            print("PASS — force_recompute absente (migration 034 saine)")

        for tbl in ["score_runs", "scoring_runs"]:
            cur.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema='public' AND table_name=%s
                ORDER BY ordinal_position
            """,
                (tbl,),
            )
            rows = cur.fetchall()
            print(f"\n=== {tbl} colonnes ===")
            if rows:
                for r in rows:
                    print(r)
            else:
                print("TABLE ABSENTE")
