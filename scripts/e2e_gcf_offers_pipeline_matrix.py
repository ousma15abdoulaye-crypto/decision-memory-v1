#!/usr/bin/env python3
"""E2E rigoureux : 3 offres GCF → ZIP valide → Pass -1 → pipeline V5 → sonde matrice.

Sources (dossier annotation GCF) : OFFRE BATE, OFFRE CRECOS, OFFRE FETE IMPACTE.
Fichiers exclus automatiquement si extension hors whitelist ``zip_validator``
(.odt, .txt, .msg, etc.) — journal sur stderr.

Prérequis :
  - ``DATABASE_URL`` (.env.local)
  - Migrations Alembic ; utilisateur ``admin`` (seed 004)
  - Clés LLM / extractions selon ``pipeline_v5`` (MISTRAL, etc.)
  - ``langgraph`` pour Pass -1

Usage ::
  python scripts/e2e_gcf_offers_pipeline_matrix.py
  python scripts/e2e_gcf_offers_pipeline_matrix.py --build-only
  python scripts/e2e_gcf_offers_pipeline_matrix.py --zip path\\existing.zip --no-cleanup

Sortie : IDs workspace / case, résultats Pass-1 / pipeline, JSON sonde matrice (stdout).
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
import sys
import time
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Aligné src/assembler/zip_validator.py (pas d’import circulaire ici)
_ALLOWED_EXT = frozenset(
    {
        ".pdf",
        ".docx",
        ".doc",
        ".xlsx",
        ".xls",
        ".jpg",
        ".jpeg",
        ".png",
        ".tiff",
        ".tif",
    }
)

_GCF_OFFER_DIRS = (
    ("OFFRE_BATE", "OFFRE BATE"),
    ("OFFRE_CRECOS", "OFFRE CRECOS"),
    ("OFFRE_FETE_IMPACTE", "OFFRE FETE IMPACTE"),
)


def _gcf_base() -> Path:
    return (
        ROOT
        / "data"
        / "imports"
        / "annotation"
        / "SUPPLIERS BUNDLE TEST OFFRES COMPLETE"
        / "GCF"
    )


def build_gcf_three_offers_zip(
    out_path: Path, *, docx_only: bool = False
) -> tuple[Path, list[str]]:
    """Construit un ZIP avec 3 répertoires racine (une offre chacun).

    ``docx_only=True`` : limite aux ``.docx`` pour réduire la dépendance PDF/OCR
    (utile si Mistral SSL / Azure Doc Intelligence indisponibles en local).
    """
    base = _gcf_base()
    if not base.is_dir():
        raise FileNotFoundError(f"Dossier GCF introuvable : {base}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    skipped: list[str] = []
    included = 0
    allowed = {".docx"} if docx_only else _ALLOWED_EXT

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for arc_prefix, folder_name in _GCF_OFFER_DIRS:
            src = base / folder_name
            if not src.is_dir():
                raise FileNotFoundError(f"Sous-dossier offre manquant : {src}")
            for f in src.rglob("*"):
                if not f.is_file():
                    continue
                ext = f.suffix.lower()
                if ext not in allowed:
                    skipped.append(f"{f.relative_to(base)} (ext {ext!r})")
                    continue
                rel = f.relative_to(src)
                arcname = f"{arc_prefix}/{rel.as_posix()}"
                zf.write(f, arcname=arcname)
                included += 1

    if included == 0:
        raise RuntimeError("Aucun fichier autorisé — vérifier les offres GCF.")

    out_path.write_bytes(buf.getvalue())
    print(f"[build] ZIP écrit : {out_path} ({included} fichiers)", file=sys.stderr)
    if skipped:
        print(f"[build] Fichiers exclus ({len(skipped)}) :", file=sys.stderr)
        for s in skipped[:25]:
            print(f"  - {s}", file=sys.stderr)
        if len(skipped) > 25:
            print(f"  ... +{len(skipped) - 25} autres", file=sys.stderr)
    return out_path, skipped


def _cleanup(conn, *, workspace_id: str, case_id: str, committee_id: str) -> None:
    """Suppression ordonnée (FK). NB : ``criterion_assessments.bundle_id`` → ``supplier_bundles``
    est en ON DELETE CASCADE ; on garde un DELETE explicite des lignes workspace pour clarté.
    ``evaluation_documents.committee_id`` → ``committees`` impose ``evaluation_documents`` avant
    ``committees`` (et ``committee_members`` avant ``committees``).
    Tables M13 et ``decision_snapshots`` référencent ``cases`` : les vider avant ``DELETE cases``.
    ``score_history`` / ``elimination_log`` (schéma 074+) : ``workspace_id`` ; triggers append-only
    désactivés le temps du ``DELETE`` (nettoyage E2E uniquement).
    """
    with conn.cursor() as cur:
        cur.execute("SELECT set_config('app.is_admin', 'true', true)")
        cur.execute(
            "DELETE FROM criterion_assessments WHERE workspace_id = %s::uuid",
            (workspace_id,),
        )
        cur.execute(
            "DELETE FROM evaluation_documents WHERE workspace_id = %s::uuid",
            (workspace_id,),
        )
        cur.execute(
            "DELETE FROM offer_extractions WHERE workspace_id = %s::uuid",
            (workspace_id,),
        )
        cur.execute(
            "DELETE FROM bundle_documents WHERE workspace_id = %s::uuid",
            (workspace_id,),
        )
        cur.execute(
            "DELETE FROM supplier_bundles WHERE workspace_id = %s::uuid",
            (workspace_id,),
        )
        cur.execute(
            "DELETE FROM committee_members WHERE committee_id = %s::uuid",
            (committee_id,),
        )
        cur.execute(
            "DELETE FROM committees WHERE committee_id = %s::uuid", (committee_id,)
        )
        cur.execute(
            "DELETE FROM dao_criteria WHERE workspace_id = %s::uuid", (workspace_id,)
        )
        # M14 append-only (059) : sans DISABLE TRIGGER, DELETE est rejeté.
        cur.execute(
            "ALTER TABLE score_history DISABLE TRIGGER trg_score_history_append_only"
        )
        cur.execute(
            "ALTER TABLE elimination_log DISABLE TRIGGER trg_elimination_log_append_only"
        )
        try:
            cur.execute(
                "DELETE FROM score_history WHERE workspace_id = %s::uuid",
                (workspace_id,),
            )
            cur.execute(
                "DELETE FROM elimination_log WHERE workspace_id = %s::uuid",
                (workspace_id,),
            )
        finally:
            cur.execute(
                "ALTER TABLE score_history ENABLE TRIGGER trg_score_history_append_only"
            )
            cur.execute(
                "ALTER TABLE elimination_log ENABLE TRIGGER trg_elimination_log_append_only"
            )
        cur.execute(
            "DELETE FROM process_workspaces WHERE id = %s::uuid", (workspace_id,)
        )
        cur.execute(
            "DELETE FROM m13_regulatory_profile_versions WHERE case_id = %s",
            (case_id,),
        )
        cur.execute(
            "DELETE FROM m13_correction_log WHERE case_id = %s",
            (case_id,),
        )
        cur.execute(
            "ALTER TABLE decision_snapshots DISABLE TRIGGER "
            "trg_decision_snapshots_append_only"
        )
        try:
            cur.execute(
                "DELETE FROM decision_snapshots WHERE case_id = %s",
                (case_id,),
            )
        finally:
            cur.execute(
                "ALTER TABLE decision_snapshots ENABLE TRIGGER "
                "trg_decision_snapshots_append_only"
            )
        cur.execute("DELETE FROM cases WHERE id = %s", (case_id,))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--build-only",
        action="store_true",
        help="Ne construire que le ZIP puis quitter",
    )
    parser.add_argument(
        "--zip",
        type=Path,
        help="ZIP existant (sinon construction GCF → data/test_zip/gcf_three_offers.zip)",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Conserver workspace / artefacts pour inspection Grafana / API",
    )
    parser.add_argument(
        "--docx-only",
        action="store_true",
        help="ZIP uniquement .docx (recommandé si OCR PDF indisponible)",
    )
    parser.add_argument(
        "--strict-hitl",
        action="store_true",
        help="Ne pas forcer DMS_PASS1_HEADLESS (sinon reprise HITL LangGraph requise)",
    )
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
        load_dotenv(ROOT / ".env.local", override=True)
    except ImportError:
        pass

    zpath = args.zip
    if zpath is None:
        name = (
            "gcf_three_offers_docx_only.zip"
            if args.docx_only
            else "gcf_three_offers.zip"
        )
        zpath = ROOT / "data" / "test_zip" / name
        build_gcf_three_offers_zip(zpath, docx_only=args.docx_only)
    else:
        zpath = zpath.resolve()
        if not zpath.is_file():
            print(f"ZIP introuvable : {zpath}", file=sys.stderr)
            return 2

    if args.build_only:
        print(json.dumps({"zip": str(zpath)}, indent=2))
        return 0

    import psycopg
    from psycopg.rows import dict_row

    url = os.environ.get("DATABASE_URL", "").replace(
        "postgresql+psycopg://", "postgresql://"
    )
    if not url:
        print("DATABASE_URL requis", file=sys.stderr)
        return 2

    from src.db.tenant_context import reset_rls_request_context, set_rls_is_admin
    from src.services.pipeline_v5_service import run_pipeline_v5
    from src.workers.arq_tasks import run_pass_minus_1

    case_id = str(uuid.uuid4())
    ws_id = str(uuid.uuid4())
    committee_id = str(uuid.uuid4())

    conn = psycopg.connect(url, row_factory=dict_row, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.is_admin', 'true', true)")
            cur.execute("SELECT id FROM tenants WHERE code = %s LIMIT 1", ("sci_mali",))
            tr = cur.fetchone()
            if tr:
                tenant_id = str(tr["id"])
            else:
                tenant_id = str(uuid.uuid4())
                cur.execute(
                    "INSERT INTO tenants (id, code, name) VALUES (%s, %s, %s)",
                    (tenant_id, "sci_mali", "SCI Mali"),
                )
            cur.execute("SELECT id FROM users WHERE username = %s LIMIT 1", ("admin",))
            ur = cur.fetchone()
            if not ur:
                print(
                    "Utilisateur admin absent — migrations / seed 004.",
                    file=sys.stderr,
                )
                return 2
            owner_id = int(ur["id"])

            cur.execute(
                """
                INSERT INTO public.cases
                    (id, case_type, title, created_at, currency, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    case_id,
                    "DAO",
                    f"gcf-e2e-{case_id[:8]}",
                    datetime.now(UTC).isoformat(),
                    "XOF",
                    "draft",
                ),
            )
            cur.execute(
                """
                INSERT INTO process_workspaces
                    (id, tenant_id, created_by, reference_code, title, process_type,
                     status, legacy_case_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    ws_id,
                    tenant_id,
                    owner_id,
                    f"GCF-E2E-{ws_id[:8]}",
                    "GCF corpus — 3 offres ZIP E2E",
                    "devis_simple",
                    "draft",
                    case_id,
                ),
            )
            cur.execute(
                """
                INSERT INTO public.committees
                    (committee_id, case_id, org_id, committee_type, created_by, status)
                VALUES (%s::uuid, %s, %s, %s, %s, %s)
                """,
                (committee_id, case_id, "org-test", "achat", "e2e-gcf", "draft"),
            )
            # INV-W03 : somme des pondérations = 100 % (hors éliminatoires)
            for i, w in enumerate((55.0, 45.0)):
                cid = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO public.dao_criteria
                        (id, workspace_id, categorie, critere_nom, description,
                         ponderation, type_reponse, seuil_elimination,
                         ordre_affichage, created_at, m16_criterion_code)
                    VALUES (%s, %s::uuid, %s, %s, %s, %s, %s, NULL, %s, NOW()::text, %s)
                    """,
                    (
                        cid,
                        ws_id,
                        "commercial",
                        f"Critère E2E GCF {i + 1}",
                        "Pondération script E2E",
                        w,
                        "quantitatif",
                        i,
                        f"GCF_E2E_{i}",
                    ),
                )
    finally:
        conn.close()

    meta = {
        "zip": str(zpath),
        "workspace_id": ws_id,
        "case_id": case_id,
        "committee_id": committee_id,
        "tenant_id": tenant_id,
    }
    print(json.dumps({"phase": "db_seeded", **meta}, indent=2), file=sys.stderr)

    t_all = time.perf_counter()
    _prev_headless = os.environ.get("DMS_PASS1_HEADLESS")
    if not args.strict_hitl:
        os.environ["DMS_PASS1_HEADLESS"] = "1"
    try:
        out_pass = asyncio.run(
            run_pass_minus_1(
                {},
                workspace_id=ws_id,
                tenant_id=tenant_id,
                zip_path=str(zpath),
            )
        )
    finally:
        if _prev_headless is None:
            os.environ.pop("DMS_PASS1_HEADLESS", None)
        else:
            os.environ["DMS_PASS1_HEADLESS"] = _prev_headless
    meta["pass_minus_1"] = out_pass
    if out_pass.get("error"):
        if not args.no_cleanup:
            conn = psycopg.connect(url, row_factory=dict_row, autocommit=True)
            try:
                _cleanup(
                    conn, workspace_id=ws_id, case_id=case_id, committee_id=committee_id
                )
            finally:
                conn.close()
        print(json.dumps({"error": "pass_minus_1", **meta}, indent=2))
        return 1

    bids = out_pass.get("bundle_ids") or []
    if len(bids) == 0:
        meta["error"] = "pass_minus_1_zero_bundles"
        meta["hint"] = (
            "Réessayer avec --docx-only ; vérifier OCR (Mistral SSL, Azure) "
            "ou logs assembleur Pass -1."
        )
        if not args.no_cleanup:
            conn = psycopg.connect(url, row_factory=dict_row, autocommit=True)
            try:
                _cleanup(
                    conn, workspace_id=ws_id, case_id=case_id, committee_id=committee_id
                )
            finally:
                conn.close()
        print(json.dumps(meta, indent=2))
        return 1

    set_rls_is_admin(True)
    try:
        t0 = time.perf_counter()
        result = run_pipeline_v5(ws_id, force_m14=True)
        meta["pipeline_v5_seconds"] = round(time.perf_counter() - t0, 2)
    finally:
        reset_rls_request_context()

    meta["pipeline_v5"] = {
        "completed": result.completed,
        "stopped_at": result.stopped_at,
        "error": result.error,
        "step_5_assessments_created": result.step_5_assessments_created,
    }
    meta["wall_seconds_total"] = round(time.perf_counter() - t_all, 2)

    # Sonde matrice (réutilise la logique probe)
    sys.path.insert(0, str(ROOT / "scripts"))
    import importlib.util

    probe_path = ROOT / "scripts" / "probe_matrix_m14_m16.py"
    spec = importlib.util.spec_from_file_location("probe_matrix_m14_m16", probe_path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        conn = psycopg.connect(url, row_factory=dict_row, autocommit=True)
        try:
            ed = conn.execute(
                """
                SELECT id::text, scores_matrix
                FROM evaluation_documents
                WHERE workspace_id = %s::uuid
                ORDER BY created_at DESC NULLS LAST
                LIMIT 1
                """,
                (ws_id,),
            ).fetchone()
            sm = (ed or {}).get("scores_matrix")
            if isinstance(sm, str):
                sm = json.loads(sm)
            meta["matrix_probe"] = mod.analyze_scores_matrix(sm)
            meta["evaluation_document_id"] = ed.get("id") if ed else None
            n_b = conn.execute(
                "SELECT COUNT(*)::int AS n FROM supplier_bundles WHERE workspace_id = %s::uuid",
                (ws_id,),
            ).fetchone()
            meta["supplier_bundles_count"] = n_b["n"] if n_b else 0
            n_ca = conn.execute(
                """
                SELECT COUNT(*)::int AS n FROM criterion_assessments
                WHERE workspace_id = %s::uuid
                """,
                (ws_id,),
            ).fetchone()
            meta["criterion_assessments_count"] = n_ca["n"] if n_ca else 0
        finally:
            conn.close()

    print(json.dumps({"phase": "complete", **meta}, indent=2, default=str))

    if not args.no_cleanup:
        conn = psycopg.connect(url, row_factory=dict_row, autocommit=True)
        try:
            _cleanup(
                conn, workspace_id=ws_id, case_id=case_id, committee_id=committee_id
            )
            meta["cleanup"] = "done"
        finally:
            conn.close()

    return 0 if result.completed and not result.error else 1


if __name__ == "__main__":
    raise SystemExit(main())
