"""
M13 — Regulatory Profile API (lecture métadonnées ; exécution via pipeline Pass 2A).
"""

from __future__ import annotations

from fastapi import APIRouter

from src.annotation.orchestrator import use_pass_2a

router = APIRouter(prefix="/api/m13", tags=["m13-regulatory"])


@router.get("/status")
def m13_status() -> dict[str, str | bool]:
    """Indique si Pass 2A est activé côté configuration."""
    return {
        "pass_2a_enabled": use_pass_2a(),
        "module": "M13 Regulatory Profile Engine",
    }
