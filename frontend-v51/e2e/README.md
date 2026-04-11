# Tests Playwright (frontend-v51)

## `comparative-matrix.spec.ts`

- **Objectif** : valider le comportement **React** de la grille (accessibilité clavier, filtres, zoom).
- **Données** : réponses HTTP **fictives** via `page.route("**/api/workspaces/**", …)`.
- **Limite** : ne démontre **pas** l’alignement avec une base réelle ni le corridor ZIP → pipeline.

## `home.spec.ts`

- Redirection racine / middleware (sans dépendre d’une API métier pour la matrice).

## `real-api-smoke.spec.ts` (opt-in)

- **Désactivé par défaut** (CI et local) : aucune variable → tests ignorés.
- Pour l’activer :
  - `E2E_REAL_API=1`
  - `E2E_LOGIN_EMAIL`, `E2E_LOGIN_PASSWORD` : compte de test sur l’API ciblée par `NEXT_PUBLIC_API_URL` au build du front.
  - `E2E_WORKSPACE_ID` : UUID d’un workspace accessible par ce compte.
- Prérequis : API joignable depuis la machine qui lance Playwright, CORS correct, front qui pointe vers cette API.
- Installation navigateurs : `npx playwright install chromium` (en entreprise, erreur TLS → confier l’exécution aux jobs GitHub Actions ou ajuster les certificats racine).
