"""DMS – FastAPI application entry-point.

Run with:  uvicorn backend.main:app --reload
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.couche_a.routes import router as couche_a_router
from backend.couche_b.routes import router as couche_b_router
from backend.system.auth import auth_router
from backend.system.db import init_db
from backend.system.firewall import FirewallMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle events."""
    await init_db()
    yield


app = FastAPI(
    title="Decision Memory System",
    version="0.2.0",
    lifespan=lifespan,
)

# ---- Middleware --------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(FirewallMiddleware)

# ---- Routers ----------------------------------------------------------------
app.include_router(auth_router)
app.include_router(couche_a_router)
app.include_router(couche_b_router)


# ---- Health check ------------------------------------------------------------
@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ---- Static files (frontend) ------------------------------------------------
# Must be mounted last — catch-all "/" would shadow API routes defined after it.
_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
