# Audit V5.2 — Pydantic Settings (E-19)

## Ecart E-19 : os.environ.get() disperses — pas de source unique de config

### Statut : Corrige en P3 / P5.1

### Probleme initial
`os.environ.get()` appels directs dans ~12 fichiers. Aucune validation.
Rejets Pydantic non detectes au demarrage. Secrets exposables par erreur.

### Correction appliquee (src/core/config.py)

- `BaseSettings` avec `SettingsConfigDict(env_file=".env", extra="ignore")`
- `SECRET_KEY` via `AliasChoices("SECRET_KEY", "JWT_SECRET")` pour compatibilite V4.x
- `populate_by_name=True` pour les deux formes
- `DATABASE_URL` normalise : `postgresql+psycopg://` → `postgresql://` via `field_validator`
- Variables optionnelles : `LANGFUSE_*`, `REDIS_URL`, `MISTRAL_HTTPX_VERIFY_SSL`

### Tests associes

`tests/unit/test_settings.py` — 8 cas :
- Chargement minimal (3 vars requis)
- Alias JWT_SECRET → SECRET_KEY
- Validation longueur SECRET_KEY < 32 chars
- Normalisation postgresql+psycopg://
- TESTING=false par defaut
- LANGFUSE optionnel sans erreur
- Isolation env via `_ISOLATE` list

### Invariants verifies en CI

`ci-v52-gates.yml` job `permissions-matrix` :
- ROLE_PERMISSIONS 18 permissions × 6 roles
- admin == ALL_PERMISSIONS
- observer sans .write
