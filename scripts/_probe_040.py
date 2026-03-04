import psycopg, os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
load_dotenv('.env.local')
url = os.environ['DATABASE_URL'].replace('postgresql+psycopg://', 'postgresql://')
with psycopg.connect(url) as conn:
    rows = conn.execute('SELECT * FROM alembic_version').fetchall()
    print('ALL alembic_version rows:')
    for r in rows:
        print(' -', r)
    print('COUNT:', len(rows))
