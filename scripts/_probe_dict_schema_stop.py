"""Probe STOP · Schéma dict_* et procurement_dict_* · Tech Lead mandat."""
from dotenv import load_dotenv
load_dotenv()
load_dotenv(".env.local")
import psycopg
import os
from psycopg.rows import dict_row

url = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
if not url:
    print("DATABASE_URL non definie")
    exit(1)

with psycopg.connect(url, row_factory=dict_row) as conn:
    tables_dict = [
        "dict_families",
        "dict_unit_conversions",
        "dict_units",
        "dictionary",
        "procurement_dict_aliases",
        "procurement_dict_families",
        "procurement_dict_items",
        "procurement_dict_unit_conversions",
        "procurement_dict_units",
    ]

    for table in tables_dict:
        print(f"=== {table} ===")
        try:
            cols = conn.execute(
                """
                SELECT table_schema, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY table_schema, ordinal_position
                """,
                (table,),
            ).fetchall()
            for c in cols:
                print(f"  {dict(c)}")

            schemas = conn.execute(
                "SELECT table_schema FROM information_schema.tables WHERE table_name = %s",
                (table,),
            ).fetchall()
            if schemas:
                schema = schemas[0]["table_schema"]
                count = conn.execute(
                    f'SELECT COUNT(*) AS n FROM "{schema}"."{table}"'
                ).fetchone()
            else:
                count = {"n": "N/A"}
            print(f"  Lignes : {count['n']}")
        except Exception as e:
            print(f"  ERREUR : {e}")

    print("=== VUES SUPPRIMEES (021) ===")
    for vname in ["dict_items", "dict_aliases"]:
        r = conn.execute(
            """
            SELECT table_type FROM information_schema.tables
            WHERE table_name = %s
            """,
            (vname,),
        ).fetchone()
        print(f"  {vname} : {r['table_type'] if r else 'ABSENT'}")

    print("=== MIGRATION 021 ===")
    r = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    print(f"  alembic current : {r['version_num']}")
