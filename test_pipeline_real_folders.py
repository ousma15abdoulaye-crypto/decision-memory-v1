"""Test Pipeline V5 avec 3 dossiers reels -- Metrics mesurables.

DOSSIERS:
1. GCF -- 20 documents Solution & One (attestations, contrats)
2. PADEM -- 4 offres (IEF SARL, ABESSAME, CRDDD, + docs)
3. TEST -- Mercuriale prix 2023 (16 bulletins regionaux)

METRICS:
- Duration extraction (par dossier)
- Nb offres extraites vs documents
- Framework detected (DGMP/SCI/UNKNOWN)
- Procedure type resolu
- M14 scores_matrix populated
- M16 assessments created
"""
import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Setup
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/dms")
os.environ.setdefault("MISTRAL_API_KEY", "fake-key-for-test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-minimum-32-chars-long")

from src.services.pipeline_v5_service import run_pipeline_v5

DOSSIERS = {
    "GCF": {
        "path": "data/imports/annotation/SUPPLIERS BUNDLE TEST OFFRES COMPLETE/GCF",
        "description": "Solution & One -- Offre GCF (2024)",
        "expected_docs": 20,
        "expected_framework": "SCI",
    },
    "PADEM": {
        "path": "data/imports/annotation/SUPPLIERS BUNDLE TEST OFFRES COMPLETE/PADEM",
        "description": "PADEM -- Enquete de base (IEF, ABESSAME, CRDDD)",
        "expected_docs": 30,
        "expected_framework": "SCI",
    },
    "TEST_MERCURIALE": {
        "path": "data/imports/annotation/SUPPLIERS BUNDLE TEST OFFRES COMPLETE/TEST/Mercurial",
        "description": "Mercuriale prix Mali 2023 (16 regions)",
        "expected_docs": 16,
        "expected_framework": "DGMP_MALI",
    },
}


def count_files_recursive(folder_path: str) -> int:
    """Compte fichiers PDF/DOCX dans dossier."""
    if not Path(folder_path).exists():
        return 0
    count = 0
    for root, dirs, files in os.walk(folder_path):
        for f in files:
            if f.lower().endswith(('.pdf', '.docx', '.doc')):
                count += 1
    return count


def test_dossier(
    dossier_name: str,
    config: dict,
    workspace_id: str | None = None,
) -> dict:
    """Test Pipeline V5 sur un dossier réel — Retourne metrics."""
    print(f"\n{'='*80}")
    print(f"TEST DOSSIER: {dossier_name}")
    print(f"Description: {config['description']}")
    print(f"{'='*80}")

    # Step 1: Compter documents
    folder_path = config["path"]
    doc_count = count_files_recursive(folder_path)
    print(f"\n[1/5] Documents trouves: {doc_count} (attendu: {config['expected_docs']})")

    if doc_count == 0:
        print(f"[SKIP] Aucun document dans {folder_path}")
        return {
            "dossier": dossier_name,
            "status": "SKIPPED",
            "reason": "no_documents",
            "doc_count": 0,
        }

    # Step 2: Upload documents -> workspace (MOCK -- en reel via API)
    print(f"\n[2/5] Upload documents -> workspace...")
    print(f"[MOCK] En production: POST /workspaces/{workspace_id}/upload-zip")

    # Step 3: Run Pipeline V5 (MOCK -- workspace doit exister)
    if not workspace_id:
        print(f"[MOCK] Pas de workspace_id fourni")
        print(f"En production: creer workspace + upload ZIP + run pipeline")
        return {
            "dossier": dossier_name,
            "status": "MOCK",
            "doc_count": doc_count,
            "note": "Test structure — workspace requis pour exécution réelle",
        }

    print(f"\n[3/5] Pipeline V5 execution...")
    t0 = time.time()
    try:
        result = run_pipeline_v5(workspace_id, force_m14=True)
        duration = time.time() - t0

        print(f"✅ Completed in {duration:.1f}s")
        print(f"   Offers extracted: {result.step_1_offers_extracted}")
        print(f"   M12 reconstructed: {result.step_2_m12_reconstructed}")
        print(f"   M13 procedure_type: {result.step_3_m13_procedure_type}")
        print(f"   M14 eval_doc: {result.step_4_m14_eval_doc_id}")
        print(f"   M16 assessments: {result.step_5_assessments_created}")

        return {
            "dossier": dossier_name,
            "status": "SUCCESS",
            "doc_count": doc_count,
            "duration_s": round(duration, 2),
            "offers_extracted": result.step_1_offers_extracted,
            "procedure_type": result.step_3_m13_procedure_type,
            "framework_expected": config["expected_framework"],
            "eval_doc_created": result.step_4_m14_eval_doc_id is not None,
            "assessments_created": result.step_5_assessments_created,
            "completed": result.completed,
            "error": result.error,
        }
    except Exception as exc:
        duration = time.time() - t0
        print(f"❌ FAILED: {exc}")
        return {
            "dossier": dossier_name,
            "status": "FAILED",
            "doc_count": doc_count,
            "duration_s": round(duration, 2),
            "error": str(exc)[:500],
        }


