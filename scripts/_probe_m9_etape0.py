#!/usr/bin/env python3
"""Probe ETAPE 0 M9 — autocommit."""
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

def q(sql, params=None):
    try:
        cur.execute(sql, params)
        return cur.fetchall()
    except Exception as e:
        print(f"  ERR: {e}")
        return []

# 1. market_signals
print("\n=== 1. market_signals colonnes ===")
for r in q("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name='market_signals' ORDER BY ordinal_position"):
    print(f"  {r['column_name']:35} {r['data_type']:20} null={r['is_nullable']}")

print("\n=== 1b. market_signals contraintes ===")
for r in q("SELECT constraint_name, constraint_type FROM information_schema.table_constraints WHERE table_name='market_signals'"):
    print(f"  {r['constraint_name']:50} {r['constraint_type']}")

n = q("SELECT COUNT(*) AS n FROM public.market_signals")
print(f"  Lignes: {n[0]['n'] if n else 'ERR'}")

# 2. mercurials
print("\n=== 2. mercurials colonnes ===")
merc_cols = q("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='mercurials' ORDER BY ordinal_position")
for r in merc_cols:
    print(f"  {r['column_name']:30} {r['data_type']}")

# Stats mercurials avec les vraies colonnes
print("\n=== 2b. mercurials stats ===")
col_names = [c['column_name'] for c in merc_cols]
# Chercher colonne date
date_col = next((c for c in col_names if c in ['date_recorded','date','date_surveyed','survey_date','month','year','created_at','periode']), None)
prix_col = next((c for c in col_names if c in ['price_avg','unit_price','price_xof','price','prix','montant']), None)
item_col = next((c for c in col_names if c in ['item_id','procurement_item_id']), None)
zone_col = next((c for c in col_names if c in ['zone_id','region_id']), None)
print(f"  date_col={date_col} prix_col={prix_col} item_col={item_col} zone_col={zone_col}")

for r in q(f"""SELECT COUNT(*) AS total, COUNT(DISTINCT {item_col}) AS items, COUNT(DISTINCT {zone_col}) AS zones FROM mercurials"""):
    print(f"  total={r['total']} items={r['items']} zones={r['zones']}")

if date_col == 'year':
    for r in q("SELECT MIN(year) AS debut, MAX(year) AS fin FROM mercurials"):
        print(f"  annees: {r['debut']} -> {r['fin']}")
elif date_col:
    for r in q(f"SELECT MIN({date_col}) AS debut, MAX({date_col}) AS fin FROM mercurials"):
        print(f"  periode: {r['debut']} -> {r['fin']}")

# 3. decision_history
print("\n=== 3. decision_history colonnes ===")
dh_cols = q("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='decision_history' ORDER BY ordinal_position")
for r in dh_cols:
    print(f"  {r['column_name']:30} {r['data_type']}")

print("\n=== 3b. decision_history stats ===")
dh_col_names = [c['column_name'] for c in dh_cols]
status_col = next((c for c in dh_col_names if 'status' in c.lower()), None)
if status_col:
    for r in q(f"SELECT {status_col}, COUNT(*) AS n FROM decision_history GROUP BY {status_col} ORDER BY n DESC LIMIT 10"):
        print(f"  {status_col}={r[status_col]} n={r['n']}")
n = q("SELECT COUNT(*) AS n FROM decision_history")
print(f"  Total: {n[0]['n'] if n else 'ERR'}")

# 4. INSTAT tables
print("\n=== 4. Tables INSTAT candidates ===")
instat = q("""
    SELECT table_name, table_schema FROM information_schema.tables
    WHERE table_name ILIKE '%instat%' OR table_name ILIKE '%imc%'
       OR table_name ILIKE '%indice%' OR table_name ILIKE '%materiaux%'
       OR table_name ILIKE '%construction%'
    ORDER BY table_name
""")
if instat:
    for r in instat:
        print(f"  {r['table_schema']}.{r['table_name']}")
        cols_i = q(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{r['table_name']}' AND table_schema='{r['table_schema']}' ORDER BY ordinal_position")
        for c in cols_i:
            print(f"    {c['column_name']:30} {c['data_type']}")
        n2 = q(f"SELECT COUNT(*) AS n FROM {r['table_schema']}.{r['table_name']}")
        print(f"    Lignes: {n2[0]['n'] if n2 else 'ERR'}")
else:
    print("  AUCUNE table INSTAT")

# 5. price_check
print("\n=== 5. price_check tables ===")
for r in q("SELECT table_name FROM information_schema.tables WHERE table_name IN ('price_signals','price_checks')"):
    print(f"  {r['table_name']}")

# 6. seasonal_patterns
print("\n=== 6. seasonal_patterns ===")
for r in q("SELECT COUNT(*) AS t, COUNT(DISTINCT zone_id) AS z, COUNT(DISTINCT taxo_l3) AS c FROM seasonal_patterns"):
    print(f"  total={r['t']} zones={r['z']} categories={r['c']}")

# 7. geo_price_corridors
print("\n=== 7. geo_price_corridors ===")
for r in q("SELECT COUNT(*) AS n FROM geo_price_corridors"):
    print(f"  Corridors: {r['n']}")

# 8. src market dir
import subprocess
result = subprocess.run(["git","ls-files","src/couche_a/market/"], capture_output=True, text=True)
print(f"\n=== 8. src/couche_a/market/ ===")
print(result.stdout if result.stdout.strip() else "  ABSENT")

# 9. price_check engine
print("\n=== 9. price_check engine (head) ===")
ep = Path("src/couche_a/price_check/engine.py")
if ep.exists():
    for l in ep.read_text(encoding="utf-8").splitlines()[:25]:
        print(f"  {l}")
else:
    print("  ABSENT")

# 10. cases.id type (pour reference)
print("\n=== 10. FK targets confirmees ===")
for r in q("""
    SELECT table_name, column_name, data_type
    FROM information_schema.columns
    WHERE (table_name='market_signals' AND column_name='item_id')
       OR (table_name='mercurials' AND column_name='item_id')
    ORDER BY table_name
"""):
    print(f"  {r['table_name']}.{r['column_name']} = {r['data_type']}")

conn.close()
print("\n=== PROBE ETAPE 0 COMPLETE ===")
