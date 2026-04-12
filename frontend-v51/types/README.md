# Types frontend V5.1

## `api.ts` (OpenAPI / openapi-typescript)

- **Généré** : ne pas éditer à la main ; régénérer via le workflow CI (export OpenAPI → `openapi-typescript`) ou `scripts/export_openapi_main_app.py` + `npx openapi-typescript`.
- Décrit **l’API serveur exposée**, pas uniquement ce que l’UI utilise.

## `consumed-paths.ts`

- Liste de **regex** alignées sur les appels réels dans `app/`, `components/`, `lib/`.
- Validées par `scripts/check_frontend_api_surface.py` (étape CI **INV-F01** dans `dms_invariants_v51.yml`).

## Autres `.ts`

- Types locaux (hooks, props) — maintenus à la main.
