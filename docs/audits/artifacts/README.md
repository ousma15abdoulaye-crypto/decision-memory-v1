# Artefacts d’audit FastAPI (auth / case-guard)

Ce répertoire peut contenir :

- Des **rapports Markdown** générés par la CI à partir de  
  `python scripts/audit_fastapi_auth_coverage.py --report-md ...`
- Des fichiers **optionnels** versionnés (ex. snapshot de référence) — à maintenir manuellement si besoin.

**CI** : le workflow `.github/workflows/ci-main.yml` génère à chaque run :

- `audit_main_app_auth_coverage.md` — app `main:app` (artefact nommé `fastapi-auth-audit-main-app`)
- `audit_src_api_main_app_table.md` — app modulaire `src.api.main:app` (généré avec `continue-on-error` ; peut être absent si l’étape échoue avant écriture)

Téléchargement : **Actions** → run → **Artifacts**. Le contenu peut différer entre branches ; la **politique** est définie par le script et les options `--fail-prefix` / `--fail-sensitive-prefix`.
