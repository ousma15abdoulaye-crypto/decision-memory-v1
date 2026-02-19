"""init schema

Revision ID: 0001
Revises:
Create Date: 2026-02-19

Référence : Constitution V3.3.2 — Milestone M-SCHEMA-CORE
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ── TABLE : suppliers ──────────────────────────────────────────
    op.create_table(
        'suppliers',
        sa.Column('id', UUID(as_uuid=True), primary_key=True,
                  default=uuid.uuid4),
        sa.Column('canonical_name', sa.String(255), nullable=False,
                  unique=True),
        sa.Column('aliases', JSONB, nullable=False, server_default='[]'),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(),
                  nullable=False),
    )

    # ── TABLE : dictionary ─────────────────────────────────────────
    # Dictionnaire Sahel — 9 familles minimum (Constitution V3.3.2)
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
        sa.Column('aliases', JSONB, nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # ── TABLE : offers ─────────────────────────────────────────────
    op.create_table(
        'offers',
        sa.Column('id', UUID(as_uuid=True), primary_key=True,
                  default=uuid.uuid4),
        sa.Column('process_id', sa.String(255), nullable=False),
        sa.Column('supplier_id', UUID(as_uuid=True),
                  sa.ForeignKey('suppliers.id'), nullable=True),
        sa.Column('raw_filename', sa.String(500), nullable=False),
        sa.Column('raw_content', sa.Text, nullable=True),
        sa.Column('status', sa.String(50), nullable=False,
                  server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # ── TABLE : structured_data ────────────────────────────────────
    # Offres normalisées — JSONB (Constitution V3.3.2 §4)
    op.create_table(
        'structured_data',
        sa.Column('id', UUID(as_uuid=True), primary_key=True,
                  default=uuid.uuid4),
        sa.Column('offer_id', UUID(as_uuid=True),
                  sa.ForeignKey('offers.id'), nullable=False),
        sa.Column('data', JSONB, nullable=False, server_default='{}'),
        sa.Column('normalisation_version', sa.String(50),
                  nullable=False, server_default='v3.3.2'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # ── TABLE : scores ─────────────────────────────────────────────
    # Scores Couche A uniquement — non modifiables par Couche B
    # (Constitution V3.3.2 §7 + ADR-0003 §3.1)
    op.create_table(
        'scores',
        sa.Column('id', UUID(as_uuid=True), primary_key=True,
                  default=uuid.uuid4),
        sa.Column('offer_id', UUID(as_uuid=True),
                  sa.ForeignKey('offers.id'), nullable=False),
        sa.Column('essentials', sa.Numeric(5, 2), nullable=False,
                  server_default='0'),
        sa.Column('capacity', sa.Numeric(5, 2), nullable=False,
                  server_default='0'),
        sa.Column('commercial', sa.Numeric(5, 2), nullable=False,
                  server_default='0'),
        sa.Column('sustainability', sa.Numeric(5, 2), nullable=False,
                  server_default='0'),
        sa.Column('total', sa.Numeric(5, 2), nullable=False,
                  server_default='0'),
        sa.Column('computed_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('constitution_version', sa.String(50),
                  nullable=False, server_default='v3.3.2'),
    )

    # ── TABLE : market_data ────────────────────────────────────────
    # Couche B — append-only (Invariant 9 Constitution V3.3.2)
    # Aucune UPDATE ni DELETE autorisée sur cette table
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
                  sa.ForeignKey('suppliers.id'), nullable=True),
        sa.Column('observed_at', sa.DateTime(timezone=True),
                  nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # ── INDEX ──────────────────────────────────────────────────────
    op.create_index('ix_offers_process_id', 'offers', ['process_id'])
    op.create_index('ix_scores_offer_id', 'scores', ['offer_id'])
    op.create_index('ix_market_data_item', 'market_data',
                    ['item_canonical', 'family'])
    op.create_index('ix_dictionary_family', 'dictionary', ['family'])


def downgrade() -> None:
    op.drop_index('ix_dictionary_family', 'dictionary')
    op.drop_index('ix_market_data_item', 'market_data')
    op.drop_index('ix_scores_offer_id', 'scores')
    op.drop_index('ix_offers_process_id', 'offers')
    op.drop_table('market_data')
    op.drop_table('scores')
    op.drop_table('structured_data')
    op.drop_table('offers')
    op.drop_table('dictionary')
    op.drop_table('suppliers')
