# src/api/main.py
"""
Application FastAPI — DMS (harness tests / OpenAPI parité).

Politique routers : ADR-M5-PRE-001 §D1.3 — montage centralisé dans
``src.api.app_factory.create_modular_app``.
"""

from src.api.app_factory import create_modular_app

app = create_modular_app()
