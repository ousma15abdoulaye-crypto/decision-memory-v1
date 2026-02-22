# src/api/main.py
"""
Application FastAPI — DMS
Constitution V3.3.2 — Tous les routers montés explicitement.
"""

from fastapi import FastAPI

from src.couche_a.criteria.router import router as criteria_router

# Routers optionnels — ImportError = milestone pas encore actif (normal)
# Toute autre exception remonte (bug réel — ne pas masquer — règle CTO)
_extraction_router = None
_auth_router = None
_cases_router = None
_documents_router = None
_health_router = None
_analysis_router = None
_mercuriale_router = None

try:
    from src.api.routes.extractions import router as extraction_router

    _extraction_router = extraction_router
except ImportError:
    pass

try:
    from src.auth_router import router as auth_router

    _auth_router = auth_router
except ImportError:
    pass

try:
    from src.api.cases import router as cases_router

    _cases_router = cases_router
except ImportError:
    pass

try:
    from src.api.documents import router as documents_router

    _documents_router = documents_router
except ImportError:
    pass

try:
    from src.api.health import router as health_router

    _health_router = health_router
except ImportError:
    pass

try:
    from src.api.analysis import router as analysis_router

    _analysis_router = analysis_router
except ImportError:
    pass

try:
    from src.api.routers.mercuriale import router as mercuriale_router

    _mercuriale_router = mercuriale_router
except ImportError:
    pass

app = FastAPI(
    title="DMS API",
    version="0.1.0",
    description="Decision Memory System — Constitution V3.3.2",
)

# Router obligatoire M-CRITERIA-TYPING
app.include_router(criteria_router)

# Routers conditionnels
for _router in [
    _extraction_router,
    _auth_router,
    _cases_router,
    _documents_router,
    _health_router,
    _analysis_router,
    _mercuriale_router,
]:
    if _router is not None:
        app.include_router(_router)
