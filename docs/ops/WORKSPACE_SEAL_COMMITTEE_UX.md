# Scellement workspace — chemin UI vs routes comité

## Vérité côté frontend-v51 (V5.1)

L’action **« Sceller le processus »** dans l’interface appelle :

- `PATCH /api/workspaces/{workspace_id}/status` avec corps `{"status": "sealed"}` (champ optionnel `seal_comment`).

Voir `frontend-v51/components/deliberation/seal-button.tsx`.

### Backend (Option A — ADR)

À partir de **ADR-V51-WORKSPACE-SEAL-VS-COMMITTEE-PV**, ce `PATCH` **orchestre** le scellement IRR : préconditions `run_all_seal_checks`, session `committee_sessions` (créée automatiquement si absente, membres synchronisés depuis `workspace_memberships`), snapshot PV, `seal_hash`, puis alignement `process_workspaces.status = sealed`. Les échecs de préconditions restent en **422** avec détail exploitable par l’UI.

La réponse peut inclure `irr_seal` : `session_id`, `seal_hash`, `recovered` (réconciliation workspace / session déjà scellée).

## Routes OpenAPI « comité »

Des routes additionnelles existent sous `/api/workspaces/{id}/committee/*` (ex. `open-session`, `seal`, export `pv`).

- L’**export PV** après scellement est consommé par l’UI (`GET …/committee/pv`) — cohérent avec le modèle ci-dessus.
- `POST …/committee/seal` reste l’acte W3 explicite ; la logique métier est **partagée** avec le `PATCH` sealed (même service `finalize_workspace_irr_seal`).

Toute évolution vers un assistant « session comité » uniquement (Option B historique non retenue) devrait être validée produit + CTO et documentée dans un nouvel ADR.

## Matrice comparative

L’écran principal consomme **`GET /api/workspaces/{id}/comparative-matrix`** : le serveur renvoie `source: "m16" | "m14"` et une forme alignée sur l’ancien `evaluation-frame` pour la grille (voir `comparative-table.tsx`).
