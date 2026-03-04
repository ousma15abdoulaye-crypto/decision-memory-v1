import psycopg, os
from psycopg.rows import dict_row

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(url, autocommit=True) as conn:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT version_num FROM alembic_version")
        print("Alembic:", cur.fetchone())

        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='public' AND table_name IN ('vendors','vendor_identities')
        """)
        print("Tables:", [r["table_name"] for r in cur.fetchall()])

        cur.execute("""
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_schema='public' AND table_name IN ('vendors','vendor_identities')
            ORDER BY constraint_name
        """)
        print("Constraints:", [(r["constraint_name"], r["constraint_type"]) for r in cur.fetchall()])

        cur.execute("""
            SELECT indexname FROM pg_indexes
            WHERE schemaname='public' AND tablename IN ('vendors','vendor_identities')
            ORDER BY indexname
        """)
        print("Indexes:", [r["indexname"] for r in cur.fetchall()])
