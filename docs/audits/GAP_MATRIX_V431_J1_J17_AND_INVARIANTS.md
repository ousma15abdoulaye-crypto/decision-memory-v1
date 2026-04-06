# Matrice d’écart — canon MS Workspace V4.3.1 (J1–J17 + INV) vs dépôt

**Date** : 2026-04-06  
**Méthode** : revue code + migrations + docs ops (pas d’audit runtime prod dans ce document).  
**Référence canon** : plan J1–J17 et registre INV (prompt V4.3.1).

Légende : **OK** implémenté ou équivalent documenté · **Partiel** · **Absent** · **N/A**

## Jalons J1–J17

| Jour | Livrable canon | État | Notes / preuves dépôt |
|------|----------------|------|------------------------|
| J1 | `compute_cognitive_state()` + guards C13/C14 + `extract_facts` + ConfidenceDisplay C3 + tests | **Partiel** | `src/cognitive/cognitive_state.py` ; `src/cognitive/confidence_envelope.py` ; usage dans `src/api/routers/workspaces.py`. Guards transitions : `src/workspace/status_transitions.py` — adoption route par route ([SPEC BLOC5](../specs/SPEC_BLOC5_V431_VALIDATION_REPORT.md)). Double affichage header C3 : à valider côté UI agrégée. |
| J2 | Migration 076+ (O2 `source_package_documents`), RLS, RegulatoryProfile C1 complet, 4 profils seeds | **Partiel** | `078_source_package_documents_bloc5.py` ; M13 YAML + `m13_regulatory_profile_versions` — pas le modèle Pydantic « C1 » texte canon mot pour mot. |
| J3–J5 | Migrations 077 confiance, `ConfidenceEnvelope`, propagation min/weighted, tests limites | **Partiel** | Migrations 078/079 BLOC5 ; `confidence_envelope.py` + tests `tests/cognitive/`. |
| J6–J8 | O6 CommitteeSession C4 : tables, triggers append-only, FSM, RBAC 17×6 | **Partiel** | `071_committee_sessions_deliberation.py` + services/routers ; mapping statuts vs canon ([SPEC BLOC5](../specs/SPEC_BLOC5_V431_VALIDATION_REPORT.md)). RBAC pilote : à rapprocher des matrices JWT. |
| J9–J10 | O8 C2 : `on_workspace_sealed`, tous bundles qualifiés, price_anchors, pgvector | **Partiel** | `src/workers/arq_sealed_workspace.py` — projecteur bundles `qualified` ; embeddings/pgvector : hors périmètre court grep. |
| J11–J12 | O5 `GET …/evaluation-frame`, INV-W06, C3 profil, SignalRelevance | **Partiel** | `src/cognitive/evaluation_frame.py` ; route workspaces ; kill-list tests pilote `bloc6_pilot_sci_mali_run.py`. |
| J13 | Agent surface `POST /agent/prompt` A–E | **Absent** | Aucune route `AgentRequest` / `POST /agent/prompt` dans `src/`. |
| J14 | WebSocket `dms_event_index` uniquement (INV-W07) | **Partiel** | `src/api/ws/workspace_events.py` diffuse **`workspace_events`** (poll SQL), documenté comme INV-W07 côté gateway — **diffère** du canon « projection depuis event_index uniquement ». |
| J15 | `GET …/audit-replay` + filtres | **Absent** | Aucune route `audit-replay` dans `src/`. |
| J16 | Exports audit JSON/PDF | **Absent** | Pas d’équivalent V6 ; exports PV BLOC7 sont **comité/PV**, pas audit replay. |
| J17 | UI Audit Replay E6 | **Absent** | Non applicable côté API seule ; pas d’indice dans ce dépôt backend. |

## Invariants INV (échantillon canon)

| ID | Énoncé | État | Notes |
|----|--------|------|-------|
| INV-W06 | Pas winner/rank/recommendation dans EvaluationFrame | **OK** (garde-fous) | CHECK DB + code ; tests kill-list |
| INV-W01 | Actes comité append-only | **Partiel** | Triggers M071 ; à valider cohérence exhaustive vs canon C4 |
| INV-W07 | WS = projection event_index | **Écart** | Implémentation actuelle : `workspace_events` ([workspace_events.py](../../src/api/ws/workspace_events.py)) |
| INV-C01 | cognitive_state = projection, pas colonne DB | **OK** | `compute_cognitive_state` |
| INV-C03 | EvaluationFrame serveur uniquement | **OK** | Assemblage `evaluation_frame` |
| INV-C12 | O8 écriture via handlers, tous bundles qualifiés | **Partiel** | `arq_sealed_workspace.py` |
| INV-C15 | `has_source_package` dérivé | **OK** | SPEC BLOC5 |

## Fichiers de référence rapide

- Cognitive / frame : `src/cognitive/`, `src/api/routers/workspaces.py`
- Seal / projecteur : `src/workers/arq_sealed_workspace.py`, `src/couche_a/committee/`
- WebSocket : `src/api/ws/workspace_events.py`
- M13 réglementaire : `src/procurement/m13_regulatory_profile_repository.py`, `config/regulatory/`

**Conclusion** : le dépôt couvre une **sous-partie matérielle** du canon V4.3.1 (BLOC5, migrations, comité V4.2, docgen BLOC7). Les jalons **J13 agent**, **J15–J17 V6 audit replay**, et la variante stricte **INV-W07** sur `dms_event_index` seuls sont les principaux écarts nommés.

**Preuve scellement prod (gate BLOC6)** : runbook exécutable — [`docs/ops/BLOC6_SEAL_PROD_VERIFICATION.md`](../ops/BLOC6_SEAL_PROD_VERIFICATION.md).
