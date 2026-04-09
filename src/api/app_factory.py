"""Factories FastAPI partagées — parité ``main.py`` (Railway) vs ``src.api.main`` (harness).

ADR-DUAL-FASTAPI-ENTRYPOINTS : Option A — ``create_railway_app()`` vs ``create_modular_app()``,
sans ``create_app(deployment_mode=…)``. Les deux réutilisent les mêmes hooks :
``_add_security_middleware``, ``_mount_v51_workspace_bundle``, ``_register_common_routers``.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.dms_v51_mount import mount_v51_workspace_http_and_ws
from src.core.config import APP_TITLE, APP_VERSION, STATIC_DIR

logger = logging.getLogger(__name__)

# Réexport nom plan « bundle » — implémentation : dms_v51_mount
mount_v51_workspace_bundle = mount_v51_workspace_http_and_ws


def register_security_middleware_stack(
    app: FastAPI, *, log_prefix: str = "[app_factory]"
) -> None:
    """SecurityHeaders + Redis rate limit + TenantContext (ordre Starlette inversé)."""
    try:
        from src.couche_a.auth.middleware import (
            RedisRateLimitMiddleware,
            SecurityHeadersMiddleware,
            TenantContextMiddleware,
        )

        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(RedisRateLimitMiddleware)
        app.add_middleware(TenantContextMiddleware)
    except ImportError as exc:
        logging.getLogger(__name__).warning(
            "%s middlewares sécurité non chargés : %s", log_prefix, exc
        )


def _add_security_middleware(
    app: FastAPI, *, log_prefix: str = "[app_factory]"
) -> None:
    """Hook CTO — alias de ``register_security_middleware_stack``."""
    register_security_middleware_stack(app, log_prefix=log_prefix)


def _mount_v51_workspace_bundle(app: FastAPI) -> None:
    """Hook CTO — bundle V5.1 HTTP + WebSocket."""
    mount_v51_workspace_http_and_ws(app)


OPENAPI_RAILWAY_DESCRIPTION = (
    "Certaines routes renvoient volontairement HTTP 501 (Not Implemented), documentées "
    "dans OpenAPI et dans docs/audits/HTTP_501_PUBLIC_STATUS.md : "
    "`POST /api/scoring/calculate` (scoring réservé au pipeline FSM, pas d’appel direct) ; "
    "`POST /api/analyze` s’appuie sur l’extraction structurée des critères DAO — tant que "
    "cette étape n’est pas livrée (roadmap M10B), la réponse peut être 501 (comportement attendu)."
)


@asynccontextmanager
async def railway_lifespan(_app: FastAPI):
    """Lifespan production (Railway) — migrations optionnelles, schéma DB, fermeture pools."""
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
        from src.db import init_db_schema

        init_db_schema()
    if not _is_testing:
        try:
            from src.agent.semantic_router import warm_centroids

            await warm_centroids()
            _logger.info("[lifespan] Centroïdes pré-calculés (warm_centroids OK).")
        except Exception:
            _logger.warning(
                "[lifespan] warm_centroids échoué — sera calculé au premier appel agent."
            )
    yield
    try:
        from src.db.async_pool import close_async_pool
        from src.db.pool import close_pool

        close_pool()
        await close_async_pool()
    except Exception:
        _logger.exception("[lifespan] Erreur fermeture des pools DB au shutdown.")


def _register_common_routers(
    app: FastAPI, *, entry: Literal["modular", "railway"]
) -> None:
    """Hook CTO — pile de routeurs « cœur » avant le bundle V5.1 (ordre inchangé par entrée)."""
    if entry == "modular":
        from src.api.cases import router as cases_router
        from src.api.health import router as health_router
        from src.api.routers.committee_sessions import (
            router as committee_sessions_router,
        )
        from src.api.routers.documents import router as committee_documents_router
        from src.api.routers.market import router as market_router
        from src.api.routers.workspaces import router as workspaces_router
        from src.auth_router import router as auth_router
        from src.couche_a.criteria.router import router as criteria_router

        app.include_router(criteria_router)
        app.include_router(auth_router)
        app.include_router(cases_router)
        app.include_router(health_router)
        app.include_router(workspaces_router)
        app.include_router(committee_sessions_router)
        app.include_router(committee_documents_router)
        app.include_router(market_router)
        return

    # entry == "railway"
    from src.api import analysis, cases, documents, health
    from src.api.api_auth_router import router as api_auth_router
    from src.api.routes.extractions import router as extraction_router
    from src.api.routes.regulatory_profile import router as regulatory_profile_router
    from src.auth_router import router as auth_router
    from src.couche_a.committee.router import router as committee_router
    from src.couche_a.criteria.router import router as criteria_router
    from src.couche_a.routers import router as upload_router
    from src.couche_a.scoring import api as scoring_api

    app.include_router(api_auth_router)
    app.include_router(auth_router)
    app.include_router(upload_router)
    app.include_router(health.router)
    app.include_router(cases.router)
    app.include_router(documents.router)
    app.include_router(analysis.router)
    app.include_router(extraction_router)
    app.include_router(regulatory_profile_router)
    app.include_router(committee_router)
    app.include_router(scoring_api.router)
    app.include_router(criteria_router)


_DEFAULT_CORS_ORIGINS: tuple[str, ...] = (
    "https://frontend-v51-production.up.railway.app",
    "http://localhost:3000",
    "http://localhost:8000",
)


def _cors_allow_origins() -> list[str]:
    """Liste d'origines autorisées — E-27 : aucun item ``*`` ; préférer ``CORS_ORIGINS`` en prod."""
    raw = (os.environ.get("CORS_ORIGINS") or "").strip()
    if not raw:
        return list(_DEFAULT_CORS_ORIGINS)
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if any(origin == "*" for origin in origins):
        logger.warning(
            "[CORS] CORS_ORIGINS contient '*' refusé (E-27) — utilisation des origines par défaut"
        )
        return list(_DEFAULT_CORS_ORIGINS)
    return origins


