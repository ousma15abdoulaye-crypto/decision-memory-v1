#!/usr/bin/env python3
"""Audit M12 — Structure mercurials, sources, zones, items, tables IMC."""
import os
import psycopg
from psycopg.rows import dict_row

url = (
    os.environ.get("RAILWAY_DATABASE_URL", "")
    or os.environ.get("DATABASE_URL", "")
)
if "postgresql+psycopg://" in url:
    url = url.replace("postgresql+psycopg://", "postgresql://")
if not url:
    print("DATABASE_URL / RAILWAY_DATABASE_URL absente")
    raise SystemExit(1)

conn = psycopg.connect(url, row_factory=dict_row)

print("=" * 70)
print("=== REQUÊTE 1 — COLONNES TABLE MERCURIALS ===")
print("=" * 70)
cols = conn.execute(
    """
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'mercurials'
    AND table_schema = 'public'
    ORDER BY ordinal_position
"""
).fetchall()
for c in cols:
    print(f"  {c['column_name']:30} {c['data_type']:20} null={c['is_nullable']}")

print()
print("=" * 70)
print("=== REQUÊTE 2 — SOURCES (via mercuriale_sources) ET PLAGE ===")
print("=" * 70)
try:
    rows = conn.execute(
        """
        SELECT s.source_type, COUNT(*) as n
        FROM mercurials m
        JOIN mercuriale_sources s ON s.id = m.source_id
        GROUP BY s.source_type
        ORDER BY n DESC
    """
    ).fetchall()
    for r in rows:
        print(f"  {str(r['source_type']):40} {r['n']} lignes")
except Exception as e:
    conn.rollback()
    print(f"  Erreur sources : {e}")

print()
print("=== PLAGE TEMPORELLE (year) ===")
try:
    r = conn.execute(
        """
        SELECT
            MIN(year) as year_min,
            MAX(year) as year_max,
            COUNT(DISTINCT year) as n_years,
            COUNT(*) as total
        FROM mercurials
    """
    ).fetchone()
    print(f"  year_min   : {r['year_min']}")
    print(f"  year_max   : {r['year_max']}")
    print(f"  n_years    : {r['n_years']}")
    print(f"  total      : {r['total']}")
except Exception as e:
    conn.rollback()
    print(f"  Erreur : {e}")

print()
print("=" * 70)
print("=== REQUÊTE 3 — ZONES ET ITEMS ===")
print("=" * 70)
try:
    rows = conn.execute(
        """
        SELECT zone_id, COUNT(*) as n
        FROM mercurials
        GROUP BY zone_id
        ORDER BY n DESC
        LIMIT 20
    """
    ).fetchall()
    for r in rows:
        print(f"  {str(r['zone_id']):30} {r['n']} lignes")
except Exception as e:
    conn.rollback()
    print(f"  Erreur zone_id : {e}")

print()
print("=== ECHANTILLON ITEMS (50 premiers) ===")
try:
    rows = conn.execute(
        """
        SELECT DISTINCT item_canonical
        FROM mercurials
        ORDER BY item_canonical
        LIMIT 50
    """
    ).fetchall()
    for r in rows:
        print(f"  {r['item_canonical']}")
except Exception as e:
    conn.rollback()
    print(f"  Erreur : {e}")

print()
print("=== ITEMS IMC (ciment, sable, gravier, bois, fer, etc.) ===")
try:
    rows = conn.execute(
        """
        SELECT item_canonical, COUNT(*) as n
        FROM mercurials
        WHERE LOWER(item_canonical) ~ 'ciment|sable|gravier|bois|fer|beton|moellon|chevron|carreau|granito|plomberie|electricite|peinture|menuiserie|rond|cpj|agregat'
        GROUP BY item_canonical
        ORDER BY n DESC
        LIMIT 30
    """
    ).fetchall()
    if rows:
        for r in rows:
            print(f"  {r['item_canonical']:45} {r['n']} lignes")
    else:
        print("  Aucun item IMC trouvé dans mercurials")
except Exception as e:
    conn.rollback()
    print(f"  Erreur : {e}")

print()
print("=" * 70)
print("=== REQUÊTE 4 — TABLES prix/price/imc/index/mercurial/survey ===")
print("=" * 70)
rows = conn.execute(
    """
    SELECT table_schema, table_name,
           pg_size_pretty(
               pg_total_relation_size(
                   quote_ident(table_schema)||chr(46)||
                   quote_ident(table_name)
               )
           ) as taille
    FROM information_schema.tables
    WHERE table_type = 'BASE TABLE'
    AND (
        table_name ILIKE '%prix%'
        OR table_name ILIKE '%price%'
        OR table_name ILIKE '%imc%'
        OR table_name ILIKE '%index%'
        OR table_name ILIKE '%indice%'
        OR table_name ILIKE '%materiau%'
        OR table_name ILIKE '%construction%'
        OR table_name ILIKE '%mercurial%'
        OR table_name ILIKE '%survey%'
    )
    ORDER BY table_schema, table_name
"""
).fetchall()
for r in rows:
    print(f"  {r['table_schema']:15} {r['table_name']:35} {r['taille']}")

