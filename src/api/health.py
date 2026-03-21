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

    overall = "healthy" if db_reachable else "degraded"
    payload = {
        "status": overall,
        "version": APP_VERSION,
        "invariants_status": "enforced",
        "database": "ok" if db_reachable else "error",
    }
    if redis_checked:
        payload["redis"] = "ok" if redis_ok else "error"
    return payload


@router.get("/api/constitution")
def api_constitution():
    return {"invariants": INVARIANTS, "version": APP_VERSION}
