# E2E minimal — `frontend-v51`

## Prérequis

- API locale ou `NEXT_PUBLIC_API_URL` pointant vers un backend joignable.
- Node 20+.

## Playwright

```bash
cd frontend-v51
npm ci
npx playwright install
npm run dev
# autre terminal :
npm run test:e2e
```

Les tests sous `e2e/` vérifient la présence des liens d’entrée (page d’accueil, login) sans dépendre d’un JWT réel.

## CI

Le workflow principal V5.1 (`dms_invariants_v51.yml`) exécute déjà **tsc** et les garde-fous backend. L’ajout d’un job Playwright dédié reste optionnel (coût + navigateur).

## Références

- [`frontend-v51/package.json`](../../frontend-v51/package.json) — scripts `test:e2e`
