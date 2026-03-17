"""
Prompts DMS — annotation backend v3.0.1d
Pattern : fichier texte pur — zéro f-string — zéro risque SyntaxError.
Chemin absolu — zéro dépendance PYTHONPATH Railway.
ADR-015 — 2026-03-16
"""

from pathlib import Path

_PROMPT_DIR = Path(__file__).parent

SYSTEM_PROMPT: str = (_PROMPT_DIR / "system_prompt.txt").read_text(encoding="utf-8")

__all__ = ["SYSTEM_PROMPT"]
