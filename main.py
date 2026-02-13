import json
import os
import re
import uuid

# Load .env before db import (DATABASE_URL required)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure logging pour resilience patterns
from src.logging_config import configure_logging
configure_logging()

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from src.db import get_connection, db_execute, db_execute_one, db_fetchall, init_db_schema
from src.couche_a.routers import router as upload_router
from src.auth_router import router as auth_router
from src.ratelimit import init_rate_limit, limiter
from src.auth import CurrentUser
from src.core.config import (
    APP_TITLE, APP_VERSION, BASE_DIR, DATA_DIR, UPLOADS_DIR, OUTPUTS_DIR, 
    STATIC_DIR, INVARIANTS
)
from src.core.models import (
    CaseCreate, AnalyzeRequest, DecideRequest,
    CBATemplateSchema, DAOCriterion, OfferSubtype, SupplierPackage
)
from src.api import health, cases, documents, analysis

# ❌ REMOVED: from src.couche_a.procurement import router as procurement_router (M2-Extended)

# =========================
# Database — PostgreSQL only (schema created on startup)
# =========================
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    init_db_schema()
    yield

app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)

# Initialize rate limiting
init_rate_limit(app)

# Include routers
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(health.router)
app.include_router(cases.router)
app.include_router(documents.router)
app.include_router(analysis.router)
# ❌ REMOVED: app.include_router(procurement_router) (M2-Extended)

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