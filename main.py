import logging
import os

# Load .env and .env.local before db import (DATABASE_URL required)
try:
    from dotenv import load_dotenv

    load_dotenv()
    load_dotenv(".env.local")
except ImportError:
    pass

# Configure logging pour resilience patterns
from src.logging_config import configure_logging

configure_logging()


# ❌ REMOVED: from src.couche_a.procurement import router as procurement_router (M2-Extended)
# =========================
# Database — PostgreSQL only (schema created on startup)
# =========================
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.api import analysis, cases, documents, health
from src.api.routes.extractions import router as extraction_router
from src.auth_router import router as auth_router
from src.core.config import (
    APP_TITLE,
    APP_VERSION,
    STATIC_DIR,
)
from src.core.models import (
    AnalyzeRequest,
    CaseCreate,
    DecideRequest,
)
from src.couche_a.committee.router import router as committee_router
from src.couche_a.routers import router as upload_router
from src.db import (
    init_db_schema,
)
from src.ratelimit import init_rate_limit


@asynccontextmanager
async def lifespan(app):
    # Optional Alembic migration at startup.
    # Activate by setting RUN_MIGRATIONS_ON_STARTUP=true in the environment.
    # Prefer Railway Release Command or start.sh for migrations to avoid
    # concurrent runs across workers.  This block is a fallback for deployments
    # where the Procfile / Release Command cannot be used.
    # TESTING=true (parsed as boolean) skips this block in test environments.
    _logger = logging.getLogger(__name__)
    _run_mig = os.environ.get("RUN_MIGRATIONS_ON_STARTUP", "").lower() == "true"
    _is_testing = os.environ.get("TESTING", "false").lower() == "true"
    if _run_mig and not _is_testing:
        import subprocess
        import sys

        _logger.info(
            "[lifespan] RUN_MIGRATIONS_ON_STARTUP=true — running alembic upgrade head"
        )
        try:
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                check=True,
            )
            _logger.info("[lifespan] alembic upgrade head OK:\n%s", result.stdout)
        except subprocess.CalledProcessError as exc:
            _logger.error(
                "[lifespan] alembic upgrade head FAILED (rc=%d):\n%s",
                exc.returncode,
                exc.stderr or exc.stdout,
            )
            raise RuntimeError("Alembic migration failed, aborting startup") from exc
    if not _is_testing:
        init_db_schema()
    yield


app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)


@app.get("/health")
def health_probe() -> dict[str, str]:
    """
    Sonde légère pour Railway / LB (souvent healthcheckPath=/health).
    Contrôle DB + Redis : GET /api/health.
    """
    return {"status": "ok", "service": "dms-api", "version": APP_VERSION}


# Initialize rate limiting
init_rate_limit(app)

# Middlewares sécurité (SecurityHeaders + TenantContext RLS + RedisRateLimit)
try:
    from src.couche_a.auth.middleware import (
        RedisRateLimitMiddleware,
        SecurityHeadersMiddleware,
        TenantContextMiddleware,
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RedisRateLimitMiddleware)
    app.add_middleware(TenantContextMiddleware)
except ImportError as _mw_err:
    logging.getLogger(__name__).warning(
        "[main] middlewares sécurité non chargés : %s", _mw_err
    )

# Include routers
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(health.router)
app.include_router(cases.router)
app.include_router(documents.router)
app.include_router(analysis.router)
app.include_router(extraction_router)
app.include_router(committee_router)
from src.couche_a.scoring import api as scoring_api

app.include_router(scoring_api.router)
# ❌ REMOVED: app.include_router(procurement_router) (M2-Extended)

# ── Router criteria (OBLIGATOIRE — mirrors src/api/main.py §D1.3) ────────────
from src.couche_a.criteria.router import router as _criteria_router

app.include_router(_criteria_router)

# ── Routers optionnels (strangler pattern — mirrors src/api/main.py) ──────────
_geo_router = None
try:
    from src.geo.router import router as _geo_router_imp

    _geo_router = _geo_router_imp
except ImportError as _e:
    logging.getLogger(__name__).warning(
        "[main] router optionnel src.geo non chargé : %s", _e
    )

_vendors_router = None
try:
    from src.vendors.router import router as _vendors_router_imp

    _vendors_router = _vendors_router_imp
except ImportError as _e:
    logging.getLogger(__name__).warning(
        "[main] router optionnel src.vendors non chargé : %s", _e
    )

_mercuriale_router = None
try:
    from src.api.routers.mercuriale import router as _mercuriale_router_imp

    _mercuriale_router = _mercuriale_router_imp
except ImportError as _e:
    logging.getLogger(__name__).warning(
        "[main] router optionnel src.api.routers.mercuriale non chargé : %s", _e
    )

_price_check_router = None
try:
    from src.api.routers.price_check import router as _price_check_router_imp

    _price_check_router = _price_check_router_imp
except ImportError as _e:
    logging.getLogger(__name__).warning(
        "[main] router optionnel src.api.routers.price_check non chargé : %s", _e
    )

_pipeline_a_router = None
try:
    from src.couche_a.pipeline.router import router as _pipeline_a_router_imp

    _pipeline_a_router = _pipeline_a_router_imp
except ImportError as _e:
    logging.getLogger(__name__).warning(
        "[main] router optionnel src.couche_a.pipeline non chargé : %s", _e
    )

_analysis_summary_router = None
try:
    from src.couche_a.analysis_summary.router import (
        router as _analysis_summary_router_imp,
    )

    _analysis_summary_router = _analysis_summary_router_imp
except ImportError as _e:
    logging.getLogger(__name__).warning(
        "[main] router optionnel src.couche_a.analysis_summary non chargé : %s", _e
    )

for _opt_router in [
    _geo_router,
    _vendors_router,
    _mercuriale_router,
    _price_check_router,
    _pipeline_a_router,
    _analysis_summary_router,
]:
    if _opt_router is not None:
        app.include_router(_opt_router)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Rebuild Pydantic models to resolve forward references
try:
    CaseCreate.model_rebuild()
    AnalyzeRequest.model_rebuild()
    DecideRequest.model_rebuild()
except Exception:
    pass  # Ignore if models don't need rebuilding

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
