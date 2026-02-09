#!/usr/bin/env python3
"""
Smoke test PostgreSQL réel
Valide que le code fonctionne sur PostgreSQL avec placeholders transformés
"""

import os
import sys
import json
import uuid
from pathlib import Path
from datetime import datetime

# Configuration DATABASE_URL PostgreSQL
os.environ["DATABASE_URL"] = "postgresql+psycopg2://dms:dms@localhost:5432/dms"

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 70)
print("SMOKE TEST POSTGRESQL RÉEL")
print("=" * 70)
print()

# Import après avoir configuré DATABASE_URL
from src.db import engine, init_db
from main import (
    db_execute,
    db_execute_one,
    db_write,
    add_memory,
    register_artifact,
)

print(f"Database URL: {engine.url}")
print(f"Dialect: {engine.dialect.name}")
print()

# Initialiser schéma
print("1. Initialisation du schéma...")
try:
    init_db()
    print("   ✅ Schema created")
except Exception as e:
    print(f"   ❌ ERREUR: {e}")
    sys.exit(1)

# Vérifier tables
print()
print("2. Vérification des tables...")
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"   Tables: {len(tables)}")
for table in sorted(tables):
    print(f"     - {table}")

if len(tables) != 6:
    print(f"   ❌ ERREUR: Expected 6 tables, got {len(tables)}")
    sys.exit(1)
print("   ✅ All tables present")

# Créer un case
print()
print("3. Création d'un case...")
case_id = str(uuid.uuid4())
now = datetime.utcnow().isoformat()

try:
    db_write("""
        INSERT INTO cases (id, case_type, title, lot, created_at, status)
        VALUES (:0, :1, :2, :3, :4, :5)
    """, (case_id, "DAO", "Test PostgreSQL", None, now, "open"))
    print(f"   ✅ Case créé: {case_id}")
except Exception as e:
    print(f"   ❌ ERREUR INSERT: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Vérifier lecture
print()
print("4. Lecture du case...")
try:
    case = db_execute_one("SELECT * FROM cases WHERE id=:0", (case_id,))
    if not case:
        print("   ❌ ERREUR: Case not found")
        sys.exit(1)
    print(f"   ✅ Case lu: {case['title']}")
    print(f"      Status: {case['status']}")
except Exception as e:
    print(f"   ❌ ERREUR SELECT: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Ajouter un artifact
print()
print("5. Ajout d'un artifact...")
try:
    artifact_id = register_artifact(
        case_id, 
        "dao", 
        "test_dao.pdf", 
        "/tmp/test.pdf",
        meta={"test": True}
    )
    print(f"   ✅ Artifact créé: {artifact_id}")
except Exception as e:
    print(f"   ❌ ERREUR INSERT ARTIFACT: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Ajouter une entrée mémoire
print()
print("6. Ajout d'une entrée mémoire...")
try:
    mem_id = add_memory(case_id, "test", {"action": "smoke_test"})
    print(f"   ✅ Memory créée: {mem_id}")
except Exception as e:
    print(f"   ❌ ERREUR INSERT MEMORY: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# UPDATE status (simulation decide)
print()
print("7. Transition d'état (open → decided)...")
try:
    db_write("UPDATE cases SET status='decided' WHERE id=:0", (case_id,))
    print("   ✅ UPDATE exécuté")
except Exception as e:
    print(f"   ❌ ERREUR UPDATE: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Vérifier transition
print()
print("8. Vérification transition...")
try:
    case_updated = db_execute_one("SELECT * FROM cases WHERE id=:0", (case_id,))
    if case_updated["status"] != "decided":
        print(f"   ❌ ERREUR: Status = {case_updated['status']}, expected 'decided'")
        sys.exit(1)
    print(f"   ✅ Status transitionné: {case_updated['status']}")
except Exception as e:
    print(f"   ❌ ERREUR VERIFICATION: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Compter les entrées
print()
print("9. Comptage final...")
try:
    counts = {
        "cases": db_execute("SELECT COUNT(*) as c FROM cases")[0]["c"],
        "artifacts": db_execute("SELECT COUNT(*) as c FROM artifacts")[0]["c"],
        "memory_entries": db_execute("SELECT COUNT(*) as c FROM memory_entries")[0]["c"],
    }
    print(f"   Cases: {counts['cases']}")
    print(f"   Artifacts: {counts['artifacts']}")
    print(f"   Memory entries: {counts['memory_entries']}")
    
    if counts["cases"] != 1 or counts["artifacts"] != 1 or counts["memory_entries"] != 1:
        print(f"   ⚠️  WARNING: Unexpected counts")
    else:
        print("   ✅ Counts corrects")
except Exception as e:
    print(f"   ❌ ERREUR COUNT: {e}")
    sys.exit(1)

# Résumé final
print()
print("=" * 70)
print("✅ SMOKE TEST POSTGRESQL RÉUSSI")
print("=" * 70)
print()
print("Résumé:")
print(f"  Engine URL: {engine.url}")
print(f"  Dialect: {engine.dialect.name}")
print(f"  Tables: {len(tables)}")
print(f"  Case créé: {case_id}")
print(f"  Status final: {case_updated['status']}")
print(f"  Placeholders: :0, :1 → :p0, :p1 (transformation OK)")
print()
print("PostgreSQL réel validé ✅")
print()
