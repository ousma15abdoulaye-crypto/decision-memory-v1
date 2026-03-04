import psycopg, os
from psycopg.rows import dict_row

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(url, autocommit=True) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('vendors', 'vendor_identities', 'market_signals')
            ORDER BY table_name
        """)
        tables = [r[0] for r in cur.fetchall()]
        print("Tables:", tables)

        cur.execute("SELECT version_num FROM alembic_version")
        ver = cur.fetchone()
        print("Alembic current:", ver)
