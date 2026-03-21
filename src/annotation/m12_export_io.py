"""
Lecture des exports JSONL M12 pour pipelines aval (training, scoring, audit).

Formats supportés :
  - ``m12-v2`` : clé ``dms_annotation`` (+ ``export_ok``, ``ls_meta``, …)
  - ``m12-legacy`` : ancien ``ground_truth`` (pas de DMS complet)
  - ligne seule = document DMS brut (schéma v3.0.1d)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


def iter_m12_jsonl_lines(path: Path | str) -> Iterator[dict[str, Any]]:
    p = Path(path)
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def export_line_kind(line: dict[str, Any]) -> str:
    """``m12-v2`` | ``m12-legacy`` | ``raw_dms`` | ``unknown``."""
    ver = line.get("export_schema_version")
    if ver == "m12-v2":
        return "m12-v2"
    if ver == "m12-legacy":
        return "m12-legacy"
    if isinstance(line.get("couche_1_routing"), dict) and isinstance(
        line.get("couche_5_gates"), list
    ):
        return "raw_dms"
    return "unknown"


def dms_annotation_from_line(line: dict[str, Any]) -> dict[str, Any] | None:
    """
    Extrait le dict DMS v3.0.1d si présent.

    - m12-v2 : ``dms_annotation`` validé côté export (peut être null si erreurs).
    - raw_dms : la ligne entière.
    - m12-legacy / unknown : ``None``.
    """
    kind = export_line_kind(line)
    if kind == "m12-v2":
        dms = line.get("dms_annotation")
        return dms if isinstance(dms, dict) else None
    if kind == "raw_dms":
        return line
    return None


def iter_ok_dms_annotations(
    path: Path | str,
    *,
    only_export_ok: bool = True,
) -> Iterator[dict[str, Any]]:
    """
    Itère sur les annotations DMS utilisables en aval.

    Si only_export_ok (défaut), ne garde que les lignes **m12-v2** avec
    ``export_ok is True`` (lignes legacy ou DMS brut exclues).
    """
    for line in iter_m12_jsonl_lines(path):
        kind = export_line_kind(line)
        if only_export_ok:
            if kind != "m12-v2":
                continue
            if not line.get("export_ok", False):
                continue
        dms = dms_annotation_from_line(line)
        if dms is not None:
            yield dms
