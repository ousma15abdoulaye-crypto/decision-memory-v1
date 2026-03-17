"""Backfill + NOT NULL documents.sha256 — ASAP-06

Audit CTO senior 2026-03-17

CORRECTION POST-PROBE 2026-03-17 :
  documents n'a pas de colonne content_hash.
  Backfill sur id + case_id + filename + uploaded_at.
  pgcrypto vérifié dynamiquement — fallback md5 si absent.

Stratégie backfill :
  1. Vérifier pgcrypto disponible
  2. Si oui : digest(id||case_id||filename||uploaded_at, 'sha256')
  3. Si non : 'backfill_' || md5(id||filename)
  4. Vérifier 0 NULL résiduel
  5. ALTER SET NOT NULL

Downgrade : DROP NOT NULL uniquement.

Règles :
  RÈGLE-ANCHOR-05 : SQL brut — zéro autogenerate
  RÈGLE-ANCHOR-08 : périmètre fermé
"""

import sqlalchemy as sa

from alembic import op

revision = "050_documents_sha256_not_null"
down_revision = "049_validate_pipeline_runs_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── 0. TABLE EXISTE ? ────────────────────────────────────────
    table_exists = conn.execute(sa.text("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name   = 'documents'
    """)).scalar()

    if not table_exists:
        print("[050] Table documents absente — skip")
        return

    # ── 1. COLONNE sha256 EXISTE ? ───────────────────────────────
    col_exists = conn.execute(sa.text("""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_name  = 'documents'
          AND column_name = 'sha256'
    """)).scalar()

    if not col_exists:
        print("[050] Colonne sha256 absente — skip")
        return

    # ── 2. DÉJÀ NOT NULL ? ──────────────────────────────────────
    is_nullable = conn.execute(sa.text("""
        SELECT is_nullable FROM information_schema.columns
        WHERE table_name  = 'documents'
          AND column_name = 'sha256'
    """)).scalar()

    if is_nullable == "NO":
        print("[050] sha256 déjà NOT NULL — skip")
        return

    # ── 3. PROBE ÉTAT ────────────────────────────────────────────
    total = conn.execute(sa.text("SELECT COUNT(*) FROM documents")).scalar()
    nulls = conn.execute(
        sa.text("SELECT COUNT(*) FROM documents WHERE sha256 IS NULL")
    ).scalar()
    print(f"[050] documents total={total} sha256_null={nulls}")

    # ── 4. VÉRIFIER PGCRYPTO ────────────────────────────────────
    pgcrypto_ok = False
    try:
        conn.execute(sa.text("SELECT encode(digest('probe', 'sha256'), 'hex')"))
        pgcrypto_ok = True
        print("[050] pgcrypto disponible")
    except Exception:
        print("[050] pgcrypto absent — fallback md5")

    # ── 5. IDENTIFIER COLONNES DISPONIBLES ──────────────────────
    cols = conn.execute(sa.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'documents'
          AND column_name IN (
              'id', 'case_id', 'filename', 'uploaded_at',
              'created_at', 'path'
          )
        ORDER BY column_name
    """)).fetchall()
    available = [r[0] for r in cols]
    print(f"[050] Colonnes disponibles : {available}")

    parts = []
    for col in ["id", "case_id", "filename", "uploaded_at", "created_at", "path"]:
        if col in available:
            parts.append(f"COALESCE({col}::text, '')")
    concat_expr = " || '|' || ".join(parts) if parts else "'unknown'"

    # ── 6. BACKFILL ──────────────────────────────────────────────
    if nulls > 0:
        if pgcrypto_ok:
            sql = f"""
                UPDATE documents
                SET sha256 = encode(
                    digest({concat_expr}, 'sha256'),
                    'hex'
                )
                WHERE sha256 IS NULL
            """
        else:
            sql = f"""
                UPDATE documents
                SET sha256 = 'backfill_' || md5({concat_expr})
                WHERE sha256 IS NULL
            """

        conn.execute(sa.text(sql))
        print(f"[050] Backfill : {nulls} lignes mises à jour")

        # ── 7. VÉRIFICATION ZÉRO NULL ───────────────────────────
        final_nulls = conn.execute(
            sa.text("SELECT COUNT(*) FROM documents WHERE sha256 IS NULL")
        ).scalar()

        if final_nulls > 0:
            raise RuntimeError(
                f"[050] ÉCHEC : {final_nulls} NULL résiduels. "
                "Migration annulée — rollback déclenché."
            )
        print("[050] Backfill complet — 0 NULL résiduel")
    else:
        print("[050] Aucun NULL — backfill inutile")

    # ── 8. SET NOT NULL (REPORTÉ) ───────────────────────────────
    # IMPORTANT :
    #   Le passage en NOT NULL est reporté tant que tous les
    #   chemins d'écriture applicatifs ne renseignent pas sha256.
    #   Voir règle Copilot Code Review : risque d'échecs d'INSERT.
    print("[050] NOTE : documents.sha256 reste NULLABLE — NOT NULL reporté")


def downgrade() -> None:
    conn = op.get_bind()

    col_exists = conn.execute(sa.text("""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_name  = 'documents'
          AND column_name = 'sha256'
    """)).scalar()

    if col_exists:
        conn.execute(sa.text("""
            ALTER TABLE documents
            ALTER COLUMN sha256 DROP NOT NULL
        """))
        print("[050] sha256 DROP NOT NULL")
    else:
        print("[050] Colonne absente — no-op")
