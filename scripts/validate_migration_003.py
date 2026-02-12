#!/usr/bin/env python3
"""
Script de validation de la migration 003
Vérifie que toutes les tables et colonnes attendues existent après migration.
Constitution V2.1 - PostgreSQL only
"""
import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect, text


def validate_migration_003():
    """Valide que la migration 003 a correctement créé toutes les structures."""
    
    # Vérifier que DATABASE_URL est défini
    if not os.environ.get("DATABASE_URL"):
        print("❌ DATABASE_URL non défini. Impossible de valider.")
        print("   Définir DATABASE_URL pour tester la migration.")
        sys.exit(1)
    
    from src.db import engine
    
    print("🔍 Validation migration 003...")
    print(f"   Database: {engine.url.database}")
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    errors = []
    warnings = []
    
    # 1. Vérifier les nouvelles tables
    expected_tables = [
        "procurement_references",
        "procurement_categories",
        "purchase_categories",
        "procurement_thresholds"
    ]
    
    print("\n📊 Vérification des tables...")
    for table in expected_tables:
        if table in tables:
            print(f"   ✅ {table}")
        else:
            errors.append(f"Table manquante: {table}")
            print(f"   ❌ {table}")
    
    # 2. Vérifier les colonnes de cases
    print("\n📋 Vérification des colonnes cases...")
    if "cases" in tables:
        cases_columns = {col['name'] for col in inspector.get_columns('cases')}
        expected_cases_cols = [
            "ref_id",
            "category_id",
            "purchase_category_id",
            "procedure_type",
            "estimated_value",
            "closing_date"
        ]
        for col in expected_cases_cols:
            if col in cases_columns:
                print(f"   ✅ cases.{col}")
            else:
                errors.append(f"Colonne manquante: cases.{col}")
                print(f"   ❌ cases.{col}")
    else:
        errors.append("Table cases non trouvée")
    
    # 3. Vérifier les colonnes de lots
    print("\n📋 Vérification des colonnes lots...")
    if "lots" in tables:
        lots_columns = {col['name'] for col in inspector.get_columns('lots')}
        if "category_id" in lots_columns:
            print(f"   ✅ lots.category_id")
        else:
            errors.append(f"Colonne manquante: lots.category_id")
            print(f"   ❌ lots.category_id")
    else:
        warnings.append("Table lots non trouvée (attendue de migration 002)")
    
    # 4. Vérifier les seed data
    print("\n🌱 Vérification des seed data...")
    with engine.connect() as conn:
        # procurement_categories: 6 entrées
        result = conn.execute(text("SELECT COUNT(*) FROM procurement_categories"))
        count = result.scalar()
        if count == 6:
            print(f"   ✅ procurement_categories: {count} entrées")
        else:
            errors.append(f"procurement_categories: attendu 6, trouvé {count}")
            print(f"   ❌ procurement_categories: {count} (attendu 6)")
        
        # purchase_categories: 10 entrées
        result = conn.execute(text("SELECT COUNT(*) FROM purchase_categories"))
        count = result.scalar()
        if count == 10:
            print(f"   ✅ purchase_categories: {count} entrées")
        else:
            errors.append(f"purchase_categories: attendu 10, trouvé {count}")
            print(f"   ❌ purchase_categories: {count} (attendu 10)")
        
        # procurement_thresholds: 3 entrées
        result = conn.execute(text("SELECT COUNT(*) FROM procurement_thresholds"))
        count = result.scalar()
        if count == 3:
            print(f"   ✅ procurement_thresholds: {count} entrées")
        else:
            errors.append(f"procurement_thresholds: attendu 3, trouvé {count}")
            print(f"   ❌ procurement_thresholds: {count} (attendu 3)")
    
    # 5. Vérifier la contrainte CHECK sur procedure_type
    print("\n🔒 Vérification des contraintes...")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT constraint_name, check_clause
            FROM information_schema.check_constraints
            WHERE constraint_name = 'check_procedure_type'
        """))
        constraint = result.fetchone()
        if constraint:
            print(f"   ✅ check_procedure_type existe")
        else:
            warnings.append("Contrainte check_procedure_type non trouvée")
            print(f"   ⚠️  check_procedure_type non trouvée")
    
    # Rapport final
    print("\n" + "="*60)
    if errors:
        print(f"❌ VALIDATION ÉCHOUÉE - {len(errors)} erreur(s)")
        for error in errors:
            print(f"   • {error}")
        sys.exit(1)
    elif warnings:
        print(f"⚠️  VALIDATION PARTIELLE - {len(warnings)} avertissement(s)")
        for warning in warnings:
            print(f"   • {warning}")
        sys.exit(0)
    else:
        print("✅ VALIDATION RÉUSSIE")
        print("   Migration 003 correctement appliquée")
        sys.exit(0)


if __name__ == "__main__":
    validate_migration_003()
