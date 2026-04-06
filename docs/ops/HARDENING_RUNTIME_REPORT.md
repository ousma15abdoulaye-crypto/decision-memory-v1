# Rapport runtime — durcissement LOT 1

**Date** : 2026-04-06

## Seal

- Route : `src/api/routers/committee_sessions.py` — `seal_committee_session`.
- Snapshot : `build_pv_snapshot` → **`validate_pv_snapshot`** (blocs + `meta` + kill list sur `scores_matrix`).
- Hash : SHA-256 sur JSON canonique **sans** clé `seal`, puis injection `seal.seal_hash`.
- Workspace : passage à `status=sealed` + `committee_sessions` mis à jour.
- **409** si déjà scellé / mauvais état workspace (guards + `validate_transition`).

## Irréversibilité

- DB : triggers `fn_committee_session_sealed_final` (071) ; session sealed → pas de retour arrière métier.
- API : refus transition si statut incompatible (voir route).

## M14

- Écriture/lecture alignées **`workspace_id`** — `src/procurement/m14_evaluation_repository.py`.

## Exports

- `get_sealed_session` : **409** non scellé, **500** hash / snapshot absent ou mismatch.
- JSON/PDF/XLSX : contenu depuis **`pv_snapshot`** persisté uniquement.

## Tests ciblés ajoutés / durcis

- `validate_pv_snapshot` — rejet si clé interdite dans `scores_matrix`.
- PV builder — présence `meta`, kill list.
- `document_service` — 409/500/200 inchangés fonctionnellement.

## GAP

- Preuve **seal HTTP 200** + **SQL VERT** sur un workspace de prod : **à faire** après déploiement / rerun seal (voir `PRODUCT_PROOF_REPORT.md`).
