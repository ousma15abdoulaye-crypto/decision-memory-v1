#!/usr/bin/env python3
"""
Smoke test for PostgreSQL connection (Constitution V2.1)
Validates real Postgres connection using src.db
"""

import sys
from pathlib import Path

# Add repo root to path for 'import src' to work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
from sqlalchemy import text

def main():
    """Run smoke test - validate real PostgreSQL connection"""
    print("=" * 60)
    print("SMOKE TEST: PostgreSQL Connection (Constitution V2.1)")
    print("=" * 60)
    print()
    
    # Requirement: DATABASE_URL must be set
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        print("   Constitution V2.1 requires DATABASE_URL for smoke test")
        sys.exit(1)
    
    print(f"📊 DATABASE_URL: {database_url.split('@')[0] if '@' in database_url else database_url.split(':')[0]}@***")
    
    # Import engine from src.db
    try:
        from src.db import engine, init_db_schema
        print("✅ Imported engine from src.db")
    except Exception as e:
        print(f"❌ Failed to import from src.db: {e}")
        sys.exit(1)
    
    # Verify we're using PostgreSQL
    dialect_name = engine.dialect.name
    print(f"🔌 Dialect: {dialect_name}")
    
    if dialect_name != "postgresql":
        print(f"❌ ERROR: Expected 'postgresql' dialect, got '{dialect_name}'")
        print("   Constitution V2.1 requires PostgreSQL for production")
        sys.exit(1)
    
    print("✅ PostgreSQL dialect confirmed")
    
    # Initialize schema
    try:
        print("🔧 Initializing database schema...")
        init_db_schema()
    except Exception as e:
        print(f"⚠️  Schema initialization warning: {e}")
    
    # Test connection with SELECT 1
    try:
        print("🔍 Testing connection with SELECT 1...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            assert row[0] == 1, "Query returned unexpected value"
        print("✅ Connection test successful")
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("✅ SMOKE TEST PASSED")
    print("=" * 60)

if __name__ == "__main__":
    main()
