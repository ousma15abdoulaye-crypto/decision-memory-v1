"""
Client HTTP minimal Label Studio — export projet et tâche unitaire.
"""

from __future__ import annotations

from typing import Any

import requests


def fetch_project_meta(project_id: int, ls_url: str, ls_key: str) -> dict[str, Any]:
    """Métadonnées projet (léger) — pour vérifier URL + token avant export complet."""
    headers = {"Authorization": f"Token {ls_key}"}
    url = f"{ls_url.rstrip('/')}/api/projects/{project_id}/"
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict):
        raise ValueError("réponse projet non-objet")
    return data


def fetch_annotations(project_id: int, ls_url: str, ls_key: str) -> list[dict]:
    """Export JSON complet d’un projet (même contrat que l’UI Export)."""
    headers = {"Authorization": f"Token {ls_key}"}
    url = f"{ls_url.rstrip('/')}/api/projects/{project_id}/export"
    r = requests.get(
        url,
        headers=headers,
        params={"exportType": "JSON"},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def fetch_task(ls_url: str, ls_key: str, task_id: int) -> dict[str, Any]:
    """Détail d’une tâche (inclut souvent ``annotations``)."""
    headers = {"Authorization": f"Token {ls_key}"}
    url = f"{ls_url.rstrip('/')}/api/tasks/{task_id}/"
    r = requests.get(url, headers=headers, timeout=60)
    r.raise_for_status()
    return r.json()


def pick_annotation(task: dict, annotation_id: int | None) -> dict | None:
    """Choisit l’annotation ciblée ou la dernière présente."""
    anns = task.get("annotations") or []
    if not anns:
        return None
    if annotation_id is not None:
        for a in anns:
            if a.get("id") == annotation_id:
                return a
    return anns[-1]


def resolve_task_and_annotation(
    payload: dict[str, Any],
    ls_url: str,
    ls_key: str,
) -> tuple[dict, dict] | None:
    """
    Retourne (task, annotation) au format attendu par ``ls_annotation_to_m12_v2_line``.

    Utilise le corps webhook si ``task.data`` + ``annotation.result`` présents, sinon API.
    """
    ls_url = ls_url.rstrip("/")
    task = payload.get("task")
    ann = payload.get("annotation")
    task_id: int | None = None
    if isinstance(task, dict) and task.get("id") is not None:
        task_id = int(task["id"])
    if task_id is None and payload.get("task_id") is not None:
        task_id = int(payload["task_id"])

    ann_id: int | None = None
    if isinstance(ann, dict) and ann.get("id") is not None:
        ann_id = int(ann["id"])

    if (
        isinstance(task, dict)
        and isinstance(ann, dict)
        and ann.get("result") is not None
        and isinstance(task.get("data"), dict)
    ):
        return task, ann

    if task_id is None or not ls_key or not ls_url:
        return None

    full_task = fetch_task(ls_url, ls_key, task_id)
    picked = pick_annotation(full_task, ann_id)
    if picked is None:
        return None
    return full_task, picked
