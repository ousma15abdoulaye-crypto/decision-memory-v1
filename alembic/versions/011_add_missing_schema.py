"""Add missing tables per Constitution V3.3.2.

Revision ID: 011_add_missing_schema
Revises: 010_enforce_append_only_audit
Create Date: 2026-02-19

Constitution V3.3.2 — Milestone M-SCHEMA-CORE
Tables manquantes identifiées après audit de la chaîne existante :
  - dictionary  : dictionnaire Sahel, 9 familles, absent de la chaîne
  - market_data : mémoire marché append-only, distinct de market_signals
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid

revision = '011_add_missing_schema'
down_revision = '010_enforce_append_only_audit'
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ── TABLE : dictionary ─────────────────────────────────────────
    # Dictionnaire Sahel — 9 familles minimum (Constitution V3.3.2)
    # Absent de toute la chaîne existante 002→010
    # Familles : carburants, construction_liants, construction_agregats,
    #            construction_fer, vehicules, informatique, alimentation,
    #            medicaments, equipements
    op.create_table(
        'dictionary',
        sa.Column('id', UUID(as_uuid=True), primary_key=True,
                  default=uuid.uuid4),
        sa.Column('canonical_name', sa.String(255), nullable=False,
                  unique=True),
        sa.Column('family', sa.String(100), nullable=False),
        sa.Column('unit', sa.String(50), nullable=False),
        sa.Column('aliases', JSONB, nullable=False,
                  server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_dictionary_family', 'dictionary', ['family'])
    op.create_index('ix_dictionary_canonical', 'dictionary',
                    ['canonical_name'])

    # ── TABLE : market_data ────────────────────────────────────────
    # Couche B — append-only (Invariant 9 Constitution V3.3.2)
    # Distinct de market_signals :
    #   market_signals = signaux bruts
    #   market_data    = données prix structurées par item/fournisseur
    op.create_table(
        'market_data',
        sa.Column('id', UUID(as_uuid=True), primary_key=True,
                  default=uuid.uuid4),
        sa.Column('item_canonical', sa.String(255), nullable=False),
        sa.Column('family', sa.String(100), nullable=False),
        sa.Column('unit', sa.String(50), nullable=False),
        sa.Column('unit_price', sa.Numeric(12, 4), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False,
                  server_default='XOF'),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('zone', sa.String(100), nullable=True),
        sa.Column('source_process_id', sa.String(255), nullable=True),
        sa.Column('supplier_id', UUID(as_uuid=True),
                  nullable=True),
        sa.Column('observed_at', sa.DateTime(timezone=True),
                  nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_market_data_item_family', 'market_data',
                    ['item_canonical', 'family'])
    op.create_index('ix_market_data_observed_at', 'market_data',
                    ['observed_at'])
    op.create_index('ix_market_data_supplier', 'market_data',
                    ['supplier_id'])
    op.create_unique_constraint(
        'uq_market_data_item_supplier_date',
        'market_data',
        ['item_canonical', 'supplier_id', 'observed_at']
    )


def downgrade() -> None:
    op.drop_constraint('uq_market_data_item_supplier_date',
                       'market_data', type_='unique')
    op.drop_index('ix_market_data_supplier', 'market_data')
    op.drop_index('ix_market_data_observed_at', 'market_data')
    op.drop_index('ix_market_data_item_family', 'market_data')
    op.drop_table('market_data')
    op.drop_index('ix_dictionary_canonical', 'dictionary')
    op.drop_index('ix_dictionary_family', 'dictionary')
    op.drop_table('dictionary')
