#!/usr/bin/env python3
"""Probe mapping mercurials item_canonical -> dict_items."""
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

db = os.environ.get("RAILWAY_DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
if not db:
    raise SystemExit("RAILWAY_DATABASE_URL absente")
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
            print("  " + " | ".join(f"{k}={str(v)[:70]}" for k, v in r.items()))
        return rows
    except Exception as e:
        print(f"  ERR: {e}")
        return []

# 1. Sample mercurials
q("1. mercurials sample", """
    SELECT item_canonical, item_code, zone_id, year, price_avg
    FROM mercurials LIMIT 5
""")

# 2. Similarity item_canonical -> label_fr
q("2. Similarity > 0.6 (top 20)", """
    SELECT m.item_canonical,
           di.item_id,
           di.label_fr,
           ROUND(similarity(
               LOWER(m.item_canonical),
               LOWER(di.label_fr)
           )::numeric, 3) AS score
    FROM mercurials m
    JOIN couche_b.procurement_dict_items di
      ON similarity(LOWER(m.item_canonical), LOWER(di.label_fr)) > 0.6
    WHERE m.item_canonical IS NOT NULL
    ORDER BY score DESC
    LIMIT 20
""")

# 3. Stats item_canonical
q("3. item_canonical stats", """
    SELECT COUNT(DISTINCT item_canonical) AS distincts,
           COUNT(*) AS total
    FROM mercurials
""")

# 4. Tables mercuriale*
q("4. Tables mercuriale*", """
    SELECT table_name FROM information_schema.tables
    WHERE table_name ILIKE '%mercurial%'
    ORDER BY table_name
""")

# 5. mercuriale_sources
q("5. mercuriale_sources sample", """
    SELECT * FROM mercuriale_sources LIMIT 3
""")

# Bonus: % similarity > seuils
q("6. Distribution scores similarity", """
    SELECT
        SUM(CASE WHEN score >= 0.90 THEN 1 ELSE 0 END) AS n_90,
        SUM(CASE WHEN score >= 0.85 THEN 1 ELSE 0 END) AS n_85,
        SUM(CASE WHEN score >= 0.75 THEN 1 ELSE 0 END) AS n_75,
        SUM(CASE WHEN score >= 0.60 THEN 1 ELSE 0 END) AS n_60,
        COUNT(*) AS total_matches
    FROM (
        SELECT DISTINCT ON (m.item_canonical)
               similarity(LOWER(m.item_canonical), LOWER(di.label_fr)) AS score
        FROM mercurials m
        JOIN couche_b.procurement_dict_items di
          ON similarity(LOWER(m.item_canonical), LOWER(di.label_fr)) > 0.5
        WHERE m.item_canonical IS NOT NULL
        ORDER BY m.item_canonical, score DESC
    ) sub
""")

# Bonus: combien d'item_canonical uniques matchent > 0.85
q("7. item_canonical uniques matchant > 0.85", """
    SELECT COUNT(DISTINCT item_canonical) AS canonical_matches_85
    FROM (
        SELECT DISTINCT ON (m.item_canonical)
               m.item_canonical,
               di.item_id,
               similarity(LOWER(m.item_canonical), LOWER(di.label_fr)) AS score
        FROM mercurials m
        JOIN couche_b.procurement_dict_items di
          ON similarity(LOWER(m.item_canonical), LOWER(di.label_fr)) > 0.85
        WHERE m.item_canonical IS NOT NULL
        ORDER BY m.item_canonical, score DESC
    ) sub
""")

# Top mappings > 0.85 (premiers 30)
q("8. Top mappings > 0.85 (30 premiers)", """
    SELECT DISTINCT ON (m.item_canonical)
           m.item_canonical,
           di.item_id,
           di.label_fr,
           ROUND(similarity(LOWER(m.item_canonical), LOWER(di.label_fr))::numeric, 3) AS score,
           di.taxo_l1, di.taxo_l3
    FROM mercurials m
    JOIN couche_b.procurement_dict_items di
      ON similarity(LOWER(m.item_canonical), LOWER(di.label_fr)) > 0.85
    WHERE m.item_canonical IS NOT NULL
    ORDER BY m.item_canonical, score DESC
    LIMIT 30
""")

conn.close()
print("\n=== PROBE MAPPING COMPLETE ===")
