"""
src/couche_a/analysis_summary/engine/service.py

Cœur du moteur analysis_summary — #12.
Orchestre : load → validate → build → hash → idempotence → persist → return.

INV-AS7  : API publique = generate_summary(case_id, triggered_by, conn, pipeline_run_id=None)
INV-AS8  : zéro appel aux fonctions d'exécution pipeline (ADR-0015)
INV-AS9  : result_hash sha256 déterministe
INV-AS9b : idempotence DB-level via UNIQUE(result_hash)
MG-01    : result_hash partout — source_result_hash BANNI
MG-02    : errors/warnings = list[dict[str, Any]]
MG-03    : pas d'import CaseAnalysisSnapshot (OPTION A)

Stratégie commit (probe 0-F — CAS A) :
  db_conn = autocommit=True → NE PAS appeler conn.commit() dans _persist_summary()
  Commit géré par le contexte appelant (router dependency ou autocommit).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from src.couche_a.analysis_summary.engine.builder import build_summary
from src.couche_a.analysis_summary.engine.models import SummaryDocument

# ─────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────

SUMMARY_VERSION = "v1"
SUPPORTED_CAS_VERSION = "v1"

# Mapping pipeline_status → summary_status (Section 6 — gravé)
_STATUS_MAP: dict[str, str] = {
    "partial_complete": "ready",
    "incomplete": "partial",
    "blocked": "blocked",
    "failed": "failed",
}


# ─────────────────────────────────────────────────────────────
# API PUBLIQUE — INV-AS7
# ─────────────────────────────────────────────────────────────


def generate_summary(
    case_id: str,
    triggered_by: str,
    conn,
    pipeline_run_id: str | None = None,
) -> SummaryDocument:
    """
    Point d'entrée unique moteur analysis_summary.

    Séquence (INV-AS8 : zéro déclenchement de pipeline) :
      1. Charger pipeline_run (par ID ou dernier pour case_id)
      2. Si absent → SummaryDocument blocked + persist + return
      3. Valider result_jsonb présent et non vide
      4. Désérialiser CAS v1 (dict — MG-03 OPTION A)
      5. Valider cas_version == "v1"
      6. Mapper pipeline_status → summary_status (_STATUS_MAP)
      7. build_summary(cas) → sections
      8. Construire SummaryDocument v1
      9. Calculer result_hash (sha256 déterministe — MG-01)
     10. Idempotence : chercher ligne existante par result_hash
     11. Si trouvée → retourner l'existant (INV-AS9b)
     12. Sinon → persister dans analysis_summaries
     13. Retourner SummaryDocument
    """
    generated_at = datetime.now(UTC)
    summary_id = str(uuid.uuid4())

    # ── STEP 1 : charger pipeline_run ────────────────────────
    pipeline_run = _load_pipeline_run(case_id, pipeline_run_id, conn)

    if pipeline_run is None:
        # STEP 2 : aucun run → blocked
        return _build_and_persist_blocked(
            summary_id=summary_id,
            case_id=case_id,
            triggered_by=triggered_by,
            generated_at=generated_at,
            reason_code="NO_PIPELINE_RUN",
            reason_message=(
                f"Aucun pipeline_run trouvé pour case_id '{case_id}'"
                + (f" / pipeline_run_id '{pipeline_run_id}'" if pipeline_run_id else "")
            ),
            conn=conn,
        )

    # ── STEP 3 : valider result_jsonb ────────────────────────
    result_jsonb_raw = pipeline_run.get("result_jsonb")
    if not result_jsonb_raw or result_jsonb_raw == {}:
        return _build_and_persist_failed(
            summary_id=summary_id,
            case_id=case_id,
            pipeline_run=pipeline_run,
            triggered_by=triggered_by,
            generated_at=generated_at,
            reason_code="EMPTY_RESULT_JSONB",
            reason_message="pipeline_runs.result_jsonb vide ou absent",
            conn=conn,
        )

    # ── STEP 4 : désérialiser CAS v1 ─────────────────────────
    cas: dict[str, Any] = (
        result_jsonb_raw
        if isinstance(result_jsonb_raw, dict)
        else json.loads(result_jsonb_raw)
    )

    # ── STEP 5 : valider version CAS ─────────────────────────
    cas_version = cas.get("cas_version")
    if cas_version != SUPPORTED_CAS_VERSION:
        return _build_and_persist_failed(
            summary_id=summary_id,
            case_id=case_id,
            pipeline_run=pipeline_run,
            triggered_by=triggered_by,
            generated_at=generated_at,
            reason_code="UNSUPPORTED_CAS_VERSION",
            reason_message=(
                f"cas_version '{cas_version}' non supportée. "
                f"Attendu '{SUPPORTED_CAS_VERSION}'."
            ),
            conn=conn,
        )

    # ── STEP 6 : mapper status ───────────────────────────────
    pipeline_status = pipeline_run.get("status", "failed")
    summary_status = _STATUS_MAP.get(pipeline_status, "failed")

    # ── STEP 7 : construire sections ─────────────────────────
    try:
        sections = build_summary(cas)
        build_warnings: list[dict[str, Any]] = []
        build_errors: list[dict[str, Any]] = []
    except ValueError as exc:
        return _build_and_persist_failed(
            summary_id=summary_id,
            case_id=case_id,
            pipeline_run=pipeline_run,
            triggered_by=triggered_by,
            generated_at=generated_at,
            reason_code="BUILD_SUMMARY_ERROR",
            reason_message=str(exc),
            conn=conn,
        )

    # Collecter warnings de toutes les sections
    for section in sections:
        for w in section.warnings:
            build_warnings.append(
                {
                    "source": f"section.{section.section_type}",
                    "message": w,
                }
            )

    # ── STEP 8 : construire SummaryDocument v1 ───────────────
    summary = SummaryDocument(
        summary_id=summary_id,
        case_id=case_id,
        pipeline_run_id=str(pipeline_run["pipeline_run_id"]),
        summary_version=SUMMARY_VERSION,
        summary_status=summary_status,
        triggered_by=triggered_by,
        generated_at=generated_at,
        source_pipeline_status=pipeline_status,
        source_cas_version=cas_version,
        sections=sections,
        warnings=build_warnings,
        errors=build_errors,
        result_hash="placeholder",  # recalculé étape 9
    )

    # ── STEP 9 : calculer result_hash ────────────────────────
    result_hash = _compute_result_hash(summary)
    summary = summary.model_copy(update={"result_hash": result_hash})

    # ── STEP 10/11 : idempotence ─────────────────────────────
    existing = _find_existing_summary(result_hash, conn)
    if existing:
        return existing

    # ── STEP 12 : persister ──────────────────────────────────
    _persist_summary(summary, conn)

    return summary


# ─────────────────────────────────────────────────────────────
# HELPERS INTERNES
# ─────────────────────────────────────────────────────────────


def _load_pipeline_run(
    case_id: str,
    pipeline_run_id: str | None,
    conn,
) -> dict[str, Any] | None:
    """
    Charge le pipeline_run depuis DB.
    Par ID si fourni, sinon dernier pour case_id.
    Retourne None si introuvable.
    Zéro appel pipeline (INV-AS8).
    """
    with conn.cursor() as cur:
        if pipeline_run_id:
            cur.execute(
                """
                SELECT pipeline_run_id, case_id, status, mode,
                       result_jsonb, created_at
                FROM public.pipeline_runs
                WHERE pipeline_run_id = %s AND case_id = %s
                """,
                (pipeline_run_id, case_id),
            )
        else:
            # Dernier run : ORDER BY created_at DESC, pipeline_run_id DESC
            # Déterministe : pipeline_run_id tie-breaker UUID
            cur.execute(
                """
                SELECT pipeline_run_id, case_id, status, mode,
                       result_jsonb, created_at
                FROM public.pipeline_runs
                WHERE case_id = %s
                ORDER BY created_at DESC, pipeline_run_id DESC
                LIMIT 1
                """,
                (case_id,),
            )
        return cur.fetchone()


def _compute_result_hash(summary: SummaryDocument) -> str:
    """
    Calcule le sha256 déterministe du SummaryDocument.
    MG-01 : result_hash — convention unique — source_result_hash BANNI.
    Exclut result_hash, summary_id et generated_at (non-déterministes).
    sort_keys=True + default=str garantissent le déterminisme.
    """
    data = summary.model_dump()
    data.pop("result_hash", None)
    data.pop("summary_id", None)
    data.pop("generated_at", None)
    canonical = json.dumps(data, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _find_existing_summary(result_hash: str, conn) -> SummaryDocument | None:
    """
    Cherche une ligne existante par result_hash (INV-AS9b).
    Retourne SummaryDocument reconstruit si trouvé, None sinon.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT result_jsonb, result_hash
            FROM public.analysis_summaries
            WHERE result_hash = %s
            LIMIT 1
            """,
            (result_hash,),
        )
        row = cur.fetchone()

    if not row:
        return None

    jsonb_raw = row["result_jsonb"] if isinstance(row, dict) else row[0]
    data = jsonb_raw if isinstance(jsonb_raw, dict) else json.loads(jsonb_raw)
    return SummaryDocument(**data)


def _persist_summary(summary: SummaryDocument, conn) -> None:
    """
    INSERT atomique dans analysis_summaries.
    Append-only — jamais d'UPDATE (INV-AS3).
    Requêtes paramétrées — jamais f-string SQL.

    Stratégie commit (probe 0-F — CAS A) :
      db_conn autocommit=True → commit immédiat après chaque statement.
      Router dependency (autocommit=False) : conn.commit() via __exit__.
      NE PAS appeler conn.commit() ici.
    """
    pipeline_run_id_val = (
        uuid.UUID(summary.pipeline_run_id) if summary.pipeline_run_id else None
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.analysis_summaries (
                summary_id, case_id, pipeline_run_id,
                summary_version, summary_status,
                source_pipeline_status, source_cas_version,
                result_jsonb, error_jsonb,
                result_hash, triggered_by,
                generated_at, created_at
            ) VALUES (
                %s, %s, %s,
                %s, %s,
                %s, %s,
                %s::jsonb, %s::jsonb,
                %s, %s,
                %s, NOW()
            )
            """,
            (
                summary.summary_id,
                summary.case_id,
                pipeline_run_id_val,
                summary.summary_version,
                summary.summary_status,
                summary.source_pipeline_status,
                summary.source_cas_version,
                summary.to_jsonb(),
                json.dumps(summary.errors, default=str),
                summary.result_hash,
                summary.triggered_by,
                summary.generated_at,
            ),
        )


