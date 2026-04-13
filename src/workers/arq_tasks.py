"""ARQ background tasks for VIVANT V2 (event indexing, patterns, candidate rules).

Tasks are async; they receive an ``arq`` context dict with a db_conn factory
injected via on_startup. When arq is not installed (CI), the functions still
import cleanly — stubs are never called in production.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _get_conn_factory():
    """Return a conn_factory using PsycopgCursorAdapter over get_db_cursor."""
    from src.db.connection import get_db_cursor
    from src.db.cursor_adapter import PsycopgCursorAdapter

    class _CtxConn:
        """One-shot connection wrapper for service compatibility."""

        def __init__(self) -> None:
            self._cur = None
            self._ctx = None

        def _open(self):
            self._ctx = get_db_cursor()
            self._cur = PsycopgCursorAdapter(self._ctx.__enter__())
            return self._cur

    def factory():
        from src.db.connection import get_db_cursor
        from src.db.cursor_adapter import PsycopgCursorAdapter

        ctx = get_db_cursor()
        cur = ctx.__enter__()
        return PsycopgCursorAdapter(cur)

    return factory


async def index_event(ctx: dict[str, Any], event_dict: dict[str, Any]) -> str:
    """Index a single domain event into dms_event_index.

    ``event_dict`` must match the ``EventEntry`` Pydantic model fields.
    Called from bridge triggers callbacks or external producers.
    """
    try:
        from src.memory.event_index_models import EventEntry
        from src.memory.event_index_service import EventIndexService

        entry = EventEntry(**event_dict)
        svc = EventIndexService(_get_conn_factory())
        event_id = svc.append(entry)
        logger.info(
            "index_event: appended %s (domain=%s)", event_id, entry.event_domain
        )
        return event_id
    except Exception as exc:
        logger.error("index_event failed: %s", exc)
        raise


async def detect_patterns(ctx: dict[str, Any]) -> int:
    """Detect correction clusters and generate candidate rules.

    Reads ``m13_correction_log``, detects patterns with ``PatternDetector``,
    then persists candidate rules via ``CandidateRuleService``.
    Returns the count of rules saved.
    """
    try:
        from src.memory.candidate_rule_generator import CandidateRuleGenerator
        from src.memory.candidate_rule_service import CandidateRuleService
        from src.memory.pattern_detector import PatternDetector

        factory = _get_conn_factory()
        conn = factory()

        detector = PatternDetector(lambda: conn)
        patterns = detector.detect_all()
        logger.info("detect_patterns: found %d patterns", len(patterns))

        generator = CandidateRuleGenerator()
        rules = generator.generate_from_patterns(patterns)
        logger.info("detect_patterns: generated %d candidate rules", len(rules))

        svc = CandidateRuleService(lambda: conn)
        saved = 0
        for rule in rules:
            try:
                svc.save(rule)
                saved += 1
            except Exception as save_exc:
                logger.warning(
                    "detect_patterns: skip rule %s: %s", rule.get("rule_id"), save_exc
                )

        return saved
    except Exception as exc:
        logger.error("detect_patterns failed: %s", exc)
        raise


async def generate_candidate_rules(ctx: dict[str, Any]) -> int:
    """Alias for detect_patterns — kept for backward compat / independent scheduling."""
    return await detect_patterns(ctx)


async def run_pass_minus_1(
    ctx: dict[str, Any],
    workspace_id: str,
    tenant_id: str,
    zip_path: str = "",
    zip_r2_key: str = "",
) -> dict:
    """Exécute le Pass -1 (ZIP → bundles fournisseurs) via LangGraph.

    Sources du ZIP :
    - Si ``zip_path`` pointe vers un fichier local existant (tests / repli API
      filesystem), ce chemin est utilisé.
    - Sinon clé R2 : argument ``zip_r2_key`` si fourni, sinon
      ``process_workspaces.zip_r2_key``.

    Contexte RLS posé pour toute la fonction (graphe / INSERT bundles) ;
    ``reset_rls_request_context`` uniquement en ``finally``.

    Rejouable (idempotent) : bundle_documents a UNIQUE(workspace_id, sha256).
    """
    from src.assembler.graph import build_pass_minus_one_graph
    from src.assembler.zip_validator import validate_zip
    from src.core.config import get_settings, make_r2_s3_client
    from src.db import db_execute_one, get_connection
    from src.db.tenant_context import (
        reset_rls_request_context,
        set_db_tenant_id,
        set_rls_is_admin,
    )

    set_db_tenant_id(str(tenant_id))
    set_rls_is_admin(True)

    resolved_zip: str | None = None
    cleanup_path: str | None = None

    zp_in = Path(zip_path) if zip_path else None
    if zp_in and zp_in.is_file():
        resolved_zip = str(zp_in.resolve())
        ups_root = Path(get_settings().UPLOADS_DIR).resolve()
        try:
            rp = Path(resolved_zip).resolve()
            if rp == ups_root or ups_root in rp.parents:
                cleanup_path = resolved_zip
        except (OSError, ValueError):
            pass
        logger.info(
            "[PASS-1] ZIP local workspace=%s path=%s", workspace_id, resolved_zip
        )
    else:
        r2_key = (zip_r2_key or "").strip()
        if not r2_key:
            with get_connection() as conn:
                row = db_execute_one(
                    conn,
                    """
                    SELECT zip_r2_key, zip_filename
                    FROM process_workspaces
                    WHERE id = CAST(:wid AS uuid)
                    """,
                    {"wid": workspace_id},
                )
            r2_key = ((row or {}).get("zip_r2_key") or "").strip()

        if not r2_key:
            err = (
                f"[PASS-1] ZIP introuvable : pas de zip_r2_key en base pour workspace "
                f"{workspace_id}. Effectuer un upload ZIP depuis l'API (R2 ou UPLOADS_DIR)."
            )
            logger.error("%s", err)
            reset_rls_request_context()
            return {"workspace_id": workspace_id, "bundle_ids": [], "error": err}

        if not get_settings().r2_object_storage_configured():
            err = (
                "[PASS-1] zip_r2_key présent en base mais R2 non configuré sur le worker "
                "(R2_ENDPOINT_URL / clés)."
            )
            logger.error("%s", err)
            reset_rls_request_context()
            return {"workspace_id": workspace_id, "bundle_ids": [], "error": err}

        s3 = make_r2_s3_client()
        s = get_settings()
        obj = s3.get_object(Bucket=s.R2_BUCKET_NAME, Key=str(r2_key))
        body = obj["Body"]
        tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        tmp.close()
        try:
            with open(tmp.name, "wb") as out_f:
                shutil.copyfileobj(body, out_f, length=1024 * 1024)
        finally:
            try:
                body.close()
            except Exception:
                pass
        resolved_zip = tmp.name
        cleanup_path = tmp.name
        nbytes = Path(resolved_zip).stat().st_size
        logger.info(
            "[PASS-1] ZIP R2 workspace=%s key=%s bytes=%d",
            workspace_id,
            r2_key,
            nbytes,
        )

    assert resolved_zip is not None

    try:
        validation = validate_zip(resolved_zip)
        if not validation.is_valid:
            logger.error(
                "[PASS-1] ZIP invalide workspace=%s : %s",
                workspace_id,
                validation.error,
            )
            return {
                "workspace_id": workspace_id,
                "bundle_ids": [],
                "error": validation.error,
            }

        graph = build_pass_minus_one_graph()
        if graph is None:
            return {
                "workspace_id": workspace_id,
                "bundle_ids": [],
                "error": "langgraph non installé",
            }

        initial_state = {
            "workspace_id": workspace_id,
            "tenant_id": tenant_id,
            "zip_path": resolved_zip,
            "extract_dir": "",
            "raw_documents": [],
            "bundles_draft": [],
            "hitl_required": False,
            "hitl_resolved": False,
            "finalized": False,
            "bundle_ids": [],
            "error": None,
        }

        config = {"configurable": {"thread_id": workspace_id}}
        final_state = await graph.ainvoke(initial_state, config=config)

        logger.info(
            "[PASS-1] Terminé workspace=%s bundles=%d",
            workspace_id,
            len(final_state.get("bundle_ids", [])),
        )
        return {
            "workspace_id": workspace_id,
            "bundle_ids": final_state.get("bundle_ids", []),
            "error": final_state.get("error"),
        }

    except Exception as exc:
        logger.error("[PASS-1] Erreur workspace=%s : %s", workspace_id, exc)
        raise
    finally:
        reset_rls_request_context()
        if not cleanup_path:
            pass
        else:
            try:
                zp_unlink = Path(cleanup_path)
                zp_unlink.unlink(missing_ok=True)
                zip_dir = zp_unlink.parent
                ups_root = Path(get_settings().UPLOADS_DIR).resolve()
                try:
                    zr = zip_dir.resolve()
                    if (
                        zip_dir.is_dir()
                        and (ups_root in zr.parents or zr == ups_root)
                        and not any(zip_dir.iterdir())
                    ):
                        zip_dir.rmdir()
                except OSError:
                    pass
            except Exception:
                pass
