#!/usr/bin/env python3
"""
DMS V2.1 PostgreSQL ONLINE-ONLY Smoke Test
Constitution V2.1 § 1.2: PostgreSQL obligatoire en production
"""
from pathlib import Path
import sys
import os

# Safeguard: Add repository root to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

print("=" * 80)
print("DMS V2.1 - POSTGRESQL ONLINE-ONLY SMOKE TEST")
print("=" * 80)
print()

# === SECTION 1: DATABASE_URL REQUIRED ===
print("🔍 Section 1: PostgreSQL Configuration (REQUIRED)")
print("-" * 80)

database_url = os.getenv("DATABASE_URL", "")
if not database_url:
    print("❌ ERROR: DATABASE_URL environment variable is REQUIRED")
    print("   Constitution V2.1 § 1.2: PostgreSQL obligatoire en production")
    print("   This is an ONLINE-ONLY system - no offline mode")
    sys.exit(1)

# Mask password in display
safe_url = database_url.split('@')[1] if '@' in database_url else database_url
print(f"✓ DATABASE_URL configured: ...@{safe_url}")

# === SECTION 2: POSTGRESQL DIALECT CHECK ===
print("\n" + "=" * 80)
print("🎯 Section 2: PostgreSQL Dialect Verification")
print("-" * 80)

try:
    from sqlalchemy import create_engine, text
    print("✓ SQLAlchemy imported")
except ImportError:
    print("❌ ERROR: SQLAlchemy not installed")
    print("   Install with: pip install sqlalchemy psycopg[binary]")
    sys.exit(1)

try:
    engine = create_engine(database_url)
    dialect_name = engine.dialect.name
    print(f"✓ Database dialect: {dialect_name}")
    
    if dialect_name != "postgresql":
        print(f"❌ ERROR: Dialect is '{dialect_name}', Constitution V2.1 requires 'postgresql'")
        print("   SQLite, MySQL, etc. are NOT allowed in production")
        sys.exit(1)
    
    print("✓ PostgreSQL confirmed (Constitution V2.1 compliant)")
    
except Exception as e:
    print(f"❌ ERROR: Failed to connect to database: {e}")
    sys.exit(1)

# === SECTION 3: CONNECTION & BASIC QUERY ===
print("\n" + "=" * 80)
print("💾 Section 3: Connection & Query Test")
print("-" * 80)

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.scalar()
        print(f"✓ Connected to PostgreSQL")
        print(f"  Version: {version.split(',')[0]}")
        
        # Check if we can create/query tables
        result = conn.execute(text("""
            SELECT count(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        table_count = result.scalar()
        print(f"✓ Query executed successfully")
        print(f"  Public tables: {table_count}")
        
except Exception as e:
    print(f"❌ ERROR: Database query failed: {e}")
    sys.exit(1)

# === SECTION 4: REPOSITORY STRUCTURE ===
print("\n" + "=" * 80)
print("📁 Section 4: Repository Structure")
print("-" * 80)

has_src = (ROOT / "src").exists() and (ROOT / "src").is_dir()
has_backend = (ROOT / "backend").exists() and (ROOT / "backend").is_dir()

if has_backend:
    print("❌ ERROR: backend/ directory found - Constitution V2.1 uses src/")
    sys.exit(1)

if not has_src:
    print("❌ ERROR: src/ directory not found - Constitution V2.1 requires src/")
    sys.exit(1)

print("✓ Repository structure: src/ (Constitution V2.1)")

# Try importing from src
try:
    import src.mapping
    print("✓ Module src.mapping imports successfully")
except ImportError as e:
    # Dependencies might be missing, but module structure is correct
    if "openpyxl" in str(e) or "python-docx" in str(e) or "pypdf" in str(e):
        print(f"✓ src.mapping module exists (runtime dependencies missing: OK)")
    else:
        print(f"❌ ERROR: Failed to import src.mapping: {e}")
        sys.exit(1)

# === FINAL VERDICT ===
print("\n" + "=" * 80)
print("📊 VERDICT")
print("=" * 80)
print()
print("✅ SMOKE TEST PASSED")
print()
print("Summary:")
print("  ✓ DATABASE_URL: configured")
print(f"  ✓ Dialect: {dialect_name} (PostgreSQL)")
print("  ✓ Connection: successful")
print("  ✓ Query execution: working")
print("  ✓ Repository structure: src/ (Constitution V2.1)")
print()
print("🎉 PostgreSQL ONLINE-ONLY system verified")
print()
