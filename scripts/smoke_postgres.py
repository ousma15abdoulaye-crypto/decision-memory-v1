#!/usr/bin/env python3
"""
Smoke test for PostgreSQL + Couche B setup
Validates DATABASE_URL, async engine, and basic imports
"""

import sys
from pathlib import Path

# Add repo root to path for 'import src' to work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
import asyncio


async def smoke_test_async():
    """Test async PostgreSQL connection"""
    database_url = os.getenv("DATABASE_URL", "sqlite:///data/dms.sqlite3")
    
    print(f"📊 DATABASE_URL: {database_url}")
    
    if not database_url.startswith("postgresql"):
        print("⚠️  Not using PostgreSQL, skipping async test")
        return True
    
    # Test async engine
    try:
        async_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        if "asyncpg" not in async_url:
            async_url = database_url  # Already has driver
        
        print(f"🔌 Testing async connection: {async_url.split('@')[0]}@***")
        
        engine = create_async_engine(async_url, echo=False)
        
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            assert row[0] == 1, "Query failed"
        
        await engine.dispose()
        print("✅ Async PostgreSQL connection successful")
        return True
        
    except Exception as e:
        print(f"❌ Async connection failed: {e}")
        return False


def smoke_test_imports():
    """Test Couche B imports"""
    try:
        print("🔍 Testing imports...")
        import src
        print("  ✅ src imported")
        
        import src.couche_b
        print("  ✅ src.couche_b imported")
        
        from src.couche_b import models, resolvers, routers, seed
        print("  ✅ All Couche B modules imported")
        
        # Check that tables are defined
        assert hasattr(models, 'vendors'), "vendors table not found"
        assert hasattr(models, 'market_signals'), "market_signals table not found"
        print("  ✅ Tables defined correctly")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def main():
    """Run all smoke tests"""
    print("=" * 60)
    print("SMOKE TEST: PostgreSQL + Couche B")
    print("=" * 60)
    print()
    
    # Test 1: Imports
    if not smoke_test_imports():
        sys.exit(1)
    
    print()
    
    # Test 2: Async database
    if not asyncio.run(smoke_test_async()):
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("✅ All smoke tests PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
