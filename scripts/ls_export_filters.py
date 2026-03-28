"""
Filtres communs export Label Studio (autosave + export JSONL).

« Terminé » côté LS : annotation soumise (non annulée), avec au moins un champ
dans ``result``. Optionnellement restreindre au choix ``annotation_status`` (ex.
``annotated_validated``) pour ne revoir que le travail validé.
"""

from __future__ import annotations

from typing import Any


def _annotation_status_from_ann(ann: dict[str, Any]) -> str | None:
    for r in ann.get("result") or []:
        if r.get("from_name") != "annotation_status":
            continue
        val = r.get("value") or {}
        if isinstance(val, dict) and "choices" in val:
            choices = val["choices"]
            return str(choices[0]).strip() if choices else None
    return None


def filter_export_tasks(
    tasks: list[dict[str, Any]],
    *,
    only_finished: bool,
    require_annotation_status: str | None = None,
) -> list[dict[str, Any]]:
    """
    Retourne une copie des tâches avec ``annotations`` filtrées.

    - ``only_finished`` : ignore ``was_cancelled`` et annotations sans ``result``.
    - ``require_annotation_status`` : garde seulement les annotations dont le choix
      LS ``annotation_status`` est exactement cette chaîne (après strip).
    """
    if not only_finished and not (require_annotation_status or "").strip():
        return tasks

    req = (require_annotation_status or "").strip()
    out: list[dict[str, Any]] = []

    for task in tasks:
        if not isinstance(task, dict):
            continue
        anns = task.get("annotations") or []
        kept: list[dict[str, Any]] = []
        for ann in anns:
            if not isinstance(ann, dict):
                continue
            if only_finished:
                if ann.get("was_cancelled") is True:
                    continue
                if not (ann.get("result") or []):
                    continue
            if req:
                st = _annotation_status_from_ann(ann) or ""
                if st != req:
                    continue
            kept.append(ann)
        if not kept:
            continue
        t2 = dict(task)
        t2["annotations"] = kept
        out.append(t2)

    return out
