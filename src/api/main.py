# src/api/main.py
"""
Application FastAPI — DMS
Constitution V3.3.2 — Tous les routers montés explicitement.

Politique routers (ADR-M5-PRE-001 §D1.3) :
  - Routers OBLIGATOIRES (auth, cases, health, criteria) : import direct.
    Toute exception = bug réel = remonte sans masquage.
  - Routers OPTIONNELS (milestones futurs) : try/except autorisé,
    mais logger.warning explicite avec nom du module et erreur.
  - lifespan startup logue les routers actifs au démarrage.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Routers OBLIGATOIRES — import direct, aucun try/except ───────────────────
from src.api.cases import router as _cases_router
from src.api.health import router as _health_router
from src.api.routers.committee_sessions import router as committee_sessions_router
from src.api.routers.documents import router as committee_documents_router
from src.api.routers.market import router as market_router
from src.api.routers.workspaces import router as workspaces_router
from src.auth_router import router as _auth_router
from src.couche_a.criteria.router import router as criteria_router

logger = logging.getLogger(__name__)

# ── Routers OPTIONNELS — try/except avec warning explicite ───────────────────

_extraction_router = None
try:
    from src.api.routes.extractions import router as extraction_router

    _extraction_router = extraction_router
except ImportError as _e:
    logger.warning(
        "[main] router optionnel src.api.routes.extractions non chargé : %s", _e
    )

_documents_router = None
try:
    from src.api.documents import router as documents_router

    _documents_router = documents_router
except ImportError as _e:
    logger.warning("[main] router optionnel src.api.documents non chargé : %s", _e)

_analysis_router = None
try:
    from src.api.analysis import router as analysis_router

    _analysis_router = analysis_router
except ImportError as _e:
    logger.warning("[main] router optionnel src.api.analysis non chargé : %s", _e)

_mercuriale_router = None
try:
    from src.api.routers.mercuriale import router as mercuriale_router

    _mercuriale_router = mercuriale_router
except ImportError as _e:
    logger.warning(
        "[main] router optionnel src.api.routers.mercuriale non chargé : %s", _e
    )

_price_check_router = None
try:
    from src.api.routers.price_check import router as price_check_router

    _price_check_router = price_check_router
except ImportError as _e:
    logger.warning(
        "[main] router optionnel src.api.routers.price_check non chargé : %s", _e
    )

_pipeline_a_router = None
try:
    from src.couche_a.pipeline.router import router as pipeline_a_router

    _pipeline_a_router = pipeline_a_router
except ImportError as _e:
    logger.warning("[main] router optionnel src.couche_a.pipeline non chargé : %s", _e)

_analysis_summary_router = None
try:
    from src.couche_a.analysis_summary.router import router as analysis_summary_router

    _analysis_summary_router = analysis_summary_router
except ImportError as _e:
    logger.warning(
        "[main] router optionnel src.couche_a.analysis_summary non chargé : %s", _e
    )

_committee_router = None
try:
    from src.couche_a.committee.router import router as committee_router

    _committee_router = committee_router
except ImportError as _e:
    logger.warning("[main] router optionnel src.couche_a.committee non chargé : %s", _e)

_geo_router = None
try:
    from src.geo.router import router as geo_router

    _geo_router = geo_router
except ImportError as _e:
    logger.warning("[main] router optionnel src.geo non chargé : %s", _e)

_vendors_router = None
try:
    from src.vendors.router import router as vendors_router

    _vendors_router = vendors_router
except ImportError as _e:
    logger.warning("[main] router optionnel src.vendors non chargé : %s", _e)

_m14_evaluation_router = None
try:
    from src.api.routes.evaluation import router as m14_evaluation_router

    _m14_evaluation_router = m14_evaluation_router
except ImportError as _e:
    logger.warning(
        "[main] router optionnel src.api.routes.evaluation non chargé : %s", _e
    )

_m16_comparative_router = None
try:
    from src.api.routers.m16_comparative import router as m16_comparative_router

    _m16_comparative_router = m16_comparative_router
except ImportError as _e:
    logger.warning(
        "[main] router optionnel src.api.routers.m16_comparative non chargé : %s", _e
    )

# ── Lifespan (FastAPI >= 0.93.0 — pattern lifespan) ───────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup : log routers actifs. Shutdown : aucun."""
    _optional_routers = {
        "extraction": _extraction_router,
        "documents": _documents_router,
        "analysis": _analysis_router,
        "mercuriale": _mercuriale_router,
        "price_check": _price_check_router,
        "pipeline_a": _pipeline_a_router,
        "analysis_summary": _analysis_summary_router,
        "committee": _committee_router,
        "geo": _geo_router,
        "vendors": _vendors_router,
        "m14_evaluation": _m14_evaluation_router,
        "m16_comparative": _m16_comparative_router,
    }
    active = [name for name, r in _optional_routers.items() if r is not None]
    inactive = [name for name, r in _optional_routers.items() if r is None]
    logger.info(
        "[startup] Routers obligatoires : auth, cases, health, criteria, "
        "workspaces (W1), market (W2), committee_sessions (W3) — ACTIFS"
    )
    if active:
        logger.info("[startup] Routers optionnels actifs : %s", active)
    if inactive:
        logger.info(
            "[startup] Routers optionnels inactifs (milestone non ouvert) : %s",
            inactive,
        )

    yield

    # Shutdown : aucun traitement requis


# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="DMS API",
    version="0.1.0",
    description="Decision Memory System — Constitution V3.3.2",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://frontend-v51-production.up.railway.app",
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Middlewares sécurité M1 (src/couche_a/auth/middleware.py)
# Ajout non-destructif — src/auth.py legacy non modifié.
try:
    from src.couche_a.auth.middleware import (
        RedisRateLimitMiddleware,
        SecurityHeadersMiddleware,
        TenantContextMiddleware,
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RedisRateLimitMiddleware)
    app.add_middleware(TenantContextMiddleware)
except ImportError as _e:
    logger.warning("[main] middlewares sécurité M1 non chargés : %s", _e)


# ── Montage des routers ───────────────────────────────────────────────────────

# Obligatoires
app.include_router(criteria_router)
app.include_router(_auth_router)
app.include_router(_cases_router)
app.include_router(_health_router)

# V4.2.0 — P0-OPS-01 (préfixes /api/* déjà définis sur chaque APIRouter ; pas de prefix ici)
app.include_router(workspaces_router)
app.include_router(committee_sessions_router)
app.include_router(committee_documents_router)
app.include_router(market_router)

# Optionnels
for _router in [
    _extraction_router,
    _documents_router,
    _analysis_router,
    _mercuriale_router,
    _price_check_router,
    _pipeline_a_router,
    _analysis_summary_router,
    _committee_router,
    _geo_router,
    _vendors_router,
    _m14_evaluation_router,
    _m16_comparative_router,
]:
    if _router is not None:
        app.include_router(_router)
