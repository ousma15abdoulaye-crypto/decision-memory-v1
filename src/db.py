"""src.db — Database access layer (Source of Truth).

Re-exports from backend.system.db so that scripts, migrations,
and CI tooling can use ``from src.db import Base, engine, ...``.
"""

from backend.system.db import (  # noqa: F401
    Base,
    engine,
    async_session_factory,
    get_db,
    init_db,
)

__all__ = ["Base", "engine", "async_session_factory", "get_db", "init_db"]
