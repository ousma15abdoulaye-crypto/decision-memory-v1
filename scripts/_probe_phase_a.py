"""Probe Phase A - état taxo_proposals_v2."""
import os

import psycopg

url = os.environ.get("DATABASE_URL", "")
if not url:
    print("DATABASE_URL manquante")
    exit(1)

with psycopg.connect(url) as c:
    r = c.execute(
        "SELECT status, COUNT(*) FROM couche_b.taxo_proposals_v2 "
        "WHERE taxo_version='2.0.0' GROUP BY status"
    ).fetchall()
    print("Status:", r)
    t = c.execute(
        "SELECT COUNT(*) FROM couche_b.taxo_proposals_v2 WHERE taxo_version='2.0.0'"
    ).fetchone()[0]
    print("Total:", t)
    g = c.execute("""
SELECT COUNT(*) AS total,
  COUNT(*) FILTER (WHERE status='flagged') AS flagged,
  ROUND(COUNT(*) FILTER (WHERE status='flagged')*100.0/NULLIF(COUNT(*),0),1) AS flagged_pct,
  COUNT(*) FILTER (WHERE subfamily_id='DIVERS_NON_CLASSE') AS residuel,
  ROUND(COUNT(*) FILTER (WHERE subfamily_id='DIVERS_NON_CLASSE')*100.0/NULLIF(COUNT(*),0),1) AS residuel_pct
FROM couche_b.taxo_proposals_v2 WHERE taxo_version='2.0.0'
""").fetchone()
    print("Gates total/flagged/flagged_pct/residuel/residuel_pct:", g)
