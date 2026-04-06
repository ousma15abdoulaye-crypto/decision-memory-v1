"""Committee PV exports (JSON/PDF/XLSX) from sealed snapshot."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from src.couche_a.auth.dependencies import UserClaims, get_current_user
from src.couche_a.auth.workspace_access import require_workspace_access
from src.db import get_connection
from src.services.document_service import get_sealed_session
from src.services.xlsx_builder import build_xlsx_export
from src.utils.jinja_filters import build_jinja_env
from src.utils.json_utils import safe_json_dumps

router = APIRouter(prefix="/api/workspaces", tags=["documents-v421"])


def _render_pdf(doc: dict) -> bytes:
    from weasyprint import CSS, HTML

    base_dir = Path(__file__).resolve().parents[3]
    templates_dir = base_dir / "templates"
    static_dir = base_dir / "static"
    env = build_jinja_env(str(templates_dir))
    html = env.get_template("pv/_base.html.j2").render(
        snapshot=doc["pv_snapshot"],
        session_id=doc["session_id"],
        seal_hash=doc["seal_hash"],
        sealed_at=doc["sealed_at"],
    )
    base_url = static_dir.resolve().as_uri()
    return HTML(string=html, base_url=base_url).write_pdf(
        stylesheets=[CSS(filename=str(static_dir / "pv_design_system.css"))]
    )


@router.get("/{workspace_id}/committee/pv")
def export_committee_pv(
    workspace_id: str,
    format: str = Query(default="json", pattern="^(json|pdf|xlsx)$"),
    user: UserClaims = Depends(get_current_user),
):
    require_workspace_access(workspace_id, user)
    with get_connection() as conn:
        doc = get_sealed_session(conn, workspace_id)

    filename_root = f"pv_{workspace_id}_{doc['session_id']}"
    if format == "json":
        payload = {
            "workspace_id": workspace_id,
            "session_id": doc["session_id"],
            "seal_hash": doc["seal_hash"],
            "sealed_at": doc["sealed_at"],
            "pv_snapshot": doc["pv_snapshot"],
        }
        return Response(
            content=safe_json_dumps(payload, ensure_ascii=False),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{filename_root}.json"'
            },
        )

    if format == "pdf":
        pdf = _render_pdf(doc)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename_root}.pdf"'
            },
        )

    workbook = build_xlsx_export(
        snapshot=doc["pv_snapshot"],
        session_id=doc["session_id"],
        seal_hash=doc["seal_hash"],
        sealed_at=doc["sealed_at"],
    )
    return Response(
        content=workbook,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": f'attachment; filename="{filename_root}.xlsx"'},
    )
