"""Pipeline V5 — Semaine 1 : run bout-en-bout (bundles → M13 → M14 → bridge)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.couche_a.auth.workspace_access import require_workspace_access
from src.services.pipeline_v5_service import PipelineV5Result, run_pipeline_v5

router = APIRouter(prefix="/api/workspaces", tags=["pipeline-v5"])


def _workspace_access_guard(
    workspace_id: str,
    user: UserClaims = Depends(get_current_user),
) -> None:
    require_workspace_access(workspace_id, user)


@router.post(
    "/{workspace_id}/run-pipeline",
    response_model=PipelineV5Result,
)
def post_run_pipeline_v5(
    workspace_id: str,
    force_m14: bool = Query(
        False,
        description="Si true, réévalue M14 même si un brouillon existe.",
    ),
    _access: None = Depends(_workspace_access_guard),
) -> PipelineV5Result:
    """Enchaîne extraction offres depuis bundles, M13, M14, bridge M16."""
    return run_pipeline_v5(workspace_id, force_m14=force_m14)
