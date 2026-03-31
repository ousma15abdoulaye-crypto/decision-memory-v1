"""
Health and status endpoints.
"""

import logging

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.core.config import APP_VERSION, INVARIANTS, STATIC_DIR

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/", response_class=HTMLResponse)
def home():
    idx = STATIC_DIR / "index.html"
    if not idx.exists():
        return HTMLResponse("<h3>Missing static/index.html</h3>", status_code=500)
    return HTMLResponse(idx.read_text(encoding="utf-8"))


@router.get("/api/health")
def health():
    db_reachable = False
    try:
        from src.db.connection import get_db_cursor

        with get_db_cursor() as cur:
            cur.execute("SELECT 1")
        db_reachable = True
    except Exception:
        logger.exception("Health check: database unreachable")

    redis_checked = False
    redis_ok = False
    try:
        import os

        if os.environ.get("REDIS_URL", "").strip():
            import redis as redis_lib

            r = redis_lib.from_url(
                os.environ["REDIS_URL"], decode_responses=True, socket_connect_timeout=1
            )
            redis_ok = bool(r.ping())
            redis_checked = True
    except Exception:
        redis_checked = True

    # Alembic head
    alembic_head = "unknown"
    migration_current = "unknown"
    if db_reachable:
        try:
            with get_db_cursor() as cur:
                cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
                row = cur.fetchone()
                migration_current = row[0] if row else "none"
        except Exception:
            pass

    try:
        from pathlib import Path

        versions_dir = Path(__file__).resolve().parents[2] / "alembic" / "versions"
        if versions_dir.is_dir():
            all_revs: set[str] = set()
            all_downs: set[str] = set()
            for f in versions_dir.glob("*.py"):
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                    for line in content.splitlines():
                        s = line.strip()
                        if s.startswith("revision ="):
                            all_revs.add(s.split("=", 1)[1].strip().strip("\"'"))
                        if s.startswith("down_revision ="):
                            v = s.split("=", 1)[1].strip().strip("\"'")
                            if v and v != "None" and "(" not in v:
                                all_downs.add(v)
                except Exception:
                    pass
            heads = all_revs - all_downs
            alembic_head = sorted(heads)[0] if len(heads) == 1 else str(sorted(heads))
    except Exception:
        pass

    # OCR engines
    ocr_engines: list[str] = []
    try:
        import os as _os

        if _os.environ.get("MISTRAL_API_KEY", "").strip():
            ocr_engines.append("mistral_ocr")
        if (
            _os.environ.get("LLAMADMS", "").strip()
            or _os.environ.get("LLAMA_CLOUD_API_KEY", "").strip()
        ):
            ocr_engines.append("llamaparse")
        if _os.environ.get("AZURE_FORM_RECOGNIZER_ENDPOINT", "").strip():
            ocr_engines.append("azure")
        ocr_engines.extend(["native_pdf", "excel_parser", "docx_parser"])
    except Exception:
        pass

    # LLM Arbitrator
    llm_arbitrator_status = "unknown"
    try:
        from src.procurement.llm_arbitrator import get_arbitrator

        arb = get_arbitrator()
        llm_arbitrator_status = "available" if arb.is_available() else "disabled"
    except Exception:
        llm_arbitrator_status = "not_loaded"

    overall = "healthy" if db_reachable else "degraded"
    payload = {
        "status": overall,
        "version": APP_VERSION,
        "invariants_status": "enforced",
        "database": "ok" if db_reachable else "error",
        "alembic_head": alembic_head,
        "migration_current": migration_current,
        "ocr_engines_available": ocr_engines,
        "llm_arbitrator_status": llm_arbitrator_status,
    }
    if redis_checked:
        payload["redis"] = "ok" if redis_ok else "error"
    return payload


@router.get("/api/constitution")
def api_constitution():
    return {"invariants": INVARIANTS, "version": APP_VERSION}
