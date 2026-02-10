"""
Database initialization and metadata for DMS
Constitution DMS V2.1
"""

from sqlalchemy import MetaData, create_engine, text
import os

# Create metadata object for Couche B
metadata = MetaData()

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/dms.sqlite3")

# Create engine (psycopg for PostgreSQL, per Constitution V2.1)
if DATABASE_URL.startswith("sqlite"):
    # SQLite for local development
    engine = create_engine(DATABASE_URL, echo=False)
else:
    # PostgreSQL with psycopg driver
    engine = create_engine(DATABASE_URL, echo=False)

def init_db_schema():
    """Initialize database schema (create all tables)"""
    # Late import to avoid circular dependency with src/couche_b/__init__.py
    try:
        from src.couche_b import models as couche_b_models
        print("📦 Couche B models imported")
    except ImportError as e:
        print(f"⚠️  Couche B models not yet created: {e}")
    
    # Create all tables
    metadata.create_all(engine)
    print("✅ Database schemas initialized")

def init_db():
    """Legacy function - calls init_db_schema for compatibility"""
    init_db_schema()

if __name__ == "__main__":
    init_db_schema()
