"""Add procurement references, categories, lots, thresholds

Revision ID: 003_add_procurement_extensions
Revises: 002_add_couche_a
Create Date: 2026-02-12 19:15:00
"""
from __future__ import annotations

from typing import Optional
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

try:
    from alembic import op
except ImportError:
    op = None

revision = '003_add_procurement_extensions'
down_revision = '002_add_couche_a'
branch_labels = None
depends_on = None


def _get_bind(engine: Optional[Engine] = None) -> Engine | Connection:
    """Retourne la connexion/engine approprié."""
    if engine is not None:
        return engine
    if op is not None:
        return op.get_bind()
    from src.db import engine as db_engine
    return db_engine


def _execute_sql(target, sql: str) -> None:
    """Exécute du SQL brut."""
    if isinstance(target, Engine):
        with target.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
    else:
        target.execute(text(sql))


def upgrade(engine: Optional[Engine] = None) -> None:
    """Crée tables procurement + purchase_categories (M2-Extended)."""
    bind = _get_bind(engine)
    timestamp = datetime.utcnow().isoformat()
    
    # ============================================
    # 1. RÉFÉRENCES UNIQUES (M2D)
    # ============================================
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS procurement_references (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            ref_type TEXT NOT NULL,
            ref_number TEXT NOT NULL UNIQUE,
            year INTEGER NOT NULL,
            sequence INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            created_by INTEGER REFERENCES users(id),
            UNIQUE (ref_type, year, sequence)
        )
    """)
    _execute_sql(bind, "CREATE INDEX IF NOT EXISTS idx_procref_case ON procurement_references(case_id)")
    _execute_sql(bind, "CREATE INDEX IF NOT EXISTS idx_procref_year ON procurement_references(year, ref_type)")

    # ============================================
    # 2. CATÉGORIES PROCÉDURES (M2E)
    # ============================================
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS procurement_categories (
            id TEXT PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            name_en TEXT NOT NULL,
            name_fr TEXT NOT NULL,
            threshold_usd NUMERIC(12,2),
            requires_technical_eval BOOLEAN DEFAULT TRUE,
            min_suppliers INTEGER DEFAULT 3,
            created_at TEXT NOT NULL
        )
    """)

    _execute_sql(bind, f"""
        INSERT INTO procurement_categories (id, code, name_en, name_fr, threshold_usd, requires_technical_eval, min_suppliers, created_at) VALUES
        ('cat_equipmed', 'EQUIPMED', 'Medical Equipment', 'Équipement médical', 50000, TRUE, 5, '{timestamp}'),
        ('cat_vehicules', 'VEHICULES', 'Vehicles', 'Véhicules', 100000, TRUE, 5, '{timestamp}'),
        ('cat_fournitures', 'FOURNITURES', 'Office Supplies', 'Fournitures bureau', 5000, FALSE, 3, '{timestamp}'),
        ('cat_it', 'IT', 'IT Equipment', 'Équipement IT', 25000, TRUE, 3, '{timestamp}'),
        ('cat_construction', 'CONSTRUCTION', 'Construction Works', 'Travaux construction', 150000, TRUE, 5, '{timestamp}'),
        ('cat_services', 'SERVICES', 'Professional Services', 'Services professionnels', 30000, TRUE, 3, '{timestamp}')
        ON CONFLICT (code) DO NOTHING
    """)

    # ============================================
    # 2B. CATÉGORIES MÉTIER (Manuel SCI)
    # ============================================
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS purchase_categories (
            id TEXT PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            label TEXT NOT NULL,
            is_high_risk BOOLEAN DEFAULT FALSE,
            requires_expert BOOLEAN DEFAULT FALSE,
            specific_rules_json JSON,
            created_at TEXT NOT NULL
        )
    """)

    _execute_sql(bind, f"""
        INSERT INTO purchase_categories (id, code, label, is_high_risk, requires_expert, specific_rules_json, created_at) VALUES
        ('cat_travel', 'TRAVEL', 'Voyages et hôtels', FALSE, FALSE, '{{"max_procedure": "devis_formel"}}', '{timestamp}'),
        ('cat_property', 'PROPERTY', 'Location immobilière', FALSE, FALSE, '{{"legal_review_required": true}}', '{timestamp}'),
        ('cat_constr', 'CONSTR', 'Construction', TRUE, TRUE, '{{"technical_expert_required": true, "site_visit_required": true}}', '{timestamp}'),
        ('cat_health', 'HEALTH', 'Produits de santé', TRUE, TRUE, '{{"qualified_suppliers_only": true}}', '{timestamp}'),
        ('cat_it_sci', 'IT', 'IT / Technologie', TRUE, FALSE, '{{"section_889_compliance": true, "it_approval_required": true}}', '{timestamp}'),
        ('cat_labor', 'LABOR', 'Main-d''œuvre externe', FALSE, FALSE, '{{"consultancy_fee_limits": true}}', '{timestamp}'),
        ('cat_cva', 'CVA', 'Espèces et bons (CVA)', FALSE, FALSE, '{{"fsp_panel_required": true}}', '{timestamp}'),
        ('cat_fleet', 'FLEET', 'Flotte et transport', FALSE, FALSE, '{{"fleet_fund_priority": true, "safety_standards": true}}', '{timestamp}'),
        ('cat_insurance', 'INSURANCE', 'Assurance', FALSE, FALSE, '{{"provider": "Marsh/MMB", "no_competition": true}}', '{timestamp}'),
        ('cat_generic', 'GENERIC', 'Achats généraux', FALSE, FALSE, '{{}}', '{timestamp}')
        ON CONFLICT (code) DO NOTHING
    """)

    # ============================================
    # 3. SEUILS PROCÉDURES (M2H)
    # ============================================
    _execute_sql(bind, """
        CREATE TABLE IF NOT EXISTS procurement_thresholds (
            id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            procedure_type TEXT NOT NULL UNIQUE,
            min_amount_usd NUMERIC(12,2) NOT NULL,
            max_amount_usd NUMERIC(12,2),
            min_suppliers INTEGER NOT NULL,
            description_en TEXT,
            description_fr TEXT
        )
    """)

    _execute_sql(bind, """
        INSERT INTO procurement_thresholds (procedure_type, min_amount_usd, max_amount_usd, min_suppliers, description_en, description_fr) VALUES
        ('RFQ', 0, 10000, 3, 'Request for Quotation', 'Demande de cotation'),
        ('RFP', 10001, 100000, 5, 'Request for Proposal', 'Demande de proposition'),
        ('DAO', 100001, NULL, 5, 'Open Tender', 'Appel d''offres ouvert')
        ON CONFLICT (procedure_type) DO NOTHING
    """)

    # ============================================
    # 4. ENRICHISSEMENT CASES (statements séparés)
    # ============================================
    _execute_sql(bind, "ALTER TABLE cases ADD COLUMN IF NOT EXISTS ref_id TEXT REFERENCES procurement_references(id)")
    _execute_sql(bind, "ALTER TABLE cases ADD COLUMN IF NOT EXISTS category_id TEXT REFERENCES procurement_categories(id)")
    _execute_sql(bind, "ALTER TABLE cases ADD COLUMN IF NOT EXISTS purchase_category_id TEXT REFERENCES purchase_categories(id)")
    _execute_sql(bind, "ALTER TABLE cases ADD COLUMN IF NOT EXISTS estimated_value NUMERIC(12,2)")
    _execute_sql(bind, "ALTER TABLE cases ADD COLUMN IF NOT EXISTS closing_date TEXT")
    _execute_sql(bind, "ALTER TABLE cases ADD COLUMN IF NOT EXISTS procedure_type TEXT")
    _execute_sql(bind, "ALTER TABLE cases ADD COLUMN IF NOT EXISTS total_upload_size BIGINT DEFAULT 0")

    _execute_sql(bind, "CREATE INDEX IF NOT EXISTS idx_cases_ref ON cases(ref_id)")
    _execute_sql(bind, "CREATE INDEX IF NOT EXISTS idx_cases_category ON cases(category_id)")
    _execute_sql(bind, "CREATE INDEX IF NOT EXISTS idx_cases_purchase_category ON cases(purchase_category_id)")

    # Contrainte procedure_type
    _execute_sql(bind, "ALTER TABLE cases DROP CONSTRAINT IF EXISTS check_procedure_type")
    _execute_sql(bind, """
        ALTER TABLE cases ADD CONSTRAINT check_procedure_type 
        CHECK (procedure_type IN ('devis_unique', 'devis_simple', 'devis_formel', 'appel_offres_ouvert'))
    """)

    # ============================================
    # 5. ENRICHISSEMENT LOTS
    # ============================================
    _execute_sql(bind, "ALTER TABLE lots ADD COLUMN IF NOT EXISTS category_id TEXT REFERENCES procurement_categories(id)")
    _execute_sql(bind, "CREATE INDEX IF NOT EXISTS idx_lots_category ON lots(category_id)")


def downgrade(engine: Optional[Engine] = None) -> None:
    """Supprime les tables et colonnes ajoutées."""
    bind = _get_bind(engine)
    
    # Lots
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_lots_category")
    _execute_sql(bind, "ALTER TABLE lots DROP COLUMN IF EXISTS category_id")
    
    # Cases
    _execute_sql(bind, "ALTER TABLE cases DROP CONSTRAINT IF EXISTS check_procedure_type")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_cases_purchase_category")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_cases_category")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_cases_ref")
    _execute_sql(bind, "ALTER TABLE cases DROP COLUMN IF EXISTS total_upload_size")
    _execute_sql(bind, "ALTER TABLE cases DROP COLUMN IF EXISTS procedure_type")
    _execute_sql(bind, "ALTER TABLE cases DROP COLUMN IF EXISTS closing_date")
    _execute_sql(bind, "ALTER TABLE cases DROP COLUMN IF EXISTS estimated_value")
    _execute_sql(bind, "ALTER TABLE cases DROP COLUMN IF EXISTS purchase_category_id")
    _execute_sql(bind, "ALTER TABLE cases DROP COLUMN IF EXISTS category_id")
    _execute_sql(bind, "ALTER TABLE cases DROP COLUMN IF EXISTS ref_id")
    
    # Tables
    _execute_sql(bind, "DROP TABLE IF EXISTS procurement_thresholds")
    _execute_sql(bind, "DROP TABLE IF EXISTS purchase_categories")
    _execute_sql(bind, "DROP TABLE IF EXISTS procurement_categories")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_procref_year")
    _execute_sql(bind, "DROP INDEX IF EXISTS idx_procref_case")
    _execute_sql(bind, "DROP TABLE IF EXISTS procurement_references")
