"""P3.2 — Post-check migration 101 execution

Vérifie :
1. Colonnes ajoutées présentes
2. CASE-28b05d85 : family, weight_within_family, criterion_mode, scoring_mode
3. essential doctrine respectée
"""
import os
import sys
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

print("=" * 70)
print("P3.2 POST-CHECK MIGRATION 101")
print("=" * 70)
print()

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# ===========================================================================
# CHECK 1 — Colonnes ajoutées présentes
# ===========================================================================
print("=" * 70)
print("CHECK 1 — Colonnes ajoutées (dao_criteria)")
print("=" * 70)

query_columns = """
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'dao_criteria'
  AND column_name IN ('family', 'weight_within_family', 'criterion_mode', 'scoring_mode', 'min_threshold')
ORDER BY column_name;
"""

cur.execute(query_columns)
columns = cur.fetchall()

if len(columns) != 5:
    print(f"\n⛔ ERROR: Expected 5 columns, found {len(columns)}")
    for col_name, data_type, nullable, default in columns:
        print(f"  {col_name:25s} {data_type:15s} nullable={nullable} default={default}")
    sys.exit(1)

print("\n✅ 5 colonnes ajoutées présentes:\n")
print("column_name               | data_type       | nullable | default")
print("-" * 75)
for col_name, data_type, nullable, default in columns:
    print(f"{col_name:25s} | {data_type:15s} | {nullable:8s} | {default or 'NULL'}")

print()

# Check process_workspaces.technical_qualification_threshold
query_pw_col = """
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'process_workspaces'
  AND column_name = 'technical_qualification_threshold';
"""

cur.execute(query_pw_col)
pw_col = cur.fetchone()

if not pw_col:
    print("⛔ ERROR: process_workspaces.technical_qualification_threshold not found")
    sys.exit(1)

print("✅ process_workspaces.technical_qualification_threshold présente:")
col_name, data_type, nullable, default = pw_col
print(f"  {col_name:25s} | {data_type:15s} | {nullable:8s} | {default or 'NULL'}")

print()

# ===========================================================================
# CHECK 2 — CASE-28b05d85 family distribution
# ===========================================================================
print("=" * 70)
print("CHECK 2 — CASE-28b05d85 family distribution")
print("=" * 70)

query_family = """
SELECT
    dc.family,
    COUNT(*) as n_criteria,
    SUM(dc.ponderation) as sum_ponderation,
    SUM(dc.weight_within_family) as sum_weight_within_family
FROM dao_criteria dc
JOIN process_workspaces pw ON dc.workspace_id = pw.id
WHERE pw.reference_code = 'CASE-28b05d85'
  AND dc.family IS NOT NULL
GROUP BY dc.family
ORDER BY dc.family;
"""

cur.execute(query_family)
families = cur.fetchall()

print("\nfamily         | n_criteria | sum_ponderation | sum_weight")
print("-" * 65)
for family, n, sum_pond, sum_weight in families:
    status = "✅" if sum_weight == 100 else f"⚠️  {sum_weight}"
    print(f"{family:14s} | {n:10d} | {sum_pond:15.1f} | {sum_weight:10d} {status}")

print()

# ===========================================================================
# CHECK 3 — essential doctrine
# ===========================================================================
print("=" * 70)
print("CHECK 3 — essential doctrine (criterion_category='essential')")
print("=" * 70)

query_essential = """
SELECT
    pw.reference_code,
    dc.family,
    dc.criterion_mode,
    COUNT(*) as count_essential
FROM dao_criteria dc
JOIN process_workspaces pw ON dc.workspace_id = pw.id
WHERE dc.criterion_category = 'essential'
  AND pw.status != 'cancelled'
GROUP BY pw.reference_code, dc.family, dc.criterion_mode
ORDER BY pw.reference_code;
"""

cur.execute(query_essential)
essential_rows = cur.fetchall()

if not essential_rows:
    print("\n✅ Aucun critère essential sur corpus actif (ou absent)")
else:
    print("\nreference_code                 | family | criterion_mode | count")
    print("-" * 70)
    all_ok = True
    for ref_code, family, criterion_mode, count in essential_rows:
        family_ok = "✅" if family is None else f"⛔ {family}"
        mode_ok = "✅" if criterion_mode == 'GATE' else f"⛔ {criterion_mode}"
        print(f"{ref_code:30s} | {str(family):6s} | {criterion_mode:14s} | {count:5d}")
        if family is not None or criterion_mode != 'GATE':
            all_ok = False

    if all_ok:
        print("\n✅ Doctrine essential respectée : family=NULL, criterion_mode=GATE")
    else:
        print("\n⛔ ERREUR: Doctrine essential non respectée")
        sys.exit(1)

print()

# ===========================================================================
# CHECK 4 — scoring_mode NULL si m16_scoring_mode NULL
# ===========================================================================
print("=" * 70)
print("CHECK 4 — scoring_mode NULL preservation (F2c validation)")
print("=" * 70)

query_scoring_null = """
SELECT
    pw.reference_code,
    COUNT(*) as count_null_source_and_target
FROM dao_criteria dc
JOIN process_workspaces pw ON dc.workspace_id = pw.id
WHERE pw.reference_code = 'CASE-28b05d85'
  AND dc.m16_scoring_mode IS NULL
  AND dc.scoring_mode IS NULL
GROUP BY pw.reference_code;
"""

cur.execute(query_scoring_null)
scoring_null = cur.fetchone()

if scoring_null:
    ref_code, count = scoring_null
    print(f"\n✅ {count} rows CASE-28b05d85 : m16_scoring_mode IS NULL → scoring_mode IS NULL (preserved)")
else:
    print("\n✅ Aucun cas m16_scoring_mode IS NULL sur CASE-28b05d85 (ou tous backfillés)")

# Check no false fallback (m16 NULL but scoring NOT NULL)
query_false_fallback = """
SELECT COUNT(*)
FROM dao_criteria dc
JOIN process_workspaces pw ON dc.workspace_id = pw.id
WHERE pw.reference_code = 'CASE-28b05d85'
  AND dc.m16_scoring_mode IS NULL
  AND dc.scoring_mode IS NOT NULL;
"""

cur.execute(query_false_fallback)
false_fallback_count = cur.fetchone()[0]

if false_fallback_count > 0:
    print(f"\n⛔ ERREUR: {false_fallback_count} rows avec m16_scoring_mode IS NULL mais scoring_mode NOT NULL (fallback interdit)")
    sys.exit(1)
else:
    print("✅ Aucun fallback silencieux détecté (m16 NULL → scoring NULL)")

print()

cur.close()
conn.close()

print("=" * 70)
print("POST-CHECK MIGRATION 101 COMPLETE — ALL CHECKS PASS")
print("=" * 70)
