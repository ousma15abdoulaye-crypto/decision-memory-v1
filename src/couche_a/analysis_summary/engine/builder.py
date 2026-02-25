"""
src/couche_a/analysis_summary/engine/builder.py

Construction des sections génériques depuis CAS v1.
MG-03 OPTION A : entrée = dict (pas CaseAnalysisSnapshot)
  → découplage complet — pas d'import pipeline/models.py
  → validation locale des clés requises

INV-AS6  : zéro logique client-spécifique
INV-AS10 : sections neutres — pas de champs de jugement
INV-AS12 : zéro import couche présentation/export
"""

from __future__ import annotations

from typing import Any

from src.couche_a.analysis_summary.engine.models import SummarySection

# Clés requises dans le CAS dict pour construire des sections valides
_CAS_REQUIRED_KEYS: frozenset[str] = frozenset(
    {
        "cas_version",
        "case_id",
        "pipeline",
        "readiness",
        "criteria",
        "scoring",
        "documents",
        "normalization",
    }
)

# Version CAS supportée par ce builder
_SUPPORTED_CAS_VERSION = "v1"


def build_summary(cas: dict[str, Any]) -> list[SummarySection]:
    """
    Construit les sections génériques depuis CAS v1 désérialisé.

    MG-03 OPTION A : entrée = dict — pas d'import pipeline/models.py.
    Validation locale des clés requises avant toute construction.

    Sections produites (toujours dans cet ordre) :
      1. context
      2. offers
      3. criteria
      4. scoring
      5. data_quality
      6. readiness

    Règles :
      - données absentes → warning explicite, pas d'invention
      - zéro logique client-spécifique
      - zéro accès DB
      - zéro import couche présentation

    Retourne : list[SummarySection] (peut être vide si CAS vide)
    """
    _validate_cas_structure(cas)

    sections: list[SummarySection] = []

    sections.append(_build_context_section(cas))
    sections.append(_build_offers_section(cas))
    sections.append(_build_criteria_section(cas))
    sections.append(_build_scoring_section(cas))
    sections.append(_build_data_quality_section(cas))
    sections.append(_build_readiness_section(cas))

    return sections


# ─────────────────────────────────────────────────────────────
# VALIDATION LOCALE (MG-03 OPTION A)
# ─────────────────────────────────────────────────────────────


def _validate_cas_structure(cas: dict[str, Any]) -> None:
    """
    Valide les clés requises et la version CAS supportée.
    Raises ValueError si structure incompatible.
    MG-03 OPTION A — pas d'import CaseAnalysisSnapshot.
    """
    if not isinstance(cas, dict):
        raise ValueError(f"CAS doit être un dict — reçu {type(cas).__name__}")

    cas_version = cas.get("cas_version")
    if cas_version != _SUPPORTED_CAS_VERSION:
        raise ValueError(
            f"CAS version non supportée : '{cas_version}'. "
            f"Attendu : '{_SUPPORTED_CAS_VERSION}'. INV-AS4."
        )

    missing = _CAS_REQUIRED_KEYS - cas.keys()
    if missing:
        raise ValueError(
            f"CAS v1 incomplet — clés manquantes : {sorted(missing)}. "
            f"Contrat ADR-0012."
        )


# ─────────────────────────────────────────────────────────────
# CONSTRUCTEURS DE SECTIONS (génériques, neutres)
# ─────────────────────────────────────────────────────────────


def _build_context_section(cas: dict[str, Any]) -> SummarySection:
    """Section context : informations du dossier."""
    case_ctx = cas.get("case_context", {})
    pipeline = cas.get("pipeline", {})
    warnings = []

    if not case_ctx:
        warnings.append("case_context absent ou vide dans CAS v1")

    return SummarySection(
        section_type="context",
        title="Contexte du dossier",
        content={
            "case_id": cas.get("case_id"),
            "case_type": case_ctx.get("case_type"),
            "title": case_ctx.get("title"),
            "currency": case_ctx.get("currency"),
            "pipeline_mode": pipeline.get("mode"),
            "pipeline_status": pipeline.get("status"),
            "generated_at": cas.get("generated_at"),
        },
        warnings=warnings,
    )


def _build_offers_section(cas: dict[str, Any]) -> SummarySection:
    """Section offers : présence et décompte des offres."""
    docs = cas.get("documents", {})
    warnings = []

    offers_count = docs.get("offers_count", 0)
    if offers_count == 0:
        warnings.append("Aucune offre fournisseur dans le dossier")

    return SummarySection(
        section_type="offers",
        title="Offres fournisseurs",
        content={
            "dao_present": docs.get("dao_present", False),
            "offers_count": offers_count,
            "class_a_compatible": docs.get("class_a_compatible"),
        },
        warnings=warnings,
    )


def _build_criteria_section(cas: dict[str, Any]) -> SummarySection:
    """Section criteria : critères d'évaluation."""
    criteria = cas.get("criteria", {})
    warnings = []

    count_total = criteria.get("count_total", 0)
    if count_total == 0:
        warnings.append("Aucun critère d'évaluation dans le dossier")

    cats = criteria.get("categories", {})

    return SummarySection(
        section_type="criteria",
        title="Critères d'évaluation",
        content={
            "count_total": count_total,
            "count_eliminatory": criteria.get("count_eliminatory", 0),
            "categories": {
                "commercial": cats.get("commercial", 0),
                "capacity": cats.get("capacity", 0),
                "sustainability": cats.get("sustainability", 0),
                "essentials": cats.get("essentials", 0),
            },
        },
        warnings=warnings,
    )


def _build_scoring_section(cas: dict[str, Any]) -> SummarySection:
    """Section scoring : statut et référence du run de scoring."""
    scoring = cas.get("scoring", {})
    warnings = []

    score_status = scoring.get("status", "blocked")
    if score_status != "ok":
        warnings.append(f"Scoring non disponible — statut : '{score_status}'")

    return SummarySection(
        section_type="scoring",
        title="Scoring des offres",
        content={
            "status": score_status,
            "score_run_id": scoring.get("score_run_id"),
            "scoring_version": scoring.get("scoring_version"),
        },
        warnings=warnings,
    )


def _build_data_quality_section(cas: dict[str, Any]) -> SummarySection:
    """Section data_quality : normalisation et qualité des données."""
    norm = cas.get("normalization", {})
    warnings = []

    norm_status = norm.get("status", "unavailable")
    if norm_status != "ok":
        warnings.append(f"Normalisation non complète — statut : '{norm_status}'")

    coverage = norm.get("coverage_ratio")
    if coverage is not None and float(coverage) < 0.8:
        warnings.append(f"Couverture normalisation faible : {coverage:.1%}")

    return SummarySection(
        section_type="data_quality",
        title="Qualité des données",
        content={
            "normalization_status": norm_status,
            "coverage_ratio": coverage,
            "human_flags_count": norm.get("human_flags_count"),
        },
        warnings=warnings,
    )


def _build_readiness_section(cas: dict[str, Any]) -> SummarySection:
    """Section readiness : état de préparation à l'export."""
    readiness = cas.get("readiness", {})
    warnings = []

    blockers = readiness.get("blockers", [])
    if blockers:
        warnings.append(f"Blocages actifs : {blockers}")

    return SummarySection(
        section_type="readiness",
        title="État de préparation",
        content={
            "analysis_ready": readiness.get("analysis_ready", False),
            "export_ready": readiness.get("export_ready", False),
            "cba_ready": readiness.get("cba_ready", False),
            "pv_ready": readiness.get("pv_ready", False),
            "blockers": blockers,
        },
        warnings=warnings,
    )
