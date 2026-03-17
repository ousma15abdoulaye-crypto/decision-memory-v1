#!/usr/bin/env python3
"""
Probe Railway M10A — 6 vérifications post-M9 merge.
Source de vérité : Railway (pas local).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

db_url = os.environ.get("RAILWAY_DATABASE_URL", "")
if not db_url:
    print("ERROR: RAILWAY_DATABASE_URL absente")
    sys.exit(1)
db_url = db_url.replace("postgresql+psycopg://", "postgresql://", 1)

import psycopg

QUERIES = [
    ("1. Alembic Railway", "SELECT version_num FROM alembic_version;"),
    ("2. mercurials Railway", """
SELECT COUNT(*)        AS total,
       COUNT(item_id)  AS avec_item_id,
       ROUND(COUNT(item_id)::numeric / NULLIF(COUNT(*)::numeric, 0) * 100, 1) AS couverture_pct
FROM mercurials;
"""),
    ("3. mercurials_item_map Railway", "SELECT COUNT(*) AS mappings FROM mercurials_item_map;"),
    ("4. market_signals_v2 Railway", """
SELECT signal_quality, COUNT(*) AS n
FROM market_signals_v2
GROUP BY signal_quality;
"""),
    ("5. procurement_dict_items Railway", """
SELECT COUNT(*) AS items
FROM couche_b.procurement_dict_items
WHERE active = TRUE;
"""),
    ("6. Tables M9 présentes Railway", """
SELECT table_name
FROM information_schema.tables
WHERE table_name IN (
  'market_signals_v2',
  'signal_computation_log',
  'mercurials_item_map'
)
ORDER BY table_name;
"""),
]


def main():
    print("PROBE RAILWAY M10A — 6 OUTPUTS BRUTS")
    print("=" * 60)
    print(f"DB: {db_url.split('@')[-1][:50] if '@' in db_url else '...'}")

    with psycopg.connect(db_url, autocommit=True) as conn:
        for title, sql in QUERIES:
            print(f"\n--- {title} ---")
            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    rows = cur.fetchall()
                    cols = [d.name for d in cur.description] if cur.description else []
                    if cols:
                        print(" | ".join(cols))
                        print("-" * 40)
                    for r in rows:
                        print(" | ".join(str(x) for x in r))
                    if not rows:
                        print("(0 rows)")
            except Exception as e:
                print(f"ERREUR: {e}")

    print("\n" + "=" * 60)
    print("FIN PROBE RAILWAY")


if __name__ == "__main__":
    main()
