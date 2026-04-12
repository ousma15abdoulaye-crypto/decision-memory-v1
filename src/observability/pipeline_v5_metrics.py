"""Métriques pipeline V5 — compteurs / histogrammes Prometheus (optionnel).

Si ``prometheus_client`` n'est pas installé, les fonctions deviennent des no-op
pour ne pas casser les environnements minimalistes.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_PROM: Any = None
_assessments: Any = None
_duration: Any = None
_empty: Any = None
_mistral_missing: Any = None
_pass1_hitl_bypass: Any = None

try:
    from prometheus_client import Counter, Histogram

    _assessments = Counter(
        "dms_pipeline_assessments_created_total",
        "Assessments créés ou mis à jour par le pipeline V5 (bridge M14)",
        ["workspace_id"],
    )
    _duration = Histogram(
        "dms_pipeline_duration_seconds",
        "Durée totale run_pipeline_v5 (secondes)",
        ["workspace_id"],
        buckets=(1.0, 5.0, 15.0, 30.0, 60.0, 120.0, 300.0, 600.0),
    )
    _empty = Counter(
        "dms_pipeline_empty_assessments_total",
        "Runs pipeline V5 terminés avec 0 assessment (alerte)",
        ["workspace_id"],
    )
    _mistral_missing = Counter(
        "dms_pipeline_mistral_key_missing_total",
        "Démarrages pipeline / checks avec MISTRAL_API_KEY absente",
        ["phase"],
    )
    _pass1_hitl_bypass = Counter(
        "dms_pass1_hitl_bypass_total",
        "Pass -1 : contournement interrupt() HITL (DMS_PASS1_HEADLESS actif)",
        ["workspace_id"],
    )
    _PROM = True
except ImportError:
    logger.debug(
        "[METRICS] prometheus_client absent — métriques pipeline V5 désactivées"
    )


def observe_pass1_hitl_bypass(*, workspace_id: str) -> None:
    """Trace explicite quand le Pass -1 évite ``interrupt()`` (mode headless).

    À utiliser uniquement lorsque ``DMS_PASS1_HEADLESS`` est vrai — jamais comme
    comportement métier silencieux en prod. Le préfixe de log ``PASS1_HITL_BYPASS``
    sert au filtrage Loki / alertes.
    """
    wid = (workspace_id or "").strip() or "unknown"
    logger.warning(
        "[PASS1_HITL_BYPASS] DMS_PASS1_HEADLESS actif — HITL LangGraph court-circuité "
        "(bundles incomplets non bloquants) — workspace_id=%s",
        wid,
    )
    if _PROM and _pass1_hitl_bypass is not None:
        _pass1_hitl_bypass.labels(workspace_id=wid).inc()  # type: ignore[union-attr]


def observe_mistral_key_missing(phase: str = "pipeline_v5") -> None:
    """Incrément quand la clé Mistral est absente (offline / TIER 4)."""
    logger.warning(
        "[DMS] MISTRAL_API_KEY absente — phase=%s — extraction en mode dégradé (TIER 4)",
        phase,
    )
    if _PROM and _mistral_missing is not None:
        _mistral_missing.labels(phase=phase).inc()  # type: ignore[union-attr]


def observe_pipeline_v5_run(
    *,
    workspace_id: str,
    duration_seconds: float,
    assessments_created: int,
) -> None:
    """Enregistre durée, volume d'assessments et cas vide (alerte)."""
    wid = workspace_id or "unknown"
    if _PROM and _duration is not None:
        _duration.labels(workspace_id=wid).observe(duration_seconds)  # type: ignore[union-attr]
    if _PROM and _assessments is not None:
        _assessments.labels(workspace_id=wid).inc(assessments_created)  # type: ignore[union-attr]
    if assessments_created == 0:
        logger.error(
            "[PIPELINE-V5-METRICS] 0 assessment créé — workspace_id=%s — "
            "dms_pipeline_empty_assessments_total",
            wid,
        )
        if _PROM and _empty is not None:
            _empty.labels(workspace_id=wid).inc()  # type: ignore[union-attr]
