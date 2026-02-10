"""
Couche B — SQLAlchemy Models
Constitution DMS V2.1 §4 (Catalogs) + §5 (Market Signals)
"""

from sqlalchemy import (
    Table, Column, String, Integer, Numeric, Date, TIMESTAMP,
    ForeignKey, Index, CheckConstraint, UniqueConstraint,
    Text, JSON
)
from sqlalchemy.sql import func
from src.db import metadata

# Enum definitions (as constraints)
STATUS_ENUM = ['proposed', 'active', 'rejected', 'inactive']
CONFIDENCE_ENUM = ['EXACT', 'ESTIMATED', 'INDICATIVE']
VALIDATION_STATUS_ENUM = ['pending', 'confirmed', 'rejected']

# 1. VENDORS TABLE
vendors = Table(
    'vendors',
    metadata,
    Column('vendor_id', String(20), primary_key=True),
    Column('canonical_name', String(200), nullable=False, unique=True),
    Column('status', String(20), nullable=False, default='proposed'),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
    Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    Column('created_by', String(100)),
    Column('metadata_json', JSON),
    CheckConstraint("status IN ('proposed', 'active', 'rejected', 'inactive')", name='vendors_status_check'),
    schema='couche_b'
)

# 2. VENDOR_ALIASES TABLE
vendor_aliases = Table(
    'vendor_aliases',
    metadata,
    Column('alias_id', String(20), primary_key=True),
    Column('vendor_id', String(20), ForeignKey('couche_b.vendors.vendor_id', ondelete='CASCADE'), nullable=False),
    Column('alias_name', String(200), nullable=False),
    Column('confidence', String(20), nullable=False, default='EXACT'),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
    Column('created_by', String(100)),
    CheckConstraint("confidence IN ('EXACT', 'ESTIMATED', 'INDICATIVE')", name='vendor_aliases_confidence_check'),
    Index('idx_vendor_aliases_vendor_id', 'vendor_id'),
    Index('idx_vendor_aliases_alias_name', 'alias_name'),
    schema='couche_b'
)

# 3. VENDOR_EVENTS TABLE
vendor_events = Table(
    'vendor_events',
    metadata,
    Column('event_id', String(20), primary_key=True),
    Column('vendor_id', String(20), ForeignKey('couche_b.vendors.vendor_id', ondelete='CASCADE'), nullable=False),
    Column('event_type', String(50), nullable=False),
    Column('event_date', Date, nullable=False),
    Column('details', JSON),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
    Column('created_by', String(100)),
    CheckConstraint("event_type IN ('merger', 'split', 'name_change', 'status_change')", name='vendor_events_type_check'),
    Index('idx_vendor_events_vendor_id', 'vendor_id'),
    Index('idx_vendor_events_event_date', 'event_date'),
    schema='couche_b'
)

# 4. ITEMS TABLE
items = Table(
    'items',
    metadata,
    Column('item_id', String(20), primary_key=True),
    Column('canonical_description', String(500), nullable=False, unique=True),
    Column('category', String(100)),
    Column('status', String(20), nullable=False, default='proposed'),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
    Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    Column('created_by', String(100)),
    Column('metadata_json', JSON),
    CheckConstraint("status IN ('proposed', 'active', 'rejected', 'inactive')", name='items_status_check'),
    schema='couche_b'
)

# 5. ITEM_ALIASES TABLE
item_aliases = Table(
    'item_aliases',
    metadata,
    Column('alias_id', String(20), primary_key=True),
    Column('item_id', String(20), ForeignKey('couche_b.items.item_id', ondelete='CASCADE'), nullable=False),
    Column('alias_description', String(500), nullable=False),
    Column('confidence', String(20), nullable=False, default='EXACT'),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
    Column('created_by', String(100)),
    CheckConstraint("confidence IN ('EXACT', 'ESTIMATED', 'INDICATIVE')", name='item_aliases_confidence_check'),
    Index('idx_item_aliases_item_id', 'item_id'),
    Index('idx_item_aliases_alias_description', 'alias_description'),
    schema='couche_b'
)

# 6. UNITS TABLE
units = Table(
    'units',
    metadata,
    Column('unit_id', String(20), primary_key=True),
    Column('canonical_symbol', String(20), nullable=False, unique=True),
    Column('canonical_name', String(100), nullable=False),
    Column('unit_type', String(50), nullable=False),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
    Column('metadata_json', JSON),
    CheckConstraint("unit_type IN ('weight', 'volume', 'length', 'area', 'count', 'package')", name='units_type_check'),
    schema='couche_b'
)

