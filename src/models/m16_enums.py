"""
Enums métier M16 — Python pur (aucun ORM).

Alignés sur les CHECK / usages réels (migrations 081–084, schémas API).
"""

from __future__ import annotations

from enum import StrEnum


class TargetType(StrEnum):
    """Cible de cadrage M16 (routes /targets/.../frame)."""

    workspace = "workspace"
    session = "session"
    bundle = "bundle"


class ThreadStatus(StrEnum):
    """Cycle de vie d'un thread de délibération (083)."""

    open = "open"
    archived = "archived"


class ClarificationStatus(StrEnum):
    """Statut demande de clarification (083)."""

    open = "open"
    answered = "answered"
    withdrawn = "withdrawn"


class AssessmentStatus(StrEnum):
    """Statut CriterionAssessment (082)."""

    draft = "draft"
    under_review = "under_review"
    validated = "validated"
    contested = "contested"
    not_applicable = "not_applicable"


class DaoScoringMode(StrEnum):
    """Modes de scoring dao_criteria.m16_scoring_mode (081)."""

    numeric = "numeric"
    qualitative = "qualitative"
    binary = "binary"
    not_applicable = "not_applicable"


class PriceSignal(StrEnum):
    """Signaux visuels pour cellules prix et assessments (moteur unifié)."""

    green = "green"
    yellow = "yellow"
    bell = "bell"
    red = "red"
