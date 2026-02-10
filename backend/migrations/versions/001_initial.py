"""Initial schema – all tables.

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- Couche A tables --
    op.create_table(
        "cases",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("reference", sa.String(50), unique=True, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("buyer_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_cases_reference", "cases", ["reference"])
    op.create_index("ix_cases_buyer_name", "cases", ["buyer_name"])
    op.create_index("ix_cases_status", "cases", ["status"])

    op.create_table(
        "lots",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("case_id", sa.String(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_lots_case_id", "lots", ["case_id"])

    op.create_table(
        "submissions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("case_id", sa.String(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("lot_id", sa.String(), sa.ForeignKey("lots.id"), nullable=False),
        sa.Column("vendor_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), server_default="received", nullable=False),
        sa.Column("declared_type", sa.String(30), nullable=True),
        sa.Column("channel", sa.String(30), server_default="upload", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_submissions_case_id", "submissions", ["case_id"])
    op.create_index("ix_submissions_lot_id", "submissions", ["lot_id"])
    op.create_index("ix_submissions_vendor_name", "submissions", ["vendor_name"])
    op.create_index("ix_submissions_status", "submissions", ["status"])
    op.create_index("ix_submissions_case_lot", "submissions", ["case_id", "lot_id"])

    op.create_table(
        "submission_documents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("submission_id", sa.String(), sa.ForeignKey("submissions.id"), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=True),
        sa.Column("file_size", sa.Integer(), server_default="0", nullable=False),
        sa.Column("doc_type", sa.String(30), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_submission_documents_submission_id", "submission_documents", ["submission_id"])

    op.create_table(
        "preanalysis_results",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("submission_id", sa.String(), sa.ForeignKey("submissions.id"), nullable=False),
        sa.Column("document_id", sa.String(), sa.ForeignKey("submission_documents.id"), nullable=True),
        sa.Column("vendor_name", sa.String(255), nullable=True),
        sa.Column("submission_date", sa.String(30), nullable=True),
        sa.Column("amount", sa.String(50), nullable=True),
        sa.Column("detected_type", sa.String(30), nullable=True),
        sa.Column("doc_checklist", sa.JSON(), nullable=True),
        sa.Column("flags", sa.JSON(), nullable=True),
        sa.Column("llm_used", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_preanalysis_results_submission_id", "preanalysis_results", ["submission_id"])

    op.create_table(
        "cba_exports",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("case_id", sa.String(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("lot_id", sa.String(), sa.ForeignKey("lots.id"), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_cba_exports_case_id", "cba_exports", ["case_id"])
    op.create_index("ix_cba_exports_lot_id", "cba_exports", ["lot_id"])

    op.create_table(
        "minutes_pv",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("case_id", sa.String(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("lot_id", sa.String(), sa.ForeignKey("lots.id"), nullable=False),
        sa.Column("pv_type", sa.Enum("opening", "analysis", name="pvtype"), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_minutes_pv_case_id", "minutes_pv", ["case_id"])
    op.create_index("ix_minutes_pv_lot_id", "minutes_pv", ["lot_id"])

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("status", sa.Enum("pending", "delivered", "failed", name="outboxstatus"), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_outbox_events_event_type", "outbox_events", ["event_type"])
    op.create_index("ix_outbox_events_status", "outbox_events", ["status"])

    # -- Couche B tables --
    op.create_table(
        "vendors",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("canonical_name", sa.String(255), unique=True, nullable=False),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_vendors_canonical_name", "vendors", ["canonical_name"])

    op.create_table(
        "vendor_aliases",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("vendor_id", sa.String(), sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("alias", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_vendor_aliases_vendor_id", "vendor_aliases", ["vendor_id"])
    op.create_index("ix_vendor_aliases_alias", "vendor_aliases", ["alias"])

    op.create_table(
        "vendor_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("vendor_id", sa.String(), sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_vendor_events_vendor_id", "vendor_events", ["vendor_id"])
    op.create_index("ix_vendor_events_event_type", "vendor_events", ["event_type"])

    op.create_table(
        "units",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_units_code", "units", ["code"])

    op.create_table(
        "unit_aliases",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("unit_id", sa.String(), sa.ForeignKey("units.id"), nullable=False),
        sa.Column("alias", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_unit_aliases_unit_id", "unit_aliases", ["unit_id"])
    op.create_index("ix_unit_aliases_alias", "unit_aliases", ["alias"])

    op.create_table(
        "items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("canonical_name", sa.String(255), unique=True, nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("unit_id", sa.String(), sa.ForeignKey("units.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_items_canonical_name", "items", ["canonical_name"])
    op.create_index("ix_items_category", "items", ["category"])

    op.create_table(
        "item_aliases",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("item_id", sa.String(), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("alias", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_item_aliases_item_id", "item_aliases", ["item_id"])
    op.create_index("ix_item_aliases_alias", "item_aliases", ["alias"])

    op.create_table(
        "geo_master",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("geo_type", sa.Enum("country", "region", "city", name="geotype"), nullable=False),
        sa.Column("parent_id", sa.String(), sa.ForeignKey("geo_master.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_geo_master_name", "geo_master", ["name"])
    op.create_index("ix_geo_master_geo_type", "geo_master", ["geo_type"])
    op.create_index("ix_geo_master_parent_id", "geo_master", ["parent_id"])

    op.create_table(
        "geo_aliases",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("geo_id", sa.String(), sa.ForeignKey("geo_master.id"), nullable=False),
        sa.Column("alias", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_geo_aliases_geo_id", "geo_aliases", ["geo_id"])
    op.create_index("ix_geo_aliases_alias", "geo_aliases", ["alias"])

    op.create_table(
        "market_signals",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("item_id", sa.String(), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("vendor_id", sa.String(), sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("geo_id", sa.String(), sa.ForeignKey("geo_master.id"), nullable=True),
        sa.Column("unit_id", sa.String(), sa.ForeignKey("units.id"), nullable=True),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(10), server_default="XOF", nullable=False),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("signal_date", sa.String(30), nullable=True),
        sa.Column("source", sa.String(255), nullable=True),
        sa.Column("case_reference", sa.String(100), nullable=True),
        sa.Column("superseded_by", sa.String(), sa.ForeignKey("market_signals.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_market_signals_item_id", "market_signals", ["item_id"])
    op.create_index("ix_market_signals_vendor_id", "market_signals", ["vendor_id"])
    op.create_index("ix_market_signals_geo_id", "market_signals", ["geo_id"])
    op.create_index("ix_market_signals_case_reference", "market_signals", ["case_reference"])
    op.create_index("ix_market_signals_item_geo", "market_signals", ["item_id", "geo_id"])
    op.create_index("ix_market_signals_vendor_item", "market_signals", ["vendor_id", "item_id"])


def downgrade() -> None:
    op.drop_table("market_signals")
    op.drop_table("geo_aliases")
    op.drop_table("geo_master")
    op.drop_table("item_aliases")
    op.drop_table("items")
    op.drop_table("unit_aliases")
    op.drop_table("units")
    op.drop_table("vendor_events")
    op.drop_table("vendor_aliases")
    op.drop_table("vendors")
    op.drop_table("outbox_events")
    op.drop_table("minutes_pv")
    op.drop_table("cba_exports")
    op.drop_table("preanalysis_results")
    op.drop_table("submission_documents")
    op.drop_table("submissions")
    op.drop_table("lots")
    op.drop_table("cases")