def register_modular_cors(app: FastAPI) -> None:
    """CORS aligné frontend-v51 / dev local + Railway ``main:app``.

    À appeler **après** les autres ``add_middleware`` (rate limit, sécurité) : sous Starlette,
    le dernier middleware ajouté est le plus externe ; sinon les réponses court-circuitées
    (ex. 429) partent sans en-têtes CORS.

    Variables : ``CORS_ORIGINS`` (séparateur virgule, ex. ``https://app.example.com``).
    Si absente : défauts (frontend Railway historique + localhost).
    """
    allow_origins = _cors_allow_origins()
    if not allow_origins:
        logger.warning("[CORS] Liste d'origines vide — fallback défaut")
        allow_origins = list(_DEFAULT_CORS_ORIGINS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _load_optional_routers() -> dict[str, object | None]:
    """Routers optionnels ADR-M5-PRE-001 — même liste que l’ancien ``src/api/main.py``."""
    opt: dict[str, object | None] = {}
    try:
        from src.api.routes.extractions import router as extraction_router

        opt["extraction"] = extraction_router
    except ImportError as e:
        logger.warning(
            "[app_factory] router optionnel src.api.routes.extractions non chargé : %s",
            e,
        )
        opt["extraction"] = None

    try:
        from src.api.documents import router as documents_router

        opt["documents"] = documents_router
    except ImportError as e:
        logger.warning(
            "[app_factory] router optionnel src.api.documents non chargé : %s", e
        )
        opt["documents"] = None

    try:
        from src.api.analysis import router as analysis_router

        opt["analysis"] = analysis_router
    except ImportError as e:
        logger.warning(
            "[app_factory] router optionnel src.api.analysis non chargé : %s", e
        )
        opt["analysis"] = None

    try:
        from src.api.routers.mercuriale import router as mercuriale_router

        opt["mercuriale"] = mercuriale_router
    except ImportError as e:
        logger.warning(
            "[app_factory] router optionnel src.api.routers.mercuriale non chargé : %s",
            e,
        )
        opt["mercuriale"] = None

    try:
        from src.api.routers.price_check import router as price_check_router

        opt["price_check"] = price_check_router
    except ImportError as e:
        logger.warning(
            "[app_factory] router optionnel src.api.routers.price_check non chargé : %s",
            e,
        )
        opt["price_check"] = None

    try:
        from src.couche_a.pipeline.router import router as pipeline_a_router

        opt["pipeline_a"] = pipeline_a_router
    except ImportError as e:
        logger.warning(
            "[app_factory] router optionnel src.couche_a.pipeline non chargé : %s", e
        )
        opt["pipeline_a"] = None

    try:
        from src.couche_a.analysis_summary.router import (
            router as analysis_summary_router,
        )

        opt["analysis_summary"] = analysis_summary_router
    except ImportError as e:
        logger.warning(
            "[app_factory] router optionnel src.couche_a.analysis_summary non chargé : %s",
            e,
        )
        opt["analysis_summary"] = None

    try:
        from src.couche_a.committee.router import router as committee_router

        opt["committee"] = committee_router
    except ImportError as e:
        logger.warning(
            "[app_factory] router optionnel src.couche_a.committee non chargé : %s", e
        )
        opt["committee"] = None

    try:
        from src.geo.router import router as geo_router

        opt["geo"] = geo_router
    except ImportError as e:
        logger.warning("[app_factory] router optionnel src.geo non chargé : %s", e)
        opt["geo"] = None

    try:
        from src.vendors.router import router as vendors_router

        opt["vendors"] = vendors_router
    except ImportError as e:
        logger.warning("[app_factory] router optionnel src.vendors non chargé : %s", e)
        opt["vendors"] = None

    try:
        from src.api.routes.evaluation import router as m14_evaluation_router

        opt["m14_evaluation"] = m14_evaluation_router
    except ImportError as e:
        logger.warning(
            "[app_factory] router optionnel src.api.routes.evaluation non chargé : %s",
            e,
        )
        opt["m14_evaluation"] = None

    try:
        from src.api.routers.m16_comparative import router as m16_comparative_router

        opt["m16_comparative"] = m16_comparative_router
    except ImportError as e:
        logger.warning(
            "[app_factory] router optionnel src.api.routers.m16_comparative non chargé : %s",
            e,
        )
        opt["m16_comparative"] = None

    return opt


def _load_railway_optional_routers() -> list[object | None]:
    """Routers optionnels ``main.py`` (ordre du ``for`` inchangé)."""
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

    _m14_evaluation_router = None
    try:
        from src.api.routes.evaluation import router as _m14_evaluation_router_imp

        _m14_evaluation_router = _m14_evaluation_router_imp
    except ImportError as _e:
        logging.getLogger(__name__).warning(
            "[main] router optionnel src.api.routes.evaluation (M14) non chargé : %s",
            _e,
        )

    _case_timeline_router = None
    try:
        from src.api.views.case_timeline import router as _case_timeline_router_imp

        _case_timeline_router = _case_timeline_router_imp
    except ImportError as _e:
        logging.getLogger(__name__).warning(
            "[main] router optionnel src.api.views.case_timeline non chargé : %s", _e
        )

    _market_memory_router = None
    try:
        from src.api.views.market_memory_card import router as _market_memory_router_imp

        _market_memory_router = _market_memory_router_imp
    except ImportError as _e:
        logging.getLogger(__name__).warning(
            "[main] router optionnel src.api.views.market_memory_card non chargé : %s",
            _e,
        )

    _learning_console_router = None
    try:
        from src.api.views.learning_console import (
            router as _learning_console_router_imp,
        )

        _learning_console_router = _learning_console_router_imp
    except ImportError as _e:
        logging.getLogger(__name__).warning(
            "[main] router optionnel src.api.views.learning_console non chargé : %s", _e
        )

    _workspaces_router = None
    try:
        from src.api.routers.workspaces import router as _workspaces_router_imp

        _workspaces_router = _workspaces_router_imp
    except ImportError as _e:
        logging.getLogger(__name__).warning(
            "[main] router optionnel src.api.routers.workspaces (W1) non chargé : %s",
            _e,
        )

    _market_v420_router = None
    try:
        from src.api.routers.market import router as _market_v420_router_imp

        _market_v420_router = _market_v420_router_imp
    except ImportError as _e:
        logging.getLogger(__name__).warning(
            "[main] router optionnel src.api.routers.market (W2) non chargé : %s", _e
        )

    _committee_sessions_router = None
    try:
        from src.api.routers.committee_sessions import (
            router as _committee_sessions_router_imp,
        )

        _committee_sessions_router = _committee_sessions_router_imp
    except ImportError as _e:
        logging.getLogger(__name__).warning(
            "[main] router optionnel src.api.routers.committee_sessions (W3) non chargé : %s",
            _e,
        )

    _committee_documents_router = None
    try:
        from src.api.routers.documents import (
            router as _committee_documents_router_imp,
        )

        _committee_documents_router = _committee_documents_router_imp
    except ImportError as _e:
        logging.getLogger(__name__).warning(
            "[main] router optionnel src.api.routers.documents (BLOC7) non chargé : %s",
            _e,
        )

    _m16_comparative_router = None
    try:
        from src.api.routers.m16_comparative import (
            router as _m16_comparative_router_imp,
        )

        _m16_comparative_router = _m16_comparative_router_imp
    except ImportError as _e:
        logging.getLogger(__name__).warning(
            "[main] router optionnel src.api.routers.m16_comparative non chargé : %s",
            _e,
        )

    return [
        _geo_router,
        _vendors_router,
        _mercuriale_router,
        _price_check_router,
        _pipeline_a_router,
        _analysis_summary_router,
        _m14_evaluation_router,
        _case_timeline_router,
        _market_memory_router,
        _learning_console_router,
        _workspaces_router,
        _market_v420_router,
        _committee_sessions_router,
        _committee_documents_router,
        _m16_comparative_router,
    ]


def create_modular_app() -> FastAPI:
    """Application harness ``src.api.main`` — routers obligatoires + optionnels + V5.1."""
    optional = _load_optional_routers()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        active = [name for name, r in optional.items() if r is not None]
        inactive = [name for name, r in optional.items() if r is None]
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
        _is_testing = os.environ.get("TESTING", "false").lower() == "true"
        if not _is_testing:
            try:
                from src.agent.semantic_router import warm_centroids

                await warm_centroids()
                logger.info("[startup] Centroïdes pré-calculés (warm_centroids OK).")
            except Exception:
                logger.warning(
                    "[startup] warm_centroids échoué — sera calculé au premier appel agent."
                )
        yield

    app = FastAPI(
        title="DMS API",
        version="0.1.0",
        description="Decision Memory System — Constitution V3.3.2",
        lifespan=lifespan,
    )
    _add_security_middleware(app, log_prefix="[src.api.main]")
    register_modular_cors(app)
    _register_common_routers(app, entry="modular")
    _mount_v51_workspace_bundle(app)

    for router in optional.values():
        if router is not None:
            app.include_router(router)

    return app


def create_railway_app() -> FastAPI:
    """Application production Railway — équivalent historique de ``main.py``."""
    from src.ratelimit import init_rate_limit

    app = FastAPI(
        title=APP_TITLE,
        version=APP_VERSION,
        lifespan=railway_lifespan,
        description=OPENAPI_RAILWAY_DESCRIPTION,
    )

    @app.get("/health")
    def health_probe() -> dict[str, str]:
        """Sonde légère pour Railway / LB (souvent healthcheckPath=/health)."""
        return {"status": "ok", "service": "dms-api", "version": APP_VERSION}

    init_rate_limit(app)
    _add_security_middleware(app, log_prefix="[main]")
    # Dernier middleware = le plus externe (headers CORS aussi sur 429 / erreurs).
    register_modular_cors(app)
    _register_common_routers(app, entry="railway")
    _mount_v51_workspace_bundle(app)

    for _opt_router in _load_railway_optional_routers():
        if _opt_router is not None:
            app.include_router(_opt_router)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    return app
