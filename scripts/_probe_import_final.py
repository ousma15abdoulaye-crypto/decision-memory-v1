"""Probe post-import final — 2023 + 2024."""
import psycopg
import psycopg.rows

url = "postgresql://dms:dms123@localhost:5432/dms"
with psycopg.connect(url, row_factory=psycopg.rows.dict_row) as conn:
    for year in [2024, 2023]:
        r = conn.execute("""
            SELECT
                COUNT(*)                                        AS total,
                COUNT(zone_id)                                  AS zones_ok,
                COUNT(*) - COUNT(zone_id)                       AS zones_null,
                SUM(CASE WHEN review_required THEN 1 ELSE 0 END) AS review,
                COUNT(DISTINCT zone_id)                         AS zones_uniq,
                COUNT(DISTINCT source_id)                       AS sources
            FROM mercurials WHERE year = %s
        """, (year,)).fetchone()
        print(f"{year} ->", dict(r))

    total = conn.execute("SELECT COUNT(*) AS n FROM mercurials").fetchone()
    sources = conn.execute("SELECT COUNT(*) AS n FROM mercuriale_sources").fetchone()
    print(f"TOTAL GLOBAL  : {total['n']} lignes")
    print(f"TOTAL SOURCES : {sources['n']} fichiers")
