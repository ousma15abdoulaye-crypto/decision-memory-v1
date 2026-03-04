# scripts/_probe_cases_cols.py  <- NE PAS COMMITTER
import os
import psycopg
from psycopg.rows import dict_row

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")

with psycopg.connect(url, row_factory=dict_row) as conn:
    with conn.cursor() as cur:

        # Toutes les colonnes de public.cases
        cur.execute("""
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'cases'
            ORDER BY ordinal_position
        """)
        cols = cur.fetchall()

        print("=== COLONNES CASES (contrat case_factory) ===")
        for c in cols:
            not_null = c["is_nullable"] == "NO"
            has_default = c["column_default"] is not None
            flag = ""
            if not_null and not has_default:
                flag = "  <== NOT NULL SANS DEFAULT"
            print(
                f"  {c['column_name']:30s} | {c['data_type']:20s} | nullable={c['is_nullable']} | default={c['column_default']}{flag}"
            )

        print()
        # Resume des colonnes critiques
        critical = [c for c in cols if c["is_nullable"] == "NO" and c["column_default"] is None]
        print(f"Colonnes NOT NULL sans default ({len(critical)}) :")
        for c in critical:
            print(f"  -> {c['column_name']} ({c['data_type']})")