print()
print("=== TABLES PUBLIC (taille décroissante) ===")
rows = conn.execute(
    """
    SELECT relname as table_name,
           pg_size_pretty(pg_total_relation_size(c.oid)) as taille
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
    AND c.relkind = 'r'
    ORDER BY pg_total_relation_size(c.oid) DESC
    LIMIT 30
"""
).fetchall()
for r in rows:
    print(f"  {r['table_name']:40} {r['taille']}")

print()
print("=" * 70)
print("=== REQUÊTE A — CONTENU imc_entries ===")
print("=" * 70)
print("=== COLONNES imc_entries ===")
try:
    cols = conn.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'imc_entries'
        AND table_schema = 'public'
        ORDER BY ordinal_position
    """
    ).fetchall()
    for c in cols:
        print(f"  {c['column_name']:30} {c['data_type']}")
except Exception as e:
    conn.rollback()
    print(f"  Erreur : {e}")

print()
print("=== PLAGE TEMPORELLE imc_entries ===")
try:
    r = conn.execute(
        """
        SELECT
            MIN(period_year)        as year_min,
            MAX(period_year)        as year_max,
            MIN(period_month)       as month_min,
            MAX(period_month)       as month_max,
            COUNT(*)         as total,
            COUNT(DISTINCT period_year||chr(45)||LPAD(period_month::text,2,chr(48)))
                             as n_periods
        FROM imc_entries
    """
    ).fetchone()
    for k, v in r.items():
        print(f"  {k:20} : {v}")
except Exception as e:
    conn.rollback()
    try:
        r = conn.execute(
            """
            SELECT MIN(period_year) as year_min,
                   MAX(period_year) as year_max,
                   COUNT(*) as total
            FROM imc_entries
        """
        ).fetchone()
        for k, v in r.items():
            print(f"  {k:20} : {v}")
    except Exception as e2:
        conn.rollback()
        print(f"  Erreur : {e2}")

print()
print("=== ECHANTILLON imc_entries (10 lignes) ===")
try:
    rows = conn.execute("SELECT * FROM imc_entries LIMIT 10").fetchall()
    for r in rows:
        print(f"  {dict(r)}")
except Exception as e:
    conn.rollback()
    print(f"  Erreur : {e}")

print()
print("=" * 70)
print("=== REQUÊTE B — imc_sources et mercuriale_sources ===")
print("=" * 70)
print("=== imc_sources (20 lignes) ===")
try:
    rows = conn.execute("SELECT * FROM imc_sources LIMIT 20").fetchall()
    for r in rows:
        print(f"  {dict(r)}")
except Exception as e:
    conn.rollback()
    print(f"  Erreur : {e}")

print()
print("=== mercuriale_sources (20 lignes) ===")
try:
    rows = conn.execute("SELECT * FROM mercuriale_sources LIMIT 20").fetchall()
    for r in rows:
        print(f"  {dict(r)}")
except Exception as e:
    conn.rollback()
    print(f"  Erreur : {e}")

print()
print("=" * 70)
print("=== REQUÊTE C — Recouvrement imc_entries vs mercurials ===")
print("=" * 70)
print("=== CATÉGORIES imc_entries NON dans mercurials (category_raw) ===")
try:
    rows = conn.execute(
        """
        SELECT DISTINCT ie.category_raw, COUNT(*) as n
        FROM imc_entries ie
        LEFT JOIN mercurials m
               ON LOWER(TRIM(m.item_canonical))
                = LOWER(TRIM(ie.category_raw))
        WHERE m.item_canonical IS NULL
        GROUP BY ie.category_raw
        ORDER BY n DESC
        LIMIT 20
    """
    ).fetchall()
    if rows:
        print(f"  {len(rows)} catégories IMC absentes de mercurials (top 20) :")
        for r in rows:
            print(f"    {str(r['category_raw'])[:50]:50} {r['n']} lignes")
    else:
        print("  Toutes les catégories IMC sont dans mercurials")
except Exception as e:
    conn.rollback()
    print(f"  Erreur : {e}")

print()
print("=== ANNÉES dans imc_entries (period_year) ===")
try:
    rows = conn.execute(
        """
        SELECT period_year as year, COUNT(*) as n
        FROM imc_entries
        GROUP BY period_year
        ORDER BY period_year
    """
    ).fetchall()
    for r in rows:
        print(f"  {r['year']} : {r['n']} lignes")
except Exception as e:
    conn.rollback()
    print(f"  Erreur (pas de colonne period_year) : {e}")

conn.close()
print()
print("=== FIN AUDIT ===")
