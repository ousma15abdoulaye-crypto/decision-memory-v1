"""Garde-fou : paliers DGMP Pass 1A = YAML (pas de constantes Python parallèles)."""

from __future__ import annotations

import inspect
from pathlib import Path

from src.procurement import procedure_rules_dgmp_mali as dgmp_mod
from src.procurement.procedure_rules_dgmp_mali import determine_dgmp_procedure_tier


def test_determine_dgmp_uses_regulatory_config_loader_only() -> None:
    src = inspect.getsource(determine_dgmp_procedure_tier)
    assert "RegulatoryConfigLoader" in src
    assert "_DGMP_THRESHOLDS_FCFA" not in src


def test_no_legacy_threshold_tuple_constant_in_module_file() -> None:
    path = Path(dgmp_mod.__file__)
    assert path.name == "procedure_rules_dgmp_mali.py"
    text = path.read_text(encoding="utf-8")
    assert "_DGMP_THRESHOLDS_FCFA" not in text


def test_dgmp_tiers_align_thresholds_yaml_goods() -> None:
    """Seuils biens — config/regulatory/dgmp_mali/thresholds.yaml."""
    r = determine_dgmp_procedure_tier(20_000_000.0, "XOF", family_key="goods")
    assert r.procedure_tier == "simplified"
    r2 = determine_dgmp_procedure_tier(26_000_000.0, "XOF", family_key="goods")
    assert r2.procedure_tier == "request_for_quotation"