# 7. UNIT_ALIASES TABLE
unit_aliases = Table(
    'unit_aliases',
    metadata,
    Column('alias_id', String(20), primary_key=True),
    Column('unit_id', String(20), ForeignKey('couche_b.units.unit_id', ondelete='CASCADE'), nullable=False),
    Column('alias_symbol', String(20)),
    Column('alias_name', String(100)),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
    Index('idx_unit_aliases_unit_id', 'unit_id'),
    schema='couche_b'
)

# 8. GEO_MASTER TABLE
geo_master = Table(
    'geo_master',
    metadata,
    Column('geo_id', String(20), primary_key=True),
    Column('canonical_name', String(200), nullable=False, unique=True),
    Column('geo_type', String(50), nullable=False),
    Column('parent_geo_id', String(20), ForeignKey('couche_b.geo_master.geo_id', ondelete='SET NULL')),
    Column('status', String(20), nullable=False, default='active'),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
    Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    Column('metadata_json', JSON),
    CheckConstraint("geo_type IN ('region', 'city', 'commune', 'country')", name='geo_master_type_check'),
    CheckConstraint("status IN ('proposed', 'active', 'rejected', 'inactive')", name='geo_master_status_check'),
    Index('idx_geo_master_parent_geo_id', 'parent_geo_id'),
    schema='couche_b'
)

# 9. GEO_ALIASES TABLE
geo_aliases = Table(
    'geo_aliases',
    metadata,
    Column('alias_id', String(20), primary_key=True),
    Column('geo_id', String(20), ForeignKey('couche_b.geo_master.geo_id', ondelete='CASCADE'), nullable=False),
    Column('alias_name', String(200), nullable=False),
    Column('confidence', String(20), nullable=False, default='EXACT'),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("confidence IN ('EXACT', 'ESTIMATED', 'INDICATIVE')", name='geo_aliases_confidence_check'),
    Index('idx_geo_aliases_geo_id', 'geo_id'),
    Index('idx_geo_aliases_alias_name', 'alias_name'),
    schema='couche_b'
)

# 10. MARKET_SIGNALS TABLE
market_signals = Table(
    'market_signals',
    metadata,
    Column('signal_id', String(20), primary_key=True),
    Column('observation_date', Date, nullable=False),
    Column('item_id', String(20), ForeignKey('couche_b.items.item_id', ondelete='RESTRICT'), nullable=False),
    Column('vendor_id', String(20), ForeignKey('couche_b.vendors.vendor_id', ondelete='SET NULL')),
    Column('geo_id', String(20), ForeignKey('couche_b.geo_master.geo_id', ondelete='RESTRICT'), nullable=False),
    Column('unit_id', String(20), ForeignKey('couche_b.units.unit_id', ondelete='RESTRICT'), nullable=False),
    Column('quantity', Numeric(15, 3), nullable=False),
    Column('unit_price', Numeric(15, 2), nullable=False),
    Column('total_price', Numeric(15, 2)),
    Column('validation_status', String(20), nullable=False, default='pending'),
    Column('source_type', String(50)),
    Column('source_ref', String(100)),
    Column('notes', Text),
    Column('superseded_by', String(20), ForeignKey('couche_b.market_signals.signal_id', ondelete='SET NULL')),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
    Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    Column('created_by', String(100)),
    Column('validated_by', String(100)),
    Column('validated_at', TIMESTAMP(timezone=True)),
    CheckConstraint("validation_status IN ('pending', 'confirmed', 'rejected')", name='market_signals_validation_check'),
    CheckConstraint("quantity > 0", name='market_signals_quantity_positive'),
    CheckConstraint("unit_price >= 0", name='market_signals_price_non_negative'),
    Index('idx_market_signals_item_geo_date', 'item_id', 'geo_id', 'observation_date'),
    Index('idx_market_signals_vendor_date', 'vendor_id', 'observation_date'),
    Index('idx_market_signals_source', 'source_type', 'source_ref'),
    Index('idx_market_signals_validation', 'validation_status'),
    schema='couche_b'
)

# Export all tables
__all__ = [
    'vendors',
    'vendor_aliases',
    'vendor_events',
    'items',
    'item_aliases',
    'units',
    'unit_aliases',
    'geo_master',
    'geo_aliases',
    'market_signals',
]
