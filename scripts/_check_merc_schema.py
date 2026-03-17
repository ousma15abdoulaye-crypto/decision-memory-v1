import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except: pass
import psycopg
db = os.environ.get("RAILWAY_DATABASE_URL","").replace("postgresql+psycopg://","postgresql://")
with psycopg.connect(db, autocommit=True) as c:
    cur = c.cursor()
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='mercurials' AND column_name IN ('item_id','item_canonical') ORDER BY 1")
    print("mercurials:", cur.fetchall())
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='mercurials_item_map' AND column_name IN ('item_canonical','dict_item_id') ORDER BY 1")
    print("mercurials_item_map:", cur.fetchall())
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='mercurials' AND column_name LIKE '%item%' ORDER BY 1")
    print("mercurials item columns:", cur.fetchall())
