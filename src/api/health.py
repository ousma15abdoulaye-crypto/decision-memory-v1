"""
Health and status endpoints.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.core.config import APP_VERSION, INVARIANTS, STATIC_DIR

router = APIRouter(tags=["health"])


@router.get("/", response_class=HTMLResponse)
def home():
    idx = STATIC_DIR / "index.html"
    if not idx.exists():
        return HTMLResponse("<h3>Missing static/index.html</h3>", status_code=500)
    return HTMLResponse(idx.read_text(encoding="utf-8"))


@router.get("/api/health")
def health():
    return {
        "status": "healthy",
        "version": APP_VERSION,
        "invariants_status": "enforced"
    }


@router.get("/api/constitution")
def api_constitution():
    return {"invariants": INVARIANTS, "version": APP_VERSION}
