"""
Database initialization and metadata for DMS
Constitution DMS V2.1
"""

from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
import os

# Create metadata object for Couche B
metadata = MetaData()

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/dms.sqlite3")

# Create engines
if DATABASE_URL.startswith("sqlite"):
    # SQLite for local development
    engine = create_engine(DATABASE_URL, echo=False)
    async_engine = None  # SQLite async support is limited
else:
    # PostgreSQL for production
    # Convert postgresql:// to postgresql+asyncpg://
    async_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    async_engine = create_async_engine(async_url, echo=False)
    engine = create_engine(DATABASE_URL, echo=False)

def init_db():
    """Initialize all schemas: Couche A + Couche B"""
    # Late import to avoid circular dependency with src/couche_b/__init__.py
    try:
        from src.couche_b import models as couche_b_models
        print("📦 Couche B models imported")
    except ImportError as e:
        print(f"⚠️  Couche B models not yet created: {e}")
    
    # Create all tables
    metadata.create_all(engine)
    print("✅ Database schemas initialized")

if __name__ == "__main__":
    init_db()
