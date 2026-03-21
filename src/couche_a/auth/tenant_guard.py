"""Tenant isolation guard — Règle R7 multi-tenant enforcement.

Utilitaires pour garantir l'isolation des données par organisation.

Principes :
  - org_id est OBLIGATOIRE sur toutes les requêtes TENANT_SCOPED
  - GLOBAL_CORE tables (geo_master, procurement_dict_items, imc_sources)
    ne requièrent PAS org_id
  - Aucune exception silencieuse — échec explicite et bruyant

ADR : V4.1.0 — Data Classification (GLOBAL_CORE / TENANT_SCOPED / TENANT_OVERLAY)
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, status

from src.couche_a.auth.dependencies import UserClaims

logger = logging.getLogger(__name__)

# Tables classifiées TENANT_SCOPED — org_id obligatoire
TENANT_SCOPED_TABLES: frozenset[str] = frozenset(
    {
        "cases",
        "documents",
        "offers",
        "offer_extractions",
        "dao_criteria",
        "committees",
        "committee_members",
        "committee_decisions",
        "committee_events",
        "decision_snapshots",
        "decision_history",
        "pipeline_runs",
        "pipeline_steps",
        "vendors",
        "vendors_sensitive_data",
        "extraction_jobs",
        "market_surveys",
        "artifacts",
        "memory_entries",
    }
)

# Tables classifiées GLOBAL_CORE — org_id NON requis
GLOBAL_CORE_TABLES: frozenset[str] = frozenset(
    {
        "geo_master",
        "procurement_dict_items",
        "procurement_dict_aliases",
        "imc_sources",
        "imc_entries",
        "market_signals_v2",
        "seasonal_patterns",
        "zone_context_registry",
        "geo_price_corridors",
        "mercuriale_snapshots",
        "mercuriale_items",
    }
)


def require_org_id(user: UserClaims) -> str:
    """Extrait org_id du UserClaims ou lève 403.

    À utiliser dans tout endpoint accédant à des données TENANT_SCOPED.

    Raises:
        HTTPException 403: org_id absent du token JWT.
    """
    if user.org_id is None:
        logger.warning(
            "Accès refusé: org_id absent du token JWT pour user_id=%s",
            user.user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "org_id absent du token. "
                "Ré-authentification nécessaire avec contexte organisation."
            ),
        )
    return user.org_id


def is_tenant_scoped(table_name: str) -> bool:
    """Retourne True si la table est classifiée TENANT_SCOPED."""
    return table_name in TENANT_SCOPED_TABLES
