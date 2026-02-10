#!/usr/bin/env python3
"""
DMS V2.1 Constitution Smoke Test
Vérifie que le CI exécute le bon DMS (Constitution V2.1) et pas un cousin.
"""
from pathlib import Path
import sys
import os

# Safeguard: Add repository root to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

print("=" * 80)
print("DMS V2.1 CONSTITUTION - SMOKE TEST")
print("=" * 80)
print()

# === SECTION 1: ENVIRONMENT VERIFICATION ===
print("🔍 Section 1: Environment Verification")
print("-" * 80)

print("\n1.1 Working Directory:")
print(f"  pwd: {os.getcwd()}")

print("\n1.2 Repository Structure:")
repo_files = sorted(os.listdir(ROOT))
print(f"  Repository root: {ROOT}")
print(f"  Files/dirs: {', '.join(repo_files[:10])}{'...' if len(repo_files) > 10 else ''}")

print("\n1.3 Python Path (sys.path):")
for i, path in enumerate(sys.path[:5], 1):
    print(f"  {i}. {path}")

print("\n1.4 Module Resolution:")
import importlib.util as util

src_spec = util.find_spec('src')
backend_spec = util.find_spec('backend')
print(f"  src module: {src_spec}")
print(f"  backend module: {backend_spec}")

# === SECTION 2: CONSTITUTION V2.1 COMPLIANCE ===
print("\n" + "=" * 80)
print("🎯 Section 2: Constitution V2.1 Compliance")
print("-" * 80)

print("\n2.1 Repository Structure Check:")
# Constitution V2.1 uses src/ structure
has_src = (ROOT / "src").exists() and (ROOT / "src").is_dir()
has_backend = (ROOT / "backend").exists() and (ROOT / "backend").is_dir()

print(f"  ✓ src/ exists: {has_src}")
print(f"  ✗ backend/ exists: {has_backend}")

if has_backend:
    print(f"  ⚠️  WARNING: backend/ directory found - Constitution V2.1 uses src/")
    sys.exit(1)

if not has_src:
    print(f"  ❌ ERROR: src/ directory not found - Constitution V2.1 requires src/")
    sys.exit(1)

print(f"  ✓ Repository structure matches Constitution V2.1 (src/)")

print("\n2.2 Constitution V2.1 Files:")
constitution_files = {
    "docs/constitution_v2.1.md": "Constitution V2.1 spec",
    "COMPLIANCE_CHECKLIST.md": "Compliance checklist",
    "IMPLEMENTATION_GUIDE_COUCHE_B.md": "Implementation guide",
}

for file_path, description in constitution_files.items():
    exists = (ROOT / file_path).exists()
    status = "✓" if exists else "✗"
    print(f"  {status} {file_path}: {description}")

print("\n2.3 Module Import Check:")
# Try importing from src (Constitution V2.1 structure)
# First check if src.mapping exists as a module
try:
    import src.mapping
    print(f"  ✓ src.mapping module exists")
    
    # Try to import supplier_mapper (may fail if dependencies missing)
    try:
        from src.mapping import supplier_mapper
        print(f"  ✓ Successfully imported src.mapping.supplier_mapper")
    except ImportError as e:
        # Dependencies might be missing, but module structure is correct
        if "openpyxl" in str(e) or "python-docx" in str(e) or "pypdf" in str(e):
            print(f"  ⚠️  src.mapping imports OK, but runtime dependencies missing: {e}")
            print(f"     (This is expected if dependencies aren't installed yet)")
        else:
            print(f"  ❌ Failed to import from src.mapping: {e}")
            sys.exit(1)
except ImportError as e:
    print(f"  ❌ src.mapping module not found: {e}")
    sys.exit(1)

# Verify NO backend imports exist
try:
    # This should fail if we're following Constitution V2.1
    import backend.system.db
    print(f"  ❌ ERROR: backend.system.db should NOT exist in Constitution V2.1")
    sys.exit(1)
except ImportError:
    print(f"  ✓ Confirmed: backend.system.db does not exist (expected)")

# === SECTION 3: DATABASE COMPLIANCE (if PostgreSQL available) ===
print("\n" + "=" * 80)
print("💾 Section 3: Database Compliance")
print("-" * 80)

# Check if we have database dependencies
database_url = os.getenv("DATABASE_URL", "")
print(f"\n3.1 Database Configuration:")
print(f"  DATABASE_URL env: {'<set>' if database_url else '<not set>'}")

# Check for SQLite (Constitution V2.1 forbids SQLite in production)
has_sqlite_file = (ROOT / "data" / "dms.sqlite3").exists() if (ROOT / "data").exists() else False
print(f"\n3.2 SQLite Check:")
print(f"  SQLite file exists: {has_sqlite_file}")
if has_sqlite_file:
    print(f"  ⚠️  WARNING: SQLite found - Constitution V2.1 requires PostgreSQL in production")

# Try to check database dialect if we can import SQLAlchemy
try:
    from sqlalchemy import create_engine
    print(f"\n3.3 Database Dialect Check:")
    
    if database_url:
        # Remove password from display
        safe_url = database_url.split('@')[1] if '@' in database_url else database_url
        print(f"  Connecting to: ...@{safe_url}")
        
        engine = create_engine(database_url)
        dialect_name = engine.dialect.name
        print(f"  ✓ Dialect: {dialect_name}")
        
        if dialect_name == "postgresql":
            print(f"  ✓ PostgreSQL detected (Constitution V2.1 compliant)")
        else:
            print(f"  ❌ ERROR: Dialect is '{dialect_name}', Constitution V2.1 requires 'postgresql'")
            sys.exit(1)
    else:
        print(f"  ⚠️  SKIP: No DATABASE_URL provided (PostgreSQL check skipped)")
        
except ImportError:
    print(f"\n3.3 Database Dialect Check:")
    print(f"  ⚠️  SKIP: SQLAlchemy not installed (database check skipped)")

# === SECTION 4: SECURITY CHECK ===
print("\n" + "=" * 80)
print("🔐 Section 4: Security Check")
print("-" * 80)

print("\n4.1 Secrets Check:")
# Verify no secrets are exposed in this output
sensitive_patterns = [
    ("DATABASE_URL", os.getenv("DATABASE_URL", "")),
    ("SECRET_KEY", os.getenv("SECRET_KEY", "")),
    ("API_KEY", os.getenv("API_KEY", "")),
]

has_secrets = False
for key, value in sensitive_patterns:
    if value:
        # Don't print the actual value!
        print(f"  ⚠️  {key}: <REDACTED - present but not shown>")
        has_secrets = True

if not has_secrets:
    print(f"  ✓ No sensitive environment variables detected in common patterns")

# === SECTION 5: FINAL VERDICT ===
print("\n" + "=" * 80)
print("📊 VERDICT")
print("=" * 80)

print("\n✅ SMOKE TEST PASSED")
print("\nSummary:")
print("  ✓ Repository structure: src/ (Constitution V2.1)")
print("  ✓ Module resolution: src module found, backend NOT found")
print("  ✓ Imports: src.mapping imports successfully")
print("  ✓ No backend/ confusion detected")
if database_url and 'dialect_name' in locals() and dialect_name == "postgresql":
    print("  ✓ Database: PostgreSQL (compliant)")
else:
    print("  ⚠️  Database: Not verified (PostgreSQL check skipped)")
print("\n🎉 This is the correct DMS (Constitution V2.1)")
print()
