"""DEPRECATED — This file is superseded by alembic/env.py.

The canonical migration source of truth is now the top-level alembic/ directory.
See alembic.ini (script_location = alembic) and alembic/env.py which imports
from src.db instead of backend.system.db.

This file is kept only as an archive reference. Do not use.
"""

raise RuntimeError(
    "DEPRECATED: backend/migrations/env.py is no longer the migration source. "
    "Use the top-level alembic/ directory instead (alembic.ini → script_location = alembic)."
)
