"""
Root pytest config. Set DATABASE_URL before any test imports src.db.

src.db creates the engine at import time (Constitution V2.1). Without DATABASE_URL,
any module that imports src.db (e.g. scoring engine) raises at collection time.
This conftest runs first so collection succeeds; same URL as CI for local runs.
"""

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:testpass@localhost:5432/dmstest",
)
