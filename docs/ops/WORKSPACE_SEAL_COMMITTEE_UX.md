# Scellement workspace — chemin UI vs routes comité

## Vérité côté frontend-v51 (V5.1)

L’action **« Sceller le processus »** dans l’interface appelle :

- `PATCH /api/workspaces/{workspace_id}/status` avec corps `{"status": "sealed"}`

Voir `frontend-v51/components/deliberation/seal-button.tsx`.

Les guards métier (préconditions) sont renvoyés en **422** avec détail exploitable par l’UI.

## Routes OpenAPI « comité »

Des routes additionnelles existent sous `/api/workspaces/{id}/committee/*` (ex. `open-session`, `seal`, export `pv`).

- L’**export PV** après scellement est bien consommé par l’UI (`GET …/committee/pv`).
- L’**ouverture de session comité** et le **seal** « nommé comité » ne sont **pas** exposés comme parcours séparé dans l’UI actuelle : le produit V5.1 s’appuie sur la **transition de statut workspace** pour le scellement.

Toute évolution vers un assistant « session comité » explicite (boutons `open-session` / `committee/seal`) doit être validée produit + CTO et alignée sur le backend (une seule source de vérité des guards).
