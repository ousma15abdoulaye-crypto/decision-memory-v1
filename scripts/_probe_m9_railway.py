#!/usr/bin/env python3
"""
Probe Railway DB — lecture seule.
Utilise RAILWAY_DATABASE_URL (pas DATABASE_URL).
Aucune migration, aucune écriture.
"""
import os
from pathlib import Path
import urllib.parse
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local")
except ImportError:
    pass
import psycopg
from psycopg.rows import dict_row

# Lecture seule via RAILWAY_DATABASE_URL
db = os.environ.get("RAILWAY_DATABASE_URL", "")
if not db:
    raise SystemExit("RAILWAY_DATABASE_URL absente dans .env")
db = db.replace("postgresql+psycopg://", "postgresql://")
_parsed = urllib.parse.urlparse(db)
_host_port = f"{_parsed.hostname}:{_parsed.port}" if _parsed.port else _parsed.hostname
_safe_url = f"{_parsed.scheme}://{_host_port}{_parsed.path}"
print(f"Connexion Railway : {_safe_url}")

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
            print("  " + " | ".join(f"{k}={str(v)[:60]}" for k, v in r.items()))
        return rows
    except Exception as e:
        print(f"  ERR: {e}")
        return []

# 1. mercurials une vraie ligne complète
q("1. mercurials LIMIT 3 (toutes colonnes)", "SELECT * FROM mercurials LIMIT 3")

# 2. colonnes mercurials avec stats nullité
q("2. mercurials colonnes", """
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'mercurials'
    ORDER BY ordinal_position
""")

q("2b. mercurials nullité item_id zone_id", """
    SELECT
        COUNT(*) AS total,
        COUNT(item_id) AS item_id_non_null,
        COUNT(zone_id) AS zone_id_non_null,
        COUNT(price_avg) AS price_avg_non_null,
        MIN(year) AS year_min,
        MAX(year) AS year_max
    FROM mercurials
""")

# 3. imc_entries Railway
q("3. imc_entries LIMIT 3", "SELECT * FROM imc_entries LIMIT 3")

# 4. market_surveys Railway
q("4. market_surveys count + sample", "SELECT COUNT(*) AS n FROM market_surveys")
q("4b. market_surveys LIMIT 3", "SELECT * FROM market_surveys LIMIT 3")

# 5. decision_history Railway
q("5. decision_history existe ?", """
    SELECT COUNT(*) AS n FROM information_schema.tables
    WHERE table_name = 'decision_history'
""")
q("5b. decision_history count", "SELECT COUNT(*) AS n FROM decision_history")

# 6. market_signals Railway
q("6. market_signals colonnes", """
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'market_signals'
    ORDER BY ordinal_position
""")
q("6b. market_signals count + sample", "SELECT COUNT(*) AS n FROM market_signals")
q("6c. market_signals LIMIT 3", "SELECT * FROM market_signals LIMIT 3")

# 7. mercurials sample WHERE zone_id non null
q("7. mercurials avec zone + item non null", """
    SELECT * FROM mercurials
    WHERE zone_id IS NOT NULL
    LIMIT 5
""")

# 8. Inventaire complet tables Railway
q("8. Tables Railway (toutes schemas)", """
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_schema IN ('public','couche_b','raw','staging','ingest')
    ORDER BY table_schema, table_name
""")

# 9. market_signals_v2 déjà présente ?
q("9. market_signals_v2 présente ?", """
    SELECT COUNT(*) AS n FROM information_schema.tables
    WHERE table_name = 'market_signals_v2'
""")

# 10. alembic_version Railway
q("10. alembic_version Railway", "SELECT * FROM alembic_version")

conn.close()
print("\n=== PROBE RAILWAY COMPLETE ===")
