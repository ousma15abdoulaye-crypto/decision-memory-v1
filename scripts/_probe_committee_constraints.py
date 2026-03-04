import psycopg, os
db = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(db) as conn:
    rows = conn.execute("""
        SELECT conname, pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conrelid = 'committee_events'::regclass
          AND contype  = 'c'
        ORDER BY conname
    """).fetchall()
    for name, defn in rows:
        print(f"NAME : {name}")
        print(f"DEF  : {defn}")
        print()
