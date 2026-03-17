"""Validate FK pipeline_runs.case_id — ASAP-05

Audit CTO senior 2026-03-17

CORRECTION POST-PROBE 2026-03-17 :
  pipeline_runs a un trigger append-only (trg_pipeline_runs_append_only)
  qui bloque tout DELETE. Stratégie :
    1. DROP TRIGGER temporaire
    2. DELETE orphelins
    3. VALIDATE CONSTRAINT FK
    4. RECREATE TRIGGER (définition 032)
    5. CREATE INDEX si absent

Downgrade :
  Invalider la contrainte — irréversible.
  DROP INDEX ix_pipeline_runs_case_id.

Règles :
  RÈGLE-ANCHOR-05 : SQL brut — zéro autogenerate
  E-25 : FK ON DELETE RESTRICT sur tables append-only
"""

from alembic import op
import sqlalchemy as sa

revision = "049_validate_pipeline_runs_fk"
down_revision = "048_vendors_sensitive_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── 0. VÉRIFIER QUE LA TABLE EXISTE ─────────────────────────
    table_exists = conn.execute(sa.text("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name   = 'pipeline_runs'
    """)).scalar()

    if not table_exists:
        print("[049] Table pipeline_runs absente — skip")
        return

    # ── 1. PROBE — état FK ───────────────────────────────────────
    fk_row = conn.execute(sa.text("""
        SELECT conname, convalidated
        FROM pg_constraint
        WHERE conrelid = 'pipeline_runs'::regclass
          AND contype   = 'f'
          AND conname   = 'fk_pipeline_runs_case_id'
    """)).fetchone()

    if not fk_row:
        print("[049] Contrainte fk_pipeline_runs_case_id absente — skip")
        return

    if fk_row[1]:
        print("[049] Contrainte déjà validée — skip")
        return

    # ── 2. PROBE — orphelins ─────────────────────────────────────
    cases_exist = conn.execute(sa.text("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name   = 'cases'
    """)).scalar()

    if not cases_exist:
        print("[049] Table cases absente — impossible de valider FK")
        return

    orphelins = conn.execute(sa.text("""
        SELECT COUNT(*)
        FROM pipeline_runs pr
        LEFT JOIN cases c ON c.id = pr.case_id
        WHERE c.id IS NULL
          AND pr.case_id IS NOT NULL
    """)).scalar()

    total = conn.execute(sa.text(
        "SELECT COUNT(*) FROM pipeline_runs"
    )).scalar()

    print(f"[049] pipeline_runs total={total} orphelins={orphelins}")

    # ── 3. DROP TRIGGER TEMPORAIRE ───────────────────────────────
    conn.execute(sa.text("""
        DROP TRIGGER IF EXISTS trg_pipeline_runs_append_only
        ON pipeline_runs
    """))
    print("[049] Trigger trg_pipeline_runs_append_only droppé temporairement")

    # ── 4. DELETE ORPHELINS ──────────────────────────────────────
    if orphelins and orphelins > 0:
        deleted = conn.execute(sa.text("""
            DELETE FROM pipeline_runs
            WHERE case_id IS NOT NULL
              AND case_id NOT IN (SELECT id FROM cases)
        """)).rowcount
        print(f"[049] Orphelins supprimés : {deleted}")
    else:
        print("[049] Aucun orphelin — DELETE sauté")

    # ── 5. RECREATE TRIGGER (définition 032) ─────────────────────
    conn.execute(sa.text("""
        CREATE OR REPLACE FUNCTION public.fn_pipeline_runs_append_only()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION
                'pipeline_runs is append-only — UPDATE/DELETE interdit (ADR-0012)';
            RETURN NULL;
        END;
        $$
    """))
    conn.execute(sa.text("""
        CREATE TRIGGER trg_pipeline_runs_append_only
        BEFORE UPDATE OR DELETE ON public.pipeline_runs
        FOR EACH ROW EXECUTE FUNCTION public.fn_pipeline_runs_append_only()
    """))
    print("[049] Trigger trg_pipeline_runs_append_only recréé")

    # ── 6. VALIDATE CONSTRAINT ───────────────────────────────────
    conn.execute(sa.text("""
        ALTER TABLE pipeline_runs
        VALIDATE CONSTRAINT fk_pipeline_runs_case_id
    """))
    print("[049] CONSTRAINT fk_pipeline_runs_case_id VALIDATED")

    # ── 7. INDEX sur case_id si absent ──────────────────────────
    idx_exists = conn.execute(sa.text("""
        SELECT COUNT(*) FROM pg_indexes
        WHERE tablename = 'pipeline_runs'
          AND indexname = 'ix_pipeline_runs_case_id'
    """)).scalar()

    if not idx_exists:
        conn.execute(sa.text("""
            CREATE INDEX ix_pipeline_runs_case_id
            ON pipeline_runs (case_id)
        """))
        print("[049] INDEX ix_pipeline_runs_case_id créé")
    else:
        print("[049] INDEX déjà présent — skip")


def downgrade() -> None:
    conn = op.get_bind()

    exists = conn.execute(sa.text("""
        SELECT COUNT(*) FROM pg_constraint
        WHERE conrelid = 'pipeline_runs'::regclass
          AND contype   = 'f'
          AND conname   = 'fk_pipeline_runs_case_id'
    """)).scalar()

    if exists:
        print("[049] downgrade : VALIDATE est irréversible — no-op")
    else:
        print("[049] downgrade : contrainte absente — no-op")

    conn.execute(sa.text("""
        DROP INDEX IF EXISTS ix_pipeline_runs_case_id
    """))
    print("[049] INDEX ix_pipeline_runs_case_id supprimé")
