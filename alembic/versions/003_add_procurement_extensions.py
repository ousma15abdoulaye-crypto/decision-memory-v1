"""Add procurement extended: references, categories, lots, thresholds.

Revision ID: 003_add_procurement_extensions
Revises: 002_add_couche_a
Create Date: 2026-02-12 17:15
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision = '003_add_procurement_extensions'
down_revision = '002_add_couche_a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================
    # 1. RÉFÉRENCES UNIQUES (M2D)
    # ============================================
    op.create_table(
        'procurement_references',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('case_id', sa.Text(), nullable=False),
        sa.Column('ref_type', sa.Text(), nullable=False),
        sa.Column('ref_number', sa.Text(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('ref_number', name='uq_ref_number'),
        sa.UniqueConstraint('ref_type', 'year', 'sequence', name='uq_ref_type_year_seq')
    )
    op.create_index('idx_procref_case', 'procurement_references', ['case_id'])
    op.create_index('idx_procref_year', 'procurement_references', ['year', 'ref_type'])

    # ============================================
    # 2. CATÉGORIES D'ACHAT (M2E)
    # ============================================
    op.create_table(
        'procurement_categories',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('name_en', sa.Text(), nullable=False),
        sa.Column('name_fr', sa.Text(), nullable=False),
        sa.Column('threshold_usd', sa.Numeric(12, 2), nullable=True),
        sa.Column('requires_technical_eval', sa.Boolean(), server_default=sa.text('TRUE')),
        sa.Column('min_suppliers', sa.Integer(), server_default='3'),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_category_code')
    )

    # Seed catégories
    timestamp = datetime.utcnow().isoformat()
    op.execute(f"""
        INSERT INTO procurement_categories 
        (id, code, name_en, name_fr, threshold_usd, requires_technical_eval, min_suppliers, created_at)
        VALUES
        ('cat_equipmed', 'EQUIPMED', 'Medical Equipment', 'Équipement médical', 50000, TRUE, 5, '{timestamp}'),
        ('cat_vehicules', 'VEHICULES', 'Vehicles', 'Véhicules', 100000, TRUE, 5, '{timestamp}'),
        ('cat_fournitures', 'FOURNITURES', 'Office Supplies', 'Fournitures bureau', 5000, FALSE, 3, '{timestamp}'),
        ('cat_it', 'IT', 'IT Equipment', 'Équipement IT', 25000, TRUE, 3, '{timestamp}'),
        ('cat_construction', 'CONSTRUCTION', 'Construction Works', 'Travaux construction', 150000, TRUE, 5, '{timestamp}'),
        ('cat_services', 'SERVICES', 'Professional Services', 'Services professionnels', 30000, TRUE, 3, '{timestamp}')
    """)

    # ============================================
    # 2B. CATÉGORIES D'ACHAT MÉTIER (Manuel SCI)
    # ============================================
    op.create_table(
        'purchase_categories',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('label', sa.Text(), nullable=False),
        sa.Column('is_high_risk', sa.Boolean(), server_default=sa.text('FALSE')),
        sa.Column('requires_expert', sa.Boolean(), server_default=sa.text('FALSE')),
        sa.Column('specific_rules_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_purchase_category_code')
    )

    # Seed des 9 catégories du Manuel SCI (pages 34-44)
    op.execute(f"""
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
    """)

    # ============================================
    # 3. LOTS (M2F) - Ajout colonnes
    # ============================================
    op.add_column('lots', sa.Column('category_id', sa.Text(), nullable=True))
    op.create_foreign_key('fk_lots_category', 'lots', 'procurement_categories', ['category_id'], ['id'])
    op.create_index('idx_lots_category', 'lots', ['category_id'])

    # ============================================
    # 4. SEUILS PROCÉDURES (M2H)
    # ============================================
    op.create_table(
        'procurement_thresholds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('procedure_type', sa.Text(), nullable=False),
        sa.Column('min_amount_usd', sa.Numeric(12, 2), nullable=False),
        sa.Column('max_amount_usd', sa.Numeric(12, 2), nullable=True),
        sa.Column('min_suppliers', sa.Integer(), nullable=False),
        sa.Column('description_en', sa.Text(), nullable=True),
        sa.Column('description_fr', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('procedure_type', name='uq_procedure_type')
    )

    # Seed seuils Save the Children
    op.execute("""
        INSERT INTO procurement_thresholds 
        (id, procedure_type, min_amount_usd, max_amount_usd, min_suppliers, description_en, description_fr)
        VALUES
        (1, 'RFQ', 0, 10000, 3, 'Request for Quotation', 'Demande de cotation'),
        (2, 'RFP', 10001, 100000, 5, 'Request for Proposal', 'Demande de proposition'),
        (3, 'DAO', 100001, NULL, 5, 'Open Tender', 'Appel d''offres ouvert')
    """)

    # ============================================
    # 5. MODIFICATIONS TABLES EXISTANTES (M2F/M2G)
    # ============================================
    op.add_column('cases', sa.Column('ref_id', sa.Text(), nullable=True))
    op.add_column('cases', sa.Column('category_id', sa.Text(), nullable=True))
    op.add_column('cases', sa.Column('estimated_value', sa.Numeric(12, 2), nullable=True))
    op.add_column('cases', sa.Column('closing_date', sa.Text(), nullable=True))
    
    # Colonnes métier SCI
    op.add_column('cases', sa.Column('purchase_category_id', sa.Text(), nullable=True))
    op.add_column('cases', sa.Column('procedure_type', sa.Text(), nullable=True))
    
    op.create_foreign_key('fk_cases_ref', 'cases', 'procurement_references', ['ref_id'], ['id'])
    op.create_foreign_key('fk_cases_category', 'cases', 'procurement_categories', ['category_id'], ['id'])
    op.create_foreign_key('fk_cases_purchase_category', 'cases', 'purchase_categories', ['purchase_category_id'], ['id'])
    op.create_index('idx_cases_ref', 'cases', ['ref_id'])
    op.create_index('idx_cases_category', 'cases', ['category_id'])
    op.create_index('idx_cases_purchase_category', 'cases', ['purchase_category_id'])
    
    # Contrainte de validation sur procedure_type
    op.execute("""
        ALTER TABLE cases ADD CONSTRAINT check_procedure_type 
        CHECK (procedure_type IN ('devis_unique', 'devis_simple', 'devis_formel', 'appel_offres_ouvert'))
    """)


def downgrade() -> None:
    # Ordre inverse
    op.execute("ALTER TABLE cases DROP CONSTRAINT IF EXISTS check_procedure_type")
    op.drop_index('idx_cases_purchase_category', table_name='cases')
    op.drop_index('idx_cases_category', table_name='cases')
    op.drop_index('idx_cases_ref', table_name='cases')
    op.drop_constraint('fk_cases_purchase_category', 'cases', type_='foreignkey')
    op.drop_constraint('fk_cases_category', 'cases', type_='foreignkey')
    op.drop_constraint('fk_cases_ref', 'cases', type_='foreignkey')
    op.drop_column('cases', 'procedure_type')
    op.drop_column('cases', 'purchase_category_id')
    op.drop_column('cases', 'closing_date')
    op.drop_column('cases', 'estimated_value')
    op.drop_column('cases', 'category_id')
    op.drop_column('cases', 'ref_id')
    
    op.drop_table('procurement_thresholds')
    
    op.drop_index('idx_lots_category', table_name='lots')
    op.drop_constraint('fk_lots_category', 'lots', type_='foreignkey')
    op.drop_column('lots', 'category_id')
    
    op.drop_table('purchase_categories')
    op.drop_table('procurement_categories')
    
    op.drop_index('idx_procref_year', table_name='procurement_references')
    op.drop_index('idx_procref_case', table_name='procurement_references')
    op.drop_t
