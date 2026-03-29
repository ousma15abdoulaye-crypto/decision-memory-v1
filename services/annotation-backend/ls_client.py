"""
Client HTTP minimal Label Studio — export projet et tâche unitaire.

Personal Access Token (JWT, doc LS) : ``POST /api/token/refresh`` avec
``{"refresh": "<PAT>"}`` puis ``Authorization: Bearer <access>``.
Legacy token : ``Authorization: Token <clé>``.
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests

# refresh PAT (JWT) -> (access, monotonic_expiry) — access ~5 min côté LS
_pat_access_cache: dict[str, tuple[str, float]] = {}


def _tls_verify() -> bool:
    """TLS strict par défaut ; ``LABEL_STUDIO_SSL_VERIFY=0`` si chaîne de certificats locale / proxy casse la vérif."""
    v = (os.environ.get("LABEL_STUDIO_SSL_VERIFY") or "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def _looks_like_ls_jwt_pat(key: str) -> bool:
    s = key.strip()
    parts = s.split(".")
    return len(parts) == 3 and all(parts) and parts[0].startswith("eyJ")


def _fetch_access_from_refresh(ls_url: str, refresh: str) -> str:
    base = ls_url.rstrip("/")
    body = {"refresh": refresh.strip()}
    last: requests.Response | None = None
    for path in ("/api/token/refresh", "/api/token/refresh/"):
        resp = requests.post(
            f"{base}{path}",
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=30,
            verify=_tls_verify(),
        )
        last = resp
        if resp.status_code == 404:
            continue
        resp.raise_for_status()
        data = resp.json()
        access = data.get("access")
        if isinstance(access, str) and access.strip():
            return access.strip()
        raise ValueError("réponse /api/token/refresh sans champ access")
    if last is not None:
        last.raise_for_status()
    raise RuntimeError("impossible d'atteindre /api/token/refresh")


def _cached_access(ls_url: str, refresh: str) -> str:
    r = refresh.strip()
    now = time.monotonic()
    hit = _pat_access_cache.get(r)
    if hit and now < hit[1]:
        return hit[0]
    access = _fetch_access_from_refresh(ls_url, r)
    _pat_access_cache[r] = (access, now + 240.0)
    return access


def _ls_auth_headers(ls_url: str, ls_key: str) -> dict[str, str]:
    k = ls_key.strip()
    if os.environ.get("LABEL_STUDIO_LEGACY_TOKEN", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return {"Authorization": f"Token {k}"}
    if _looks_like_ls_jwt_pat(k):
        access = _cached_access(ls_url, k)
        return {"Authorization": f"Bearer {access}"}
    return {"Authorization": f"Token {k}"}


def _http_get(
    ls_url: str,
    ls_key: str,
    path: str,
    *,
    params: dict[str, str] | None = None,
    timeout: int = 30,
) -> requests.Response:
    """GET avec retry si access JWT expiré (401) pour PAT."""
    base = ls_url.rstrip("/")
    url = f"{base}{path}"
    for attempt in range(2):
        headers = _ls_auth_headers(ls_url, ls_key)
        r = requests.get(
            url, headers=headers, params=params, timeout=timeout, verify=_tls_verify()
        )
        if (
            r.status_code == 401
            and attempt == 0
            and _looks_like_ls_jwt_pat(ls_key.strip())
        ):
            _pat_access_cache.pop(ls_key.strip(), None)
            continue
        return r
    return r


def fetch_project_meta(project_id: int, ls_url: str, ls_key: str) -> dict[str, Any]:
    """Métadonnées projet (léger) — pour vérifier URL + token avant export complet."""
    r = _http_get(ls_url, ls_key, f"/api/projects/{project_id}/", timeout=30)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict):
        raise ValueError("réponse projet non-objet")
    return data


def fetch_annotations(
    project_id: int,
    ls_url: str,
    ls_key: str,
    *,
    download_all_tasks: bool | None = None,
) -> list[dict]:
    """Export JSON d’un projet (même contrat que l’UI Export).

    ``download_all_tasks`` :
    - ``False`` : ne demande que les tâches ayant des annotations (souvent le défaut LS).
    - ``True`` : inclut aussi les tâches sans annotation.
    - ``None`` : ne passe pas le paramètre (comportement serveur par défaut).
    """
    params: dict[str, str] = {"exportType": "JSON"}
    if download_all_tasks is not None:
        params["download_all_tasks"] = "true" if download_all_tasks else "false"
    r = _http_get(
        ls_url,
        ls_key,
        f"/api/projects/{project_id}/export",
        params=params,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def fetch_task(ls_url: str, ls_key: str, task_id: int) -> dict[str, Any]:
    """Détail d’une tâche (inclut souvent ``annotations``)."""
    r = _http_get(ls_url, ls_key, f"/api/tasks/{task_id}/", timeout=60)
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
