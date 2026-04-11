"""095 — DEFAULT tenant_id (offers, extractions, analysis_summaries, mercuriale).

La migration 094 impose NOT NULL ; les fixtures de tests omettent souvent
``tenant_id``. DEFAULT stable via ``dms_default_tenant_id()`` (sci_mali ou
premier tenant par code) restaure la compatibilité CI.

Revision ID: 095_tenant_id_default_offers_extractions
Revises: 094_security_market_mercurial_tenant_rls
"""

from __future__ import annotations

from alembic import op

revision = "095_tenant_id_default_offers_extractions"
down_revision = "094_security_market_mercurial_tenant_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION public.dms_default_tenant_id()
        RETURNS uuid
        LANGUAGE sql
        STABLE
        AS $f$
            SELECT COALESCE(
                (SELECT id FROM public.tenants WHERE code = 'sci_mali' LIMIT 1),
                (SELECT id FROM public.tenants ORDER BY code LIMIT 1)
            );
        $f$;
    """)
    for tbl in (
        "offers",
        "extractions",
        "analysis_summaries",
        "mercuriale_sources",
        "mercurials",
    ):
        op.execute(f"""
            ALTER TABLE public.{tbl}
            ALTER COLUMN tenant_id
            SET DEFAULT (public.dms_default_tenant_id());
        """)


def downgrade() -> None:
    for tbl in (
        "mercurials",
        "mercuriale_sources",
        "analysis_summaries",
        "extractions",
        "offers",
    ):
        op.execute(f"ALTER TABLE public.{tbl} ALTER COLUMN tenant_id DROP DEFAULT;")
    op.execute("DROP FUNCTION IF EXISTS public.dms_default_tenant_id();")
