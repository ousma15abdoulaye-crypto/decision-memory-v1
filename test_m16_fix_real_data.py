"""Test fix M16 bridge avec données réelles.

Ce script va :
1. Re-exécuter le bridge M14→M16 sur le workspace existant
2. Vérifier que des assessments sont créés (>0)
3. Afficher statistiques détaillées
"""

import os
import sys

# Config environment
os.environ["DATABASE_URL"] = "postgresql://postgres:TgXhYlTiLLLzmUldbWFnSjTQxgCMxWqB@junction.proxy.rlwy.net:47188/railway"
os.environ["JWT_SECRET"] = "dev-local-secret-key-minimum-32-characters-long"

from src.services.m14_bridge import populate_assessments_from_m14
from src.db import get_connection, db_execute_one, db_fetchall

# Workspace de test (métriques pipeline_v5_real_metrics.json)
WORKSPACE_ID = "f1a6edfb-ac50-4301-a1a9-7a80053c632a"

def main():
    print("=" * 70)
    print("TEST FIX M16 BRIDGE - DONNEES REELLES")
    print("=" * 70)
    print()

    # 1. Vérifier état AVANT
    print("[1/4] Verification etat AVANT fix...")
    with get_connection() as conn:
        before = db_execute_one(
            conn,
            "SELECT COUNT(*)::int AS n FROM criterion_assessments WHERE workspace_id = CAST(%s AS uuid)",
            (WORKSPACE_ID,),
        )
        before_count = before["n"] if before else 0

        # Vérifier eval_doc
        ed = db_execute_one(
            conn,
            "SELECT id::text, scores_matrix FROM evaluation_documents WHERE workspace_id = CAST(%s AS uuid) ORDER BY created_at DESC LIMIT 1",
            (WORKSPACE_ID,),
        )
        if ed:
            print(f"  - evaluation_document: {ed['id']}")
            sm = ed.get("scores_matrix")
            if isinstance(sm, dict):
                bundle_count = len(sm)
                total_criteria = sum(len(v) if isinstance(v, dict) else 0 for v in sm.values())
                print(f"  - scores_matrix: {bundle_count} bundles, {total_criteria} criteres")
            else:
                print(f"  - scores_matrix: type={type(sm)} (NOT A DICT!)")
        else:
            print("  - evaluation_document: NOT FOUND")
            sys.exit(1)

        # Bundles
        bundles = db_fetchall(
            conn,
            "SELECT id::text FROM supplier_bundles WHERE workspace_id = CAST(%s AS uuid)",
            (WORKSPACE_ID,),
        )
        print(f"  - supplier_bundles: {len(bundles)}")

        # DAO criteria
        criteria = db_fetchall(
            conn,
            "SELECT id::text FROM dao_criteria WHERE workspace_id = CAST(%s AS uuid)",
            (WORKSPACE_ID,),
        )
        print(f"  - dao_criteria: {len(criteria)}")

        print(f"  - assessments AVANT: {before_count}")

    print()

    # 2. Exécuter bridge M14→M16
    print("[2/4] Execution bridge M14->M16...")
    try:
        result = populate_assessments_from_m14(WORKSPACE_ID)
        print(f"  - created: {result.created}")
        print(f"  - updated: {result.updated}")
        print(f"  - skipped: {result.skipped}")
        print(f"  - unmapped_bundles: {result.unmapped_bundles}")
        print(f"  - unmapped_criteria: {result.unmapped_criteria}")
        if result.errors:
            print(f"  - errors: {result.errors[:3]}")
    except Exception as exc:
        print(f"  [ERROR] {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print()

    # 3. Vérifier état APRÈS
    print("[3/4] Verification etat APRES fix...")
    with get_connection() as conn:
        after = db_execute_one(
            conn,
            "SELECT COUNT(*)::int AS n FROM criterion_assessments WHERE workspace_id = CAST(%s AS uuid)",
            (WORKSPACE_ID,),
        )
        after_count = after["n"] if after else 0
        print(f"  - assessments APRES: {after_count}")
        print(f"  - delta: +{after_count - before_count}")

        # Sample assessments
        if after_count > 0:
            samples = db_fetchall(
                conn,
                """
                SELECT bundle_id::text, criterion_key, cell_json->>'score' AS score,
                       cell_json->>'confidence' AS conf, cell_json->>'source' AS src
                FROM criterion_assessments
                WHERE workspace_id = CAST(%s AS uuid)
                LIMIT 5
                """,
                (WORKSPACE_ID,),
            )
            print(f"\n  Sample assessments ({len(samples)} premiers):")
            for s in samples:
                print(f"    - bundle={s['bundle_id'][:8]}... crit={s['criterion_key'][:30]} score={s['score']} conf={s['conf']} src={s['src']}")

    print()

    # 4. Validation
    print("[4/4] Validation...")
    success = result.created + result.updated > 0
    if success:
        print("  [SUCCESS] M16 bridge FONCTIONNE")
        print(f"  [SUCCESS] {result.created + result.updated} assessments crees/updates")
        return 0
    else:
        print("  [FAIL] Aucun assessment cree")
        if result.unmapped_bundles:
            print(f"  [DEBUG] unmapped_bundles: {result.unmapped_bundles}")
        if result.unmapped_criteria:
            print(f"  [DEBUG] unmapped_criteria (premiers 10): {result.unmapped_criteria[:10]}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
