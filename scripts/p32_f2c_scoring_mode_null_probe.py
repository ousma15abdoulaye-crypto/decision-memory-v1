"""P3.2 F2c — m16_scoring_mode IS NULL probe"""
import os
import psycopg2

DATABASE_URL = os.environ["DATABASE_URL"]

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

query = """
SELECT pw.reference_code, COUNT(*)
FROM dao_criteria dc
JOIN process_workspaces pw ON dc.workspace_id = pw.id
WHERE pw.status != 'cancelled'
  AND dc.m16_scoring_mode IS NULL
GROUP BY pw.reference_code
ORDER BY pw.reference_code;
"""

print("=" * 60)
print("F2c — m16_scoring_mode IS NULL (corpus actif)")
print("=" * 60)

cur.execute(query)
rows = cur.fetchall()

if not rows:
    print("\n✅ AUCUN NULL m16_scoring_mode sur corpus actif")
else:
    print(f"\n⚠️  {len(rows)} workspace(s) avec m16_scoring_mode IS NULL:")
    print("\nreference_code | count")
    print("-" * 40)
    for ref_code, count in rows:
        print(f"{ref_code:30s} | {count:5d}")

cur.close()
conn.close()
