import psycopg, os
db = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(db) as conn:
    row = conn.execute("""
        SELECT pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conname = 'committee_events_event_type_check'
    """).fetchone()
    print(row[0] if row else "NOT FOUND")
