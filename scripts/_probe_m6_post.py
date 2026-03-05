"""Probe post-M6 · counts + canonical_slug + vues + index + unaccent."""
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
    print("=== COUNTS ===")
    for q, label in [
        ("SELECT COUNT(*) AS n FROM couche_b.procurement_dict_items", "items"),
        ("SELECT COUNT(*) AS n FROM couche_b.procurement_dict_aliases", "aliases"),
        ("SELECT COUNT(*) AS n FROM couche_b.dict_proposals", "proposals"),
    ]:
        r = conn.execute(q).fetchone()
        print(f"  {label} : {r['n']}")

    print("=== CANONICAL_SLUG (echantillon) ===")
    rows = conn.execute(
        """
        SELECT item_id, canonical_slug, confidence_score,
               human_validated
        FROM couche_b.procurement_dict_items
        LIMIT 5
        """
    ).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("=== VUES PUBLIC ===")
    for v in ["dict_items", "dict_aliases", "dict_families", "dict_units"]:
        r = conn.execute(
            """
            SELECT table_type FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = %s
            """,
            (v,),
        ).fetchone()
        print(f"  {v} : {r['table_type'] if r else 'ABSENT'}")

    print("=== INDEX TRGM ===")
    rows = conn.execute(
        """
        SELECT schemaname, indexname FROM pg_indexes
        WHERE indexname LIKE '%trgm%'
           OR indexname LIKE '%dict%'
        ORDER BY schemaname, indexname
        """
    ).fetchall()
    for r in rows:
        print(" ", dict(r))

    print("=== UNACCENT ===")
    r = conn.execute("SELECT unaccent('Ségou') AS test").fetchone()
    print(f"  unaccent test : {r['test']}")
