"""Probe post-import 2024."""
import psycopg
import psycopg.rows

url = "postgresql://dms:dms123@localhost:5432/dms"
with psycopg.connect(url, row_factory=psycopg.rows.dict_row) as conn:
    r = conn.execute("""
        SELECT
            COUNT(*)                                  AS total_lignes,
            COUNT(zone_id)                            AS zones_resolues,
            COUNT(*) - COUNT(zone_id)                 AS zones_nulles,
            SUM(CASE WHEN review_required THEN 1 ELSE 0 END) AS review_requis,
            COUNT(DISTINCT zone_id)                   AS zones_distinctes
        FROM mercurials
        WHERE year = 2024
    """).fetchone()
    print("2024 lignes :", dict(r))

    r2 = conn.execute(
        "SELECT COUNT(*) AS cnt FROM mercuriale_sources WHERE year = 2024"
    ).fetchone()
    print("Sources 2024:", r2["cnt"])
