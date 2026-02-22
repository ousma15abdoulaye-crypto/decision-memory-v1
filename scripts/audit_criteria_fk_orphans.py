"""
Audit Phase 1 -- M-CRITERIA-FK
Read-only. Aucune ecriture DB.
"""
import os, sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("DATABASE_URL", os.environ.get("DM_DATABASE_URL",""))
DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")

AUDIT_QUERIES = {
    "col_info": """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'criteria'
          AND column_name  = 'canonical_item_id';
    """,
    "couche_b_tables": """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'couche_b'
          AND table_name IN ('items', 'procurement_dict_items')
        ORDER BY table_name;
    """,
    "couche_b_items_count": """
        SELECT COUNT(*) AS cnt FROM couche_b.items;
    """,
    "couche_b_dict_count": """
        SELECT COUNT(*) AS cnt FROM couche_b.procurement_dict_items;
    """,
    "orphans": """
        SELECT c.id AS criteria_id, c.canonical_item_id
        FROM public.criteria c
        LEFT JOIN couche_b.items i
               ON c.canonical_item_id::text = i.id::text
        WHERE c.canonical_item_id IS NOT NULL
          AND i.id IS NULL
        LIMIT 50;
    """,
}

def safe_query(cur, label, sql):
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        print(f"\n[{label}]")
        for r in rows:
            print(" ", dict(r))
        return rows
    except Exception as e:
        print(f"\n[{label}] ERREUR : {e}")
        return None

def main():
    print(f"[PROBE] DB : {DATABASE_URL[:50]}...")
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:

            col_rows    = safe_query(cur, "criteria.canonical_item_id", AUDIT_QUERIES["col_info"])
            tables      = safe_query(cur, "couche_b tables detectees", AUDIT_QUERIES["couche_b_tables"])

            # Comptes selon tables existantes
            for t in (tables or []):
                if t["table_name"] == "items":
                    safe_query(cur, "couche_b.items COUNT", AUDIT_QUERIES["couche_b_items_count"])
                if t["table_name"] == "procurement_dict_items":
                    safe_query(cur, "couche_b.procurement_dict_items COUNT", AUDIT_QUERIES["couche_b_dict_count"])

            orphan_rows = safe_query(cur, "ORPHELINS", AUDIT_QUERIES["orphans"])

    # Verdict
    print("\n== VERDICT ==")
    if not col_rows:
        print("[STOP] canonical_item_id ABSENTE dans public.criteria")
        sys.exit(2)
    if not tables:
        print("[STOP] Aucune table Couche B trouvee (items ni procurement_dict_items)")
        sys.exit(2)
    if orphan_rows:
        print(f"[STOP] {len(orphan_rows)} orphelin(s) detecte(s). Corriger avant FK.")
        sys.exit(1)
    table_names = [t["table_name"] for t in tables]
    print(f"[OK] 0 orphelin. Tables Couche B detectees : {table_names}")
    print("[OK] GO pour migration 023.")
    sys.exit(0)

if __name__ == "__main__":
    main()
