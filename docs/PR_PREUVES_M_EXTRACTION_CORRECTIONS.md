# PR — Preuves obligatoires M-EXTRACTION-CORRECTIONS

## 1. pytest_plugins — Package tests importable (Option A)

**État :** ✅ Conforme

- `tests/__init__.py` — existe
- `tests/db_integrity/__init__.py` — existe
- `tests/integration/__init__.py` — ajouté (Option A)

`pytest_plugins = ["tests.db_integrity.conftest"]` fonctionne.

---

## 2. Preuve import `app` (grep)

```powershell
Get-ChildItem tests -Recurse -Filter "*.py" | Select-String "import app|from .* import app"
```

**Résultat :**

| Fichier | Import |
|---------|--------|
| tests/integration/conftest.py | `from src.api.main import app` |
| tests/phase0/test_extraction_engine_api.py | `from src.api.main import app` |
| tests/test_upload_security.py | `from main import app` |
| tests/test_upload.py | `from main import app` |
| tests/test_rbac.py | `from main import app` |
| tests/test_auth.py | `from main import app` |
| tests/invariants/test_inv_01_cognitive_load.py | `from main import app` |

**Synthèse :**
- **src.api.main** : integration, phase0 extraction (extraction_router inclus)
- **main** (racine) : auth, upload, rbac, invariants (app complète)

Le router d’extraction est inclus dans les deux. Les tests extraction utilisent `src.api.main`.

---

## 3. Exécution pytest (Docker Postgres)

**Commande (si Docker est disponible) :**

```powershell
# 1. Démarrer Postgres (aligné CI : postgres:15, testpass, dmstest)
docker run --rm -d --name dms-pg -e POSTGRES_PASSWORD=testpass -e POSTGRES_DB=dmstest -p 5432:5432 postgres:15

# 2. Variables + migrations + tests
$env:DATABASE_URL="postgresql+psycopg://postgres:testpass@localhost:5432/dmstest"
cd C:\Users\abdoulaye.ousmane\decision-memory-v1
alembic upgrade head
python -m pytest tests/db_integrity -q

# 3. Arrêt
docker stop dms-pg
```

**Note :** Sur cette machine, Docker n'est pas disponible. L'exécution doit être faite localement ou en CI.
