# Tests — matrice des applications FastAPI

La production expose **`main:app`** (`main.py` à la racine). Une partie des tests importe **`src.api.main:app`** (harness ADR-M5-PRE-001, routes optionnelles). Voir le fichier racine du dépôt `docs/adr/ADR-DUAL-FASTAPI-ENTRYPOINTS.md`.

| Fichier / zone | Application importée |
|----------------|----------------------|
| `tests/test_healthcheck.py` | `main.app` |
| `tests/test_upload_security.py` | `main.app` |
| `tests/test_upload.py` | `main.app` |
| `tests/test_rbac.py` | `main.app` |
| `tests/test_auth.py` | `main.app` |
| `tests/invariants/test_inv_01_cognitive_load.py` | `main.app` |
| `tests/test_main_app_parity_smoke.py` | `main.app` (smoke OpenAPI / préfixes critiques) |
| `tests/phase0/test_extraction_engine_api.py` | `src.api.main.app` |
| `tests/integration/conftest.py` | `src.api.main.app` |
| `tests/vendors/test_vendor_*.py` | `src.api.main.app` |
| `tests/geo/conftest.py` | `src.api.main.app` |
| `tests/api/conftest.py` | `src.api.main.app` |
| `tests/api/test_extractions_auth.py` | `src.api.main.app` |

**Règle** : toute route destinée à Railway / `uvicorn main:app` doit être montée dans `main.py`. Les tests sur `src.api.main` ne remplacent pas une preuve de montage en prod.