def _build_and_persist_blocked(
    summary_id: str,
    case_id: str,
    triggered_by: str,
    generated_at: datetime,
    reason_code: str,
    reason_message: str,
    conn,
) -> SummaryDocument:
    """Construit, hash, et persiste un SummaryDocument blocked."""
    summary = SummaryDocument(
        summary_id=summary_id,
        case_id=case_id,
        pipeline_run_id=None,
        summary_version=SUMMARY_VERSION,
        summary_status="blocked",
        triggered_by=triggered_by,
        generated_at=generated_at,
        source_pipeline_status=None,
        source_cas_version=None,
        sections=[],
        warnings=[],
        errors=[
            {
                "source": "generate_summary",
                "reason_code": reason_code,
                "reason_message": reason_message,
            }
        ],
        result_hash="placeholder",
    )
    result_hash = _compute_result_hash(summary)
    summary = summary.model_copy(update={"result_hash": result_hash})

    existing = _find_existing_summary(result_hash, conn)
    if existing:
        return existing

    _persist_summary(summary, conn)
    return summary


def _build_and_persist_failed(
    summary_id: str,
    case_id: str,
    pipeline_run: dict[str, Any],
    triggered_by: str,
    generated_at: datetime,
    reason_code: str,
    reason_message: str,
    conn,
) -> SummaryDocument:
    """Construit, hash, et persiste un SummaryDocument failed."""
    pipeline_run_id_str = str(pipeline_run.get("pipeline_run_id", ""))
    pipeline_status = pipeline_run.get("status")

    summary = SummaryDocument(
        summary_id=summary_id,
        case_id=case_id,
        pipeline_run_id=pipeline_run_id_str or None,
        summary_version=SUMMARY_VERSION,
        summary_status="failed",
        triggered_by=triggered_by,
        generated_at=generated_at,
        source_pipeline_status=pipeline_status,
        source_cas_version=None,
        sections=[],
        warnings=[],
        errors=[
            {
                "source": "generate_summary",
                "reason_code": reason_code,
                "reason_message": reason_message,
            }
        ],
        result_hash="placeholder",
    )
    result_hash = _compute_result_hash(summary)
    summary = summary.model_copy(update={"result_hash": result_hash})

    existing = _find_existing_summary(result_hash, conn)
    if existing:
        return existing

    _persist_summary(summary, conn)
    return summary
