"""P3.2 R2 — Execute all F2 NULL probes sequentially"""
import os
import sys
import psycopg2
from pathlib import Path

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

print("=" * 70)
print("P3.2 ACTION R2 — F2 NULL PROBES (CORPUS ACTIF)")
print("=" * 70)
print()

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# ===========================================================================
# F2a — criterion_category IS NULL
# ===========================================================================
print("=" * 70)
print("F2a — criterion_category IS NULL")
print("=" * 70)

query_f2a = """
SELECT pw.reference_code, COUNT(*) as count_null
FROM dao_criteria dc
JOIN process_workspaces pw ON dc.workspace_id = pw.id
WHERE pw.status != 'cancelled'
  AND dc.criterion_category IS NULL
GROUP BY pw.reference_code
ORDER BY pw.reference_code;
"""

cur.execute(query_f2a)
rows_f2a = cur.fetchall()

if not rows_f2a:
    print("\n✅ AUCUN NULL criterion_category sur corpus actif")
    total_f2a = 0
else:
    print(f"\n⚠️  {len(rows_f2a)} workspace(s) avec criterion_category IS NULL:\n")
    print("reference_code                 | count")
    print("-" * 45)
    total_f2a = 0
    for ref_code, count in rows_f2a:
        print(f"{ref_code:30s} | {count:5d}")
        total_f2a += count
    print("-" * 45)
    print(f"TOTAL                          | {total_f2a:5d}")

print()

# ===========================================================================
# F2b — ponderation IS NULL
# ===========================================================================
print("=" * 70)
print("F2b — ponderation IS NULL")
print("=" * 70)

query_f2b = """
SELECT pw.reference_code, COUNT(*) as count_null
FROM dao_criteria dc
JOIN process_workspaces pw ON dc.workspace_id = pw.id
WHERE pw.status != 'cancelled'
  AND dc.ponderation IS NULL
GROUP BY pw.reference_code
ORDER BY pw.reference_code;
"""

cur.execute(query_f2b)
rows_f2b = cur.fetchall()

if not rows_f2b:
    print("\n✅ AUCUN NULL ponderation sur corpus actif")
    total_f2b = 0
else:
    print(f"\n⚠️  {len(rows_f2b)} workspace(s) avec ponderation IS NULL:\n")
    print("reference_code                 | count")
    print("-" * 45)
    total_f2b = 0
    for ref_code, count in rows_f2b:
        print(f"{ref_code:30s} | {count:5d}")
        total_f2b += count
    print("-" * 45)
    print(f"TOTAL                          | {total_f2b:5d}")

print()

# ===========================================================================
# F2c — m16_scoring_mode IS NULL
# ===========================================================================
print("=" * 70)
print("F2c — m16_scoring_mode IS NULL")
print("=" * 70)

query_f2c = """
SELECT pw.reference_code, COUNT(*) as count_null
FROM dao_criteria dc
JOIN process_workspaces pw ON dc.workspace_id = pw.id
WHERE pw.status != 'cancelled'
  AND dc.m16_scoring_mode IS NULL
GROUP BY pw.reference_code
ORDER BY pw.reference_code;
"""

cur.execute(query_f2c)
rows_f2c = cur.fetchall()

if not rows_f2c:
    print("\n✅ AUCUN NULL m16_scoring_mode sur corpus actif")
    total_f2c = 0
else:
    print(f"\n⚠️  {len(rows_f2c)} workspace(s) avec m16_scoring_mode IS NULL:\n")
    print("reference_code                 | count")
    print("-" * 45)
    total_f2c = 0
    for ref_code, count in rows_f2c:
        print(f"{ref_code:30s} | {count:5d}")
        total_f2c += count
    print("-" * 45)
    print(f"TOTAL                          | {total_f2c:5d}")

print()

# ===========================================================================
# SUMMARY
# ===========================================================================
print("=" * 70)
print("SUMMARY — Distribution NULLs par workspace actif")
print("=" * 70)

query_summary = """
SELECT
    pw.reference_code,
    COUNT(*) as total_criteria,
    COUNT(CASE WHEN dc.criterion_category IS NULL THEN 1 END) as null_category,
    COUNT(CASE WHEN dc.ponderation IS NULL THEN 1 END) as null_ponderation,
    COUNT(CASE WHEN dc.m16_scoring_mode IS NULL THEN 1 END) as null_scoring_mode
FROM dao_criteria dc
JOIN process_workspaces pw ON dc.workspace_id = pw.id
WHERE pw.status != 'cancelled'
GROUP BY pw.reference_code
ORDER BY pw.reference_code;
"""

cur.execute(query_summary)
rows_summary = cur.fetchall()

print()
print("reference_code                 | total | null_cat | null_pond | null_score")
print("-" * 80)
for ref_code, total, null_cat, null_pond, null_score in rows_summary:
    print(f"{ref_code:30s} | {total:5d} | {null_cat:8d} | {null_pond:9d} | {null_score:10d}")

print()

cur.close()
conn.close()

print("=" * 70)
print("F2 PROBES COMPLETE")
print("=" * 70)
print()
print(f"F2a (criterion_category IS NULL): {total_f2a} rows")
print(f"F2b (ponderation IS NULL):        {total_f2b} rows")
print(f"F2c (m16_scoring_mode IS NULL):   {total_f2c} rows")
print()

# Verdict
if total_f2b == 0:
    print("✅ F2b PASS: ponderation complete on active corpus")
else:
    print(f"⚠️  F2b WARNING: {total_f2b} rows with ponderation IS NULL")
    print("   These rows will be excluded from weight_within_family backfill")
