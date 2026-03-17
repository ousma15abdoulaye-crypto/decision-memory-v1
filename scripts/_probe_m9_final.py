#!/usr/bin/env python3
"""Probe final M9 avant ETAPE 3."""
import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass
import psycopg
from psycopg.rows import dict_row

db = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
conn = psycopg.connect(db, row_factory=dict_row, autocommit=True)
cur = conn.cursor()

def q(label, sql):
    print(f"\n=== {label} ===")
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        if not rows:
            print("  (vide)")
        for r in rows:
            print("  " + " | ".join(f"{k}={v}" for k, v in r.items()))
    except Exception as e:
        print(f"  ERR: {e}")

q("1a. mercurials colonnes", """
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'mercurials'
    ORDER BY ordinal_position
""")

q("1b. mercurials sample", """
    SELECT item_id, zone_id, year,
           price_avg, price_min, price_max
    FROM mercurials LIMIT 3
""")

q("2. imc_entries sample recent", """
    SELECT category_raw, period_year,
           period_month, index_value
    FROM public.imc_entries
    ORDER BY period_year DESC, period_month DESC
    LIMIT 5
""")

q("3. procurement_dict_items sample", """
    SELECT item_id, label_fr, taxo_l3
    FROM couche_b.procurement_dict_items
    WHERE taxo_l3 IS NOT NULL
    LIMIT 3
""")

q("4. market_signals_v2 absente ?", """
    SELECT COUNT(*) AS n FROM information_schema.tables
    WHERE table_name = 'market_signals_v2'
""")

q("5. market_surveys sample", """
    SELECT item_id, zone_id, price_per_unit
    FROM public.market_surveys
    LIMIT 3
""")

q("6. mercurials item_id cast TEXT sample", """
    SELECT m.item_id::text AS item_id_text,
           di.item_id      AS dict_item_id,
           di.label_fr
    FROM mercurials m
    JOIN couche_b.procurement_dict_items di
      ON di.item_id = m.item_id::text
    LIMIT 3
""")

q("7. imc_entries categories distinctes", """
    SELECT DISTINCT category_raw,
           COUNT(*) AS n
    FROM public.imc_entries
    WHERE category_raw IS NOT NULL
    GROUP BY category_raw
    ORDER BY n DESC
    LIMIT 10
""")

conn.close()
print("\n=== PROBE FINAL COMPLETE ===")
