"""Add Couche B schema

Revision ID: 001_add_couche_b
Revises: 
Create Date: 2026-02-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_add_couche_b'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Couche B schema and all tables"""
    
    # Create schema
    op.execute("CREATE SCHEMA IF NOT EXISTS couche_b")
    
    # 1. VENDORS TABLE
    op.create_table(
        'vendors',
        sa.Column('vendor_id', sa.String(20), primary_key=True),
        sa.Column('canonical_name', sa.String(200), nullable=False, unique=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='proposed'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(100)),
        sa.Column('metadata_json', sa.JSON),
        sa.CheckConstraint("status IN ('proposed', 'active', 'rejected', 'inactive')", name='vendors_status_check'),
        schema='couche_b'
    )
    
    # 2. VENDOR_ALIASES TABLE
    op.create_table(
        'vendor_aliases',
        sa.Column('alias_id', sa.String(20), primary_key=True),
        sa.Column('vendor_id', sa.String(20), nullable=False),
        sa.Column('alias_name', sa.String(200), nullable=False),
        sa.Column('confidence', sa.String(20), nullable=False, server_default='EXACT'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(100)),
        sa.ForeignKeyConstraint(['vendor_id'], ['couche_b.vendors.vendor_id'], ondelete='CASCADE'),
        sa.CheckConstraint("confidence IN ('EXACT', 'ESTIMATED', 'INDICATIVE')", name='vendor_aliases_confidence_check'),
        schema='couche_b'
    )
    op.create_index('idx_vendor_aliases_vendor_id', 'vendor_aliases', ['vendor_id'], schema='couche_b')
    op.create_index('idx_vendor_aliases_alias_name', 'vendor_aliases', ['alias_name'], schema='couche_b')
    
    # 3. VENDOR_EVENTS TABLE
    op.create_table(
        'vendor_events',
        sa.Column('event_id', sa.String(20), primary_key=True),
        sa.Column('vendor_id', sa.String(20), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_date', sa.Date, nullable=False),
        sa.Column('details', sa.JSON),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(100)),
        sa.ForeignKeyConstraint(['vendor_id'], ['couche_b.vendors.vendor_id'], ondelete='CASCADE'),
        sa.CheckConstraint("event_type IN ('merger', 'split', 'name_change', 'status_change')", name='vendor_events_type_check'),
        schema='couche_b'
    )
    op.create_index('idx_vendor_events_vendor_id', 'vendor_events', ['vendor_id'], schema='couche_b')
    op.create_index('idx_vendor_events_event_date', 'vendor_events', ['event_date'], schema='couche_b')
    
    # 4. ITEMS TABLE
    op.create_table(
        'items',
        sa.Column('item_id', sa.String(20), primary_key=True),
        sa.Column('canonical_description', sa.String(500), nullable=False, unique=True),
        sa.Column('category', sa.String(100)),
        sa.Column('status', sa.String(20), nullable=False, server_default='proposed'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(100)),
        sa.Column('metadata_json', sa.JSON),
        sa.CheckConstraint("status IN ('proposed', 'active', 'rejected', 'inactive')", name='items_status_check'),
        schema='couche_b'
    )
    
    # 5. ITEM_ALIASES TABLE
    op.create_table(
        'item_aliases',
        sa.Column('alias_id', sa.String(20), primary_key=True),
        sa.Column('item_id', sa.String(20), nullable=False),
        sa.Column('alias_description', sa.String(500), nullable=False),
        sa.Column('confidence', sa.String(20), nullable=False, server_default='EXACT'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(100)),
        sa.ForeignKeyConstraint(['item_id'], ['couche_b.items.item_id'], ondelete='CASCADE'),
        sa.CheckConstraint("confidence IN ('EXACT', 'ESTIMATED', 'INDICATIVE')", name='item_aliases_confidence_check'),
        schema='couche_b'
    )
    op.create_index('idx_item_aliases_item_id', 'item_aliases', ['item_id'], schema='couche_b')
    op.create_index('idx_item_aliases_alias_description', 'item_aliases', ['alias_description'], schema='couche_b')
    
    # 6. UNITS TABLE
    op.create_table(
        'units',
        sa.Column('unit_id', sa.String(20), primary_key=True),
        sa.Column('canonical_symbol', sa.String(20), nullable=False, unique=True),
        sa.Column('canonical_name', sa.String(100), nullable=False),
        sa.Column('unit_type', sa.String(50), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('metadata_json', sa.JSON),
        sa.CheckConstraint("unit_type IN ('weight', 'volume', 'length', 'area', 'count', 'package')", name='units_type_check'),
        schema='couche_b'
    )
    
    # 7. UNIT_ALIASES TABLE
    op.create_table(
        'unit_aliases',
        sa.Column('alias_id', sa.String(20), primary_key=True),
        sa.Column('unit_id', sa.String(20), nullable=False),
        sa.Column('alias_symbol', sa.String(20)),
        sa.Column('alias_name', sa.String(100)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['unit_id'], ['couche_b.units.unit_id'], ondelete='CASCADE'),
        schema='couche_b'
    )
    op.create_index('idx_unit_aliases_unit_id', 'unit_aliases', ['unit_id'], schema='couche_b')
    
    # 8. GEO_MASTER TABLE
    op.create_table(
        'geo_master',
        sa.Column('geo_id', sa.String(20), primary_key=True),
        sa.Column('canonical_name', sa.String(200), nullable=False, unique=True),
        sa.Column('geo_type', sa.String(50), nullable=False),
        sa.Column('parent_geo_id', sa.String(20)),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('metadata_json', sa.JSON),
        sa.ForeignKeyConstraint(['parent_geo_id'], ['couche_b.geo_master.geo_id'], ondelete='SET NULL'),
        sa.CheckConstraint("geo_type IN ('region', 'city', 'commune', 'country')", name='geo_master_type_check'),
        sa.CheckConstraint("status IN ('proposed', 'active', 'rejected', 'inactive')", name='geo_master_status_check'),
        schema='couche_b'
    )
    op.create_index('idx_geo_master_parent_geo_id', 'geo_master', ['parent_geo_id'], schema='couche_b')
    
    # 9. GEO_ALIASES TABLE
    op.create_table(
        'geo_aliases',
        sa.Column('alias_id', sa.String(20), primary_key=True),
        sa.Column('geo_id', sa.String(20), nullable=False),
        sa.Column('alias_name', sa.String(200), nullable=False),
        sa.Column('confidence', sa.String(20), nullable=False, server_default='EXACT'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['geo_id'], ['couche_b.geo_master.geo_id'], ondelete='CASCADE'),
        sa.CheckConstraint("confidence IN ('EXACT', 'ESTIMATED', 'INDICATIVE')", name='geo_aliases_confidence_check'),
        schema='couche_b'
    )
    op.create_index('idx_geo_aliases_geo_id', 'geo_aliases', ['geo_id'], schema='couche_b')
    op.create_index('idx_geo_aliases_alias_name', 'geo_aliases', ['alias_name'], schema='couche_b')
    
    # 10. MARKET_SIGNALS TABLE
    op.create_table(
        'market_signals',
        sa.Column('signal_id', sa.String(20), primary_key=True),
        sa.Column('observation_date', sa.Date, nullable=False),
        sa.Column('item_id', sa.String(20), nullable=False),
        sa.Column('vendor_id', sa.String(20)),
        sa.Column('geo_id', sa.String(20), nullable=False),
        sa.Column('unit_id', sa.String(20), nullable=False),
        sa.Column('quantity', sa.Numeric(15, 3), nullable=False),
        sa.Column('unit_price', sa.Numeric(15, 2), nullable=False),
        sa.Column('total_price', sa.Numeric(15, 2)),
        sa.Column('validation_status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('source_type', sa.String(50)),
        sa.Column('source_ref', sa.String(100)),
        sa.Column('notes', sa.Text),
        sa.Column('superseded_by', sa.String(20)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(100)),
        sa.Column('validated_by', sa.String(100)),
        sa.Column('validated_at', sa.TIMESTAMP(timezone=True)),
        sa.ForeignKeyConstraint(['item_id'], ['couche_b.items.item_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['vendor_id'], ['couche_b.vendors.vendor_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['geo_id'], ['couche_b.geo_master.geo_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['unit_id'], ['couche_b.units.unit_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['superseded_by'], ['couche_b.market_signals.signal_id'], ondelete='SET NULL'),
        sa.CheckConstraint("validation_status IN ('pending', 'confirmed', 'rejected')", name='market_signals_validation_check'),
        sa.CheckConstraint("quantity > 0", name='market_signals_quantity_positive'),
        sa.CheckConstraint("unit_price >= 0", name='market_signals_price_non_negative'),
        schema='couche_b'
    )
    op.create_index('idx_market_signals_item_geo_date', 'market_signals', ['item_id', 'geo_id', 'observation_date'], schema='couche_b')
    op.create_index('idx_market_signals_vendor_date', 'market_signals', ['vendor_id', 'observation_date'], schema='couche_b')
    op.create_index('idx_market_signals_source', 'market_signals', ['source_type', 'source_ref'], schema='couche_b')
    op.create_index('idx_market_signals_validation', 'market_signals', ['validation_status'], schema='couche_b')


def downgrade() -> None:
    """Drop Couche B schema and all tables"""
    op.execute("DROP SCHEMA IF EXISTS couche_b CASCADE")
