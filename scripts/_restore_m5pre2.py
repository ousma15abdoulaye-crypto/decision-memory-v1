import psycopg, os
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(url, autocommit=True) as conn:
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE vendor_identities RENAME TO vendors")
        print("OK: vendor_identities renamed to vendors")
