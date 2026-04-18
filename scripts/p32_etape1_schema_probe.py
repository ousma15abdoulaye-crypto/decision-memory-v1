"""P3.2 ÉTAPE 1 — Probe schéma (Python wrapper)

Exécute les 5 probes SQL schéma et formate output.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg
from psycopg.rows import dict_row


def get_db_url() -> str:
    import os
    from dotenv import load_dotenv

    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not found")
    if db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
    return db_url


def probe_schema():
    """Execute schema probes."""
    db_url = get_db_url()

    print("=" * 80)
    print("P3.2 ÉTAPE 1 — PROBE SCHÉMA")
    print("=" * 80)
    print()

    with psycopg.connect(db_url, row_factory=dict_row) as conn:

        # PROBE 1.1 : is_active existe ?
        print("PROBE 1.1 — Colonne process_workspaces.is_active")
        print("-" * 80)

        cursor = conn.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'process_workspaces'
              AND column_name = 'is_active';
        """)
        rows = cursor.fetchall()

        if not rows:
            print("⚠️  COLONNE ABSENTE — doit être créée avant soft-delete")
        else:
            row = rows[0]
            print(f"✅ Colonne existe")
            print(f"   Type: {row['data_type']}")
            print(f"   Nullable: {row['is_nullable']}")
            print(f"   Default: {row['column_default']}")

        print()
        print()

        # PROBE 1.2 : tables avec workspace_id
        print("PROBE 1.2 — Tables avec colonne workspace_id")
        print("-" * 80)

        cursor = conn.execute("""
            SELECT
                t.table_name,
                c.column_name,
                c.data_type,
                c.is_nullable
            FROM information_schema.tables t
            JOIN information_schema.columns c ON t.table_name = c.table_name
            WHERE t.table_schema = 'public'
              AND c.column_name = 'workspace_id'
              AND t.table_type = 'BASE TABLE'
            ORDER BY t.table_name;
        """)
        rows = cursor.fetchall()

        if not rows:
            print("⚠️  Aucune table avec workspace_id trouvée")
        else:
            print(f"✅ {len(rows)} tables avec workspace_id")
            print()
            for row in rows:
                nullable = "NULL" if row['is_nullable'] == 'YES' else "NOT NULL"
                print(f"  {row['table_name']:<40} | {row['data_type']:<15} | {nullable}")

        print()
        print()

        # PROBE 1.3 : tables spécifiques CTO
        print("PROBE 1.3 — Tables listées par CTO (existence)")
        print("-" * 80)

        cursor = conn.execute("""
            WITH tables_to_check AS (
                SELECT unnest(ARRAY[
                    'process_runs',
                    'procurement_documents',
                    'vendor_offers',
                    'evaluation_documents',
                    'criterion_assessments',
                    'bundle_documents',
                    'dao_criteria'
                ]) AS table_name
            )
            SELECT
                tc.table_name,
                CASE
                    WHEN t.table_name IS NOT NULL THEN 'EXISTS'
                    ELSE 'MISSING'
                END AS status,
                c.column_name AS workspace_column
            FROM tables_to_check tc
            LEFT JOIN information_schema.tables t
                ON tc.table_name = t.table_name
                AND t.table_schema = 'public'
            LEFT JOIN information_schema.columns c
                ON t.table_name = c.table_name
                AND c.column_name = 'workspace_id'
            ORDER BY tc.table_name;
        """)
        rows = cursor.fetchall()

        print()
        for row in rows:
            status = row['status']
            ws_col = row['workspace_column'] or "NO_COLUMN"
            icon = "✅" if status == 'EXISTS' and ws_col == 'workspace_id' else "⚠️"
            print(f"  {icon} {row['table_name']:<30} | {status:<10} | {ws_col}")

        print()
        print()

        # PROBE 1.4 : Foreign keys CASCADE
        print("PROBE 1.4 — Foreign keys workspace_id → process_workspaces")
        print("-" * 80)

        cursor = conn.execute("""
            SELECT
                tc.table_name,
                tc.constraint_name,
                rc.delete_rule,
                rc.update_rule
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
            JOIN information_schema.referential_constraints rc
                ON tc.constraint_name = rc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND ccu.table_name = 'process_workspaces'
              AND kcu.column_name = 'workspace_id'
              AND tc.table_schema = 'public'
            ORDER BY tc.table_name;
        """)
        rows = cursor.fetchall()

        if not rows:
            print("⚠️  Aucun FK workspace_id trouvé")
        else:
            print(f"✅ {len(rows)} foreign keys")
            print()
            for row in rows:
                print(f"  {row['table_name']:<30} | DELETE: {row['delete_rule']:<15} | UPDATE: {row['update_rule']}")

        print()
        print()

        # PROBE 1.5 : Schéma complet process_workspaces
        print("PROBE 1.5 — Colonnes process_workspaces (schéma complet)")
        print("-" * 80)

        cursor = conn.execute("""
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'process_workspaces'
            ORDER BY ordinal_position;
        """)
        rows = cursor.fetchall()

        print(f"✅ {len(rows)} colonnes")
        print()
        for row in rows:
            nullable = "NULL" if row['is_nullable'] == 'YES' else "NOT NULL"
            default = row['column_default'] or "-"
            print(f"  {row['column_name']:<35} | {row['data_type']:<15} | {nullable:<10} | {default[:30]}")

    print()
    print("=" * 80)
    print("PROBE SCHÉMA TERMINÉ")
    print("=" * 80)


if __name__ == "__main__":
    try:
        probe_schema()
    except Exception as e:
        print(f"❌ ERREUR : {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