def print_summary(results: list[dict]):
    """Affiche tableau récapitulatif metrics."""
    print(f"\n{'='*80}")
    print(f"SUMMARY METRICS -- {len(results)} dossiers testes")
    print(f"{'='*80}\n")

    for r in results:
        status_icon = {
            "SUCCESS": "[OK]",
            "FAILED": "[FAIL]",
            "SKIPPED": "[SKIP]",
            "MOCK": "[MOCK]",
        }.get(r["status"], "[?]")

        print(f"{status_icon} {r['dossier']:<20} | Docs: {r.get('doc_count', 0):>3}")

        if r["status"] == "SUCCESS":
            print(f"     Duration: {r['duration_s']}s")
            print(f"     Offers: {r['offers_extracted']}")
            print(f"     Procedure: {r['procedure_type']} (expected: {r['framework_expected']})")
            print(f"     Eval doc: {r['eval_doc_created']}")
            print(f"     Assessments: {r['assessments_created']}")
        elif r["status"] == "FAILED":
            print(f"     Error: {r.get('error', 'Unknown')[:100]}")
        elif r["status"] == "MOCK":
            print(f"     Note: {r.get('note', 'Mock test')}")

        print()

    # Metrics agregees
    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    total_docs = sum(r.get("doc_count", 0) for r in results)
    total_offers = sum(r.get("offers_extracted", 0) for r in results if r["status"] == "SUCCESS")
    avg_duration = sum(r.get("duration_s", 0) for r in results if r["status"] == "SUCCESS")
    if success_count > 0:
        avg_duration /= success_count

    print(f"{'='*80}")
    print(f"METRICS GLOBALES")
    print(f"{'='*80}")
    print(f"Success rate: {success_count}/{len(results)} ({success_count/len(results)*100:.0f}%)")
    print(f"Total documents: {total_docs}")
    print(f"Total offers extracted: {total_offers}")
    print(f"Avg duration: {avg_duration:.1f}s per dossier")
    print(f"{'='*80}\n")


def main():
    print(f"=" * 80)
    print(f"PIPELINE V5 — TEST 3 DOSSIERS RÉELS")
    print(f"Date: {datetime.now().isoformat()}")
    print(f"=" * 80)

    results = []

    # Test structure dossiers (sans execution pipeline)
    print("\n[MODE] Structure test -- Workspace IDs requis pour execution complete\n")

    for dossier_name, config in DOSSIERS.items():
        result = test_dossier(dossier_name, config, workspace_id=None)
        results.append(result)

    print_summary(results)

    # Instructions execution complete
    print("\n[EXECUTION COMPLETE]:")
    print("1. Creer 3 workspaces via API:")
    print("   POST /api/workspaces")
    print("   Body: {title, reference_code, process_type}")
    print()
    print("2. Upload ZIP pour chaque dossier:")
    print("   POST /api/workspaces/{id}/upload-zip")
    print()
    print("3. Run pipeline:")
    print("   POST /api/workspaces/{id}/run-pipeline")
    print()
    print("4. Re-run ce script avec workspace IDs:")
    print("   python test_pipeline_real_folders.py --workspace-gcf=<uuid> --workspace-padem=<uuid> ...")
    print()

    return 0 if all(r["status"] != "FAILED" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
