"""Row-Level Security policies — multi-tenant isolation.

Migration 051 — Multi-tenant hardening.

Adds RLS policies to ALL tables that carry an ``org_id`` column.
Each policy restricts rows to those matching the session variable
``app.org_id`` (set by TenantContextMiddleware or explicitly via
``SET LOCAL app.org_id = ...``).

Strategy:
  1. ENABLE ROW LEVEL SECURITY on each table.
  2. CREATE POLICY restricting SELECT / INSERT / UPDATE / DELETE.
  3. Table owner (the migration role) bypasses RLS by default.
     FORCE ROW LEVEL SECURITY is NOT enabled yet — it will be
     enabled in a follow-up migration once all code paths set
     ``app.org_id``.

Tables affected (those already having org_id):
  - criteria
  - committees
  - market_surveys
  - price_anomaly_alerts
  - survey_campaigns
  - survey_campaign_items
  - survey_campaign_zones
  - decision_history

Downgrade: drops policies and disables RLS.

Règles :
  RÈGLE-ANCHOR-05 : SQL brut — zéro autogenerate
  RÈGLE-ANCHOR-08 : périmètre fermé
"""

import sqlalchemy as sa

from alembic import op

revision = "051_rls_tenant_isolation"
down_revision = "050_documents_sha256_not_null"
branch_labels = None
depends_on = None

# Tables that already have an org_id column.
_RLS_TABLES = [
    "criteria",
    "committees",
    "market_surveys",
    "price_anomaly_alerts",
    "survey_campaigns",
    "survey_campaign_items",
    "survey_campaign_zones",
    "decision_history",
]


def _table_exists(conn, table_name: str) -> bool:
    result = conn.execute(
        sa.text("SELECT to_regclass(:tbl) IS NOT NULL AS ok"),
        {"tbl": f"public.{table_name}"},
    )
    row = result.fetchone()
    return bool(row and row[0])


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "  AND table_name = :tbl "
            "  AND column_name = :col"
        ),
        {"tbl": table_name, "col": column_name},
    )
    row = result.fetchone()
    return bool(row and row[0] > 0)


def upgrade() -> None:
    conn = op.get_bind()

    for table in _RLS_TABLES:
        if not _table_exists(conn, table):
            continue
        if not _column_exists(conn, table, "org_id"):
            continue

        policy_name = f"rls_tenant_{table}"

        # 1. Enable RLS (idempotent — safe to call multiple times)
        conn.execute(sa.text(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY"))

        # 2. Drop existing policy if present (idempotent re-runs)
        conn.execute(sa.text(f"DROP POLICY IF EXISTS {policy_name} ON public.{table}"))

        # 3. Create restrictive policy.
        # current_setting('app.org_id', true) returns '' if not set.
        # The policy allows access when:
        #   a) app.org_id matches the row's org_id, OR
        #   b) app.org_id is not set (empty string) — TEMPORARY
        #      permissive fallback for backward compatibility.
        #
        # ⚠️  SECURITY DEBT: The OR clause below allows unscoped access
        #     when no tenant context is set.  This MUST be removed in a
        #     follow-up migration that:
        #       1. Verifies ALL code paths call set_tenant_context()
        #       2. Enables FORCE ROW LEVEL SECURITY on each table
        #       3. Removes the "OR ... = ''" fallback
        #     Until then, RLS acts as a safety net (not the sole barrier).
        conn.execute(
            sa.text(
                f"CREATE POLICY {policy_name} ON public.{table} "
                f"USING ("
                f"  org_id = current_setting('app.org_id', true) "
                f"  OR current_setting('app.org_id', true) = ''"
                f") "
                f"WITH CHECK ("
                f"  org_id = current_setting('app.org_id', true) "
                f"  OR current_setting('app.org_id', true) = ''"
                f")"
            )
        )


def downgrade() -> None:
    conn = op.get_bind()

    for table in _RLS_TABLES:
        if not _table_exists(conn, table):
            continue

        policy_name = f"rls_tenant_{table}"

        conn.execute(sa.text(f"DROP POLICY IF EXISTS {policy_name} ON public.{table}"))
        conn.execute(sa.text(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY"))
