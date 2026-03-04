import os, psycopg
from psycopg.rows import dict_row
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(url, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT version_num FROM alembic_version")
        print("alembic_version:", cur.fetchone())
        cur.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='vendors') AS v")
        print("vendors exists:", cur.fetchone()["v"])
        cur.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='vendor_identities') AS v")
        print("vendor_identities exists:", cur.fetchone()["v"])
