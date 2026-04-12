# ADR — Scellement workspace (PATCH) vs session comité et PV (V5.1)

## Statut

**Accepté — Option A (GO CTO)** — 2026-04-11.

## Contexte

- L’UI V5.1 déclenche le scellement via `PATCH /api/workspaces/{id}/status` avec `{"status": "sealed"}`.
- L’export PV légal et `get_sealed_session` s’appuient sur `committee_sessions` : statut `sealed`, `pv_snapshot`, `seal_hash`.
- Avant cette décision, le seul `PATCH` mettait à jour `process_workspaces` sans garantir une session comité scellée → état ambigu (workspace « sealed » sans PV).

## Décision

**Option A — Workspace orchestre le comité / PV**

Lorsque la cible de transition est `sealed`, le backend exécute **la même séquence fonctionnelle** que `POST /api/workspaces/{id}/committee/seal` (préconditions `run_all_seal_checks`, construction du snapshot PV, mise à jour `committee_sessions` + `process_workspaces` + événements), avec les extensions suivantes :

1. **Session absente** : création automatique d’une session `active` (type `standard`, `min_members = 3`) + événement `session_activated`, puis **synchronisation** des lignes `committee_session_members` depuis `workspace_memberships` (rôles workspace projetés sur les rôles comité autorisés, défaut `observer`).
2. **Réconciliation** : si la session est déjà `sealed` mais le workspace ne l’est pas encore, alignement idempotent du workspace sur la session (chemin de récupération sans regénérer de PV).

**Option B (comité canon uniquement)** — non retenue pour ce cycle : imposait un parcours UI entièrement basé sur les routes `/committee/*` sans orchestration sur `PATCH`.

## Conséquences

- Une erreur **422** sur préconditions de scellement **empêche** tout passage à `sealed` sur le workspace (plus d’état orphelin).
- `POST …/committee/seal` reste l’API explicite W3 ; le comportement métier est **factorisé** avec le `PATCH` sealed.
- Documentation produit : `docs/ops/WORKSPACE_SEAL_COMMITTEE_UX.md`.

## Références

- `src/services/workspace_irr_seal_service.py`
- `src/api/routers/workspaces.py` — `PATCH …/status` (branche `sealed`)
- `src/api/routers/committee_sessions.py` — `POST …/committee/seal`
- `src/services/document_service.py` — `get_sealed_session`
