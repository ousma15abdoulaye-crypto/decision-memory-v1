# DMS – CBA Template Mapping Engine (V1.0)

Ce package implémente le moteur de mapping Excel pour le CBA **pré-large + masquage** (max 50 fournisseurs).
- Aucune insertion dynamique de colonnes.
- Colonnes calculées via indices (support au-delà de Z).
- Noms d'onglets canonisés.

## Structure
- `docs/templates/template_spec_v1.0.json` : spec versionnée (source de vérité)
- `src/mapping/template_engine.py` : moteur principal
- `src/mapping/supplier_mapper.py` : fonctions populate_*()
- `src/mapping/column_calculator.py` : calculs de colonnes robustes
- `src/mapping/styling.py` : couleurs confiance
- `tests/mapping/test_engine_smoke.py` : test smoke

## Usage (exemple)
```python
from mapping.template_engine import TemplateMappingEngine

engine = TemplateMappingEngine(
    spec_path="docs/templates/template_spec_v1.0.json",
    template_path="src/templates/DMS-CBA-CANONICAL-V1.0.xlsx",
)

case_data = {
  "case_id": "MOPTI-2026-01",
  "version": 1,
  "submissions": [
    {"supplier_name": "FOURNISSEUR A", "conformity": {"RC": True}, "capacity_scores": {}, "sustainability_scores": {}, "line_items": []},
    {"supplier_name": "FOURNISSEUR B", "conformity": {"RC": True}, "capacity_scores": {}, "sustainability_scores": {}, "line_items": []},
    {"supplier_name": "FOURNISSEUR C", "conformity": {"RC": False}, "capacity_scores": {}, "sustainability_scores": {}, "line_items": []},
  ]
}

out = engine.export_cba(case_data, output_dir="out")
print(out)
```
