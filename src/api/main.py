# src/api/main.py
"""
Application FastAPI — DMS
Constitution V3.3.2
"""
from fastapi import FastAPI

from src.api.routes.extractions import router as extraction_router

app = FastAPI(
    title="DMS API",
    version="0.1.0",
)

app.include_router(extraction_router)
