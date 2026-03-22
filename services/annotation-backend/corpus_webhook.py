"""
Traitement asynchrone webhook Label Studio → ligne m12-v2 → CorpusSink.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from corpus_sink import CorpusSink, build_sink_from_env
from ls_client import resolve_task_and_annotation
from m12_export_line import annotation_status_from_result, ls_annotation_to_m12_v2_line

logger = logging.getLogger(__name__)


def _parse_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "")
    try:
        return int(raw) if raw.strip() else default
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name, "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


def _enforce_validated_qa() -> bool:
    return _env_bool("M12_EXPORT_ENFORCE_VALIDATED_QA", True)


def _require_ls_attestations() -> bool:
    return _env_bool("M12_EXPORT_REQUIRE_LS_ATTESTATIONS", False)


def _project_id_from_payload(payload: dict[str, Any], task: dict[str, Any]) -> int:
    """project_id depuis webhook, tâche LS, ou env."""
    proj = payload.get("project") or {}
    if isinstance(proj, dict) and proj.get("id") is not None:
        return int(proj["id"])
    tproj = task.get("project") if isinstance(task, dict) else None
    if isinstance(tproj, dict) and tproj.get("id") is not None:
        return int(tproj["id"])
    if isinstance(tproj, int):
        return tproj
    return _parse_int_env("LABEL_STUDIO_PROJECT_ID", 0)


def _allowed_action(action: str) -> bool:
    raw = os.environ.get(
        "CORPUS_WEBHOOK_ACTIONS",
        "ANNOTATION_CREATED,ANNOTATION_UPDATED",
    )
    allowed = {a.strip() for a in raw.split(",") if a.strip()}
    return action in allowed


def _status_filter_passes(ann: dict) -> bool:
    filt = os.environ.get("CORPUS_WEBHOOK_STATUS_FILTER", "").strip()
    if not filt:
        return True
    status = (annotation_status_from_result(ann) or "").strip()
    return status == filt


def _label_studio_url() -> str:
    """``LABEL_STUDIO_URL`` ou repli ``LS_URL`` (Railway / déploiements existants)."""
    u = os.environ.get("LABEL_STUDIO_URL", "").strip().rstrip("/")
    return u or os.environ.get("LS_URL", "").strip().rstrip("/")


def _label_studio_api_key() -> str:
    """``LABEL_STUDIO_API_KEY`` ou repli ``LS_API_KEY``."""
    k = os.environ.get("LABEL_STUDIO_API_KEY", "").strip()
    return k or os.environ.get("LS_API_KEY", "").strip()


def process_label_studio_webhook_for_corpus(
    payload: dict[str, Any],
    sink: CorpusSink | None = None,
) -> None:
    """
    Construit une ligne m12-v2 et l’écrit dans le sink.

    Ne lève pas — loggue les erreurs (appelé depuis BackgroundTasks).
    """
    if not _env_bool("CORPUS_WEBHOOK_ENABLED", False):
        return

    action = str(payload.get("action") or "")
    if not _allowed_action(action):
        return

    ls_url = _label_studio_url()
    ls_key = _label_studio_api_key()
    if not ls_url or not ls_key:
        logger.warning(
            "[CORPUS] Webhook activé mais LABEL_STUDIO_URL ou LS_URL / "
            "LABEL_STUDIO_API_KEY ou LS_API_KEY manquants — tentative de résolution à partir du payload uniquement"
        )

    resolved = resolve_task_and_annotation(payload, ls_url, ls_key)
    if resolved is None:
        if not ls_url or not ls_key:
            logger.warning(
                "[CORPUS] Impossible de résoudre task/annotation sans accès à l’API Label Studio — skip"
            )
        else:
            logger.warning("[CORPUS] Impossible de résoudre task/annotation — skip")
        return

    task, ann = resolved
    if not _status_filter_passes(ann):
        logger.info(
            "[CORPUS] Filtré par status (CORPUS_WEBHOOK_STATUS_FILTER) — task_id=%s",
            task.get("id"),
        )
        return

    project_id = _project_id_from_payload(payload, task)
    if project_id == 0:
        logger.warning(
            "[CORPUS] project_id=0 — définir project.id dans le webhook ou LABEL_STUDIO_PROJECT_ID"
        )

    line = ls_annotation_to_m12_v2_line(
        ann,
        task,
        project_id,
        enforce_validated_qa=_enforce_validated_qa(),
        require_ls_attestations=_require_ls_attestations(),
    )

    sink = sink or build_sink_from_env()
    try:
        sink.append_line(line)
        logger.info(
            "[CORPUS] Écrit task_id=%s ann_id=%s export_ok=%s hash=%s",
            line.get("ls_meta", {}).get("task_id"),
            line.get("ls_meta", {}).get("annotation_id"),
            line.get("export_ok"),
            line.get("content_hash"),
        )
    except Exception as exc:
        logger.error(
            "[CORPUS] Écriture échouée : %s — %s",
            type(exc).__name__,
            exc,
        )
