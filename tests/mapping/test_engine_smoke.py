from pathlib import Path
import json
import pytest

from src.mapping.template_engine import TemplateMappingEngine

@pytest.mark.smoke
def test_engine_loads_spec():
    spec = Path("docs/templates/template_spec_v1.0.json")
    assert spec.exists()

def test_engine_instantiates_without_template():
    # Template may not be present in CI; ensure constructor works
    engine = TemplateMappingEngine("docs/templates/template_spec_v1.0.json", "src/templates/DMS-CBA-CANONICAL-V1.0.xlsx")
    assert engine.spec["max_suppliers"] == 50
