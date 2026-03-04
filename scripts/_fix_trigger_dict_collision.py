"""Applique le trigger append-only sur dict_collision_log (omis par bug EXECUTE)."""
import os
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()
url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")

with psycopg.connect(url, row_factory=dict_row, autocommit=True) as conn:
    with conn.cursor() as cur:
        cur.execute("DROP TRIGGER IF EXISTS trg_dict_collision_log_append_only ON dict_collision_log;")
        cur.execute("""
            CREATE TRIGGER trg_dict_collision_log_append_only
              BEFORE DELETE OR UPDATE ON dict_collision_log
              FOR EACH ROW
              EXECUTE FUNCTION fn_reject_mutation();
        """)
        cur.execute("""
            SELECT trigger_name FROM information_schema.triggers
            WHERE event_object_table = 'dict_collision_log'
        """)
        rows = cur.fetchall()
        print("Triggers sur dict_collision_log:", [r["trigger_name"] for r in rows])
        print("OK")
