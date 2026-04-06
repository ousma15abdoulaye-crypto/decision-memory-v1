# P0 — Livrable 2 : Moteur cognitif E0→E6

**Statut** : spécification alignée sur le **code réel** (pas de FSM persistante dédiée).  
**Sources** : [`src/cognitive/cognitive_state.py`](../../../src/cognitive/cognitive_state.py), [`src/api/cognitive_helpers.py`](../../../src/api/cognitive_helpers.py), [`src/api/routers/workspaces.py`](../../../src/api/routers/workspaces.py), [`tests/cognitive/test_cognitive_state.py`](../../../tests/cognitive/test_cognitive_state.py).

## 1. Nature de l’implémentation

### 1.1 Projection pure (INV-C01)

- **`cognitive_state` n’est pas une colonne SQL** : l’état E0–E6 est calculé à la volée par `compute_cognitive_state(CognitiveFacts)`.
- **`CognitiveFacts`** (`dataclass`) contient : `workspace_status`, `has_source_package`, `bundle_count`, `bundles_all_qualified`, `evaluation_frame_complete`.
- **Chargement DB** : `load_cognitive_facts(conn, workspace_row)` dans [`src/api/cognitive_helpers.py`](../../../src/api/cognitive_helpers.py) :
  - `has_source_package` : `EXISTS` sur `source_package_documents`.
  - `bundle_count` / `bundles_all_qualified` : agrégation sur `supplier_bundles`, basée nominalement sur `qualification_status = 'qualified'` ; le recours à `bundle_status = 'complete'` n’est qu’un repli technique en cas d’exception (par ex. colonne `qualification_status` absente), pas une règle fonctionnelle normale.
  - `evaluation_frame_complete` : dernière ligne `evaluation_documents.scores_matrix` non vide.

### 1.2 Machine à états distincte : pipeline d’annotation (M12)

Ne pas fusionner avec E0–E6. La FSM **`AnnotationPipelineState`** vit dans [`src/annotation/orchestrator.py`](../../../src/annotation/orchestrator.py) (`ingested`, `routed`, `annotated_validated`, etc.). C’est le cycle **ingestion → annotation Label Studio**, pas le cycle **process workspace** SCI.

---

## 2. États E0–E6 — spécification effective

| ID | phase (code) | label_fr (code) | Condition de sortie (résumé) |
|----|----------------|-----------------|-------------------------------|
| E0 | intake | Collecte initiale | défaut / inconnu |
| E1 | context_building | Construction du contexte | `draft` + `has_source_package` |
| E2 | assembly | Assemblage des offres | `workspace_status == assembling` |
| E3 | qualification_partial | Qualification partielle | `assembled` / `in_analysis` / `analysis_complete` sans tous bundles qualifiés |
| E4 | comparative_ready | Comparatif prêt | même groupe de statuts + tous bundles qualifiés (`bundle_count > 0`) |
| E5 | deliberation | Délibération | `in_deliberation` |
| E6 | memory_committed | Mémoire engagée / clos | `sealed`, `closed`, `cancelled` |

**Mapping `workspace_status` → E** (extrait logique — voir fichier source pour la vérité absolue) :

- `sealed` | `closed` | `cancelled` → **E6**
- `in_deliberation` → **E5**
- `assembling` → **E2**
- `draft` : sans source package → **E0** ; avec → **E1**
- `assembled` | `in_analysis` | `analysis_complete` : si tous bundles qualifiés → **E4** sinon **E3** (si `bundle_count == 0`, tous qualifiés faux → **E3**)

### 2.1 Pré / post conditions déclaratives dans le code

Le fichier ne définit **pas** une table complète pré/post par état. Les **guards de transition de statut** sont dans `validate_transition(current_status, target_status, facts)` :

| Transition cible | Guard explicite |
|-------------------|-----------------|
| `assembling` | `has_source_package` True |
| `in_analysis` | `bundle_count > 0` |
| `in_deliberation` | `evaluation_frame_complete` True |
| `sealed` | `current_status == in_deliberation` |

**NON IMPLÉMENTÉ dans ce module** : RBAC fin par état cognitif, timeouts d’état, actions automatiques d’entrée/sortie autres que celles codées dans les routes (ex. `PATCH` workspace qui met à jour `assembled_at`, etc.).

### 2.2 Permissions (implémentées pour les transitions)

Les transitions de statut passent par `PATCH /api/workspaces/{id}/status` :

- Fonction `_permission_for_status_transition` : cibles `in_deliberation`, `sealed`, `closed` → permission **`committee.manage`** ; sinon **`bundle.upload`**.
- Vérification : `require_workspace_permission(...)` dans [`src/couche_a/auth/workspace_access.py`](../../../src/couche_a/auth/workspace_access.py).

Il n’existe **pas** de matrice 17×6 canonique dans le dépôt — seulement cette règle + accès workspace (`require_workspace_access`).

### 2.3 Données visibles / modifiables par état

**NON TRANCHÉ** sous forme de matrice unique : les endpoints workspace appliquent `require_workspace_access` puis filtrent les champs interdits (INV-W06). Le détail dépend des routes appelées (voir **L4**).

---

## 3. Transitions E(n)→E(n+1)

Les transitions **métier** opérées sur `process_workspaces.status` sont exposées via **`PATCH /api/workspaces/{workspace_id}/status`** ([`workspaces.py`](../../../src/api/routers/workspaces.py)) :

1. Chargement `facts = load_cognitive_facts`.
2. `validate_transition(current, target, facts)` ou conflit 409.
3. `UPDATE process_workspaces` avec timestamps conditionnels (`assembled_at`, `analysis_started_at`, `deliberation_started_at`, `sealed_at`, `closed_at`).
4. Insertion `workspace_events` `WORKSPACE_STATUS_CHANGED`.
5. Réponse inclut `cognitive_state` et `describe_cognitive_state`.

**Réversibilité** : **NON** spécifiée comme machine à états bidirectionnelle ; seules les valeurs dans `VALID_WORKSPACE_STATUSES` sont acceptées. Pas de notion de timeout dans ce module.

**États parallèles / sous-états** : **NON** — un seul `status` par workspace. Pas de E2a/E2b dans le code.

---

## 4. Relation E0–E6 et draft / active / sealed (questions mandat)

- Le code utilise **`process_workspaces.status`** avec valeurs : `draft`, `assembling`, `assembled`, `in_analysis`, `analysis_complete`, `in_deliberation`, `sealed`, `closed`, `cancelled` ([`VALID_WORKSPACE_STATUSES`](../../../src/api/routers/workspaces.py)).
- **« active »** n’apparaît pas comme valeur de statut workspace dans ce fichier.
- **Comité** : statuts de session mappés côté API (`map_committee_session_row`) — `active` → affichage `draft` pour l’API (voir [`cognitive_helpers.py`](../../../src/api/cognitive_helpers.py)). **Système distinct** du statut workspace.

**Primaire** : statut workspace + faits DB pour E0–E6 ; la FSM annotation est **orthogonale**.

---

## 5. Stockage en base

| Concept | Stocké ? | Où |
|---------|----------|-----|
| E0–E6 | Non (projection) | Calculé |
| Statut processus | Oui | `process_workspaces.status` |
| Journal transitions | Oui | `workspace_events` (événements dont `WORKSPACE_STATUS_CHANGED`) |
| Log dédié « workspace_state_transitions » | **NON** — nom de table non trouvé ; utiliser `workspace_events` | |

---

## 6. Code source (références)

| Rôle | Fichier |
|------|---------|
| Calcul E0–E6 | [`src/cognitive/cognitive_state.py`](../../../src/cognitive/cognitive_state.py) |
| Guards | `validate_transition` (même fichier) |
| Faits DB | [`src/api/cognitive_helpers.py`](../../../src/api/cognitive_helpers.py) |
| Route transition + exposition | [`src/api/routers/workspaces.py`](../../../src/api/routers/workspaces.py) `patch_workspace_status`, `get_workspace` |
| Tests | [`tests/cognitive/test_cognitive_state.py`](../../../tests/cognitive/test_cognitive_state.py) |

---

## 7. Matrice d’activation (synthèse honnête)

| État | Endpoints utiles | Permissions | UI |
|------|------------------|-------------|-----|
| E0–E6 | Tous les endpoints workspace nécessitent JWT + accès workspace ; **aucun** n’est désactivé par E0–E6 dans le middleware | Voir `_permission_for_status_transition` pour **PATCH status** uniquement | **Hors dépôt** — pas de frontend dans ce repository |

Pour le détail des chemins OpenAPI, voir [`ANNEX_A_openapi.json`](ANNEX_A_openapi.json) et [`P0_L4_api_contract.md`](P0_L4_api_contract.md).

---

## 8. Limitations / dette

- Jalon J1 **partiel** vs canon MS Workspace : voir [`docs/audits/GAP_MATRIX_V431_J1_J17_AND_INVARIANTS.md`](../../audits/GAP_MATRIX_V431_J1_J17_AND_INVARIANTS.md).
- Pas de route dédiée `GET /cognitive-state` isolée : l’état est renvoyé dans `GET /workspaces/{id}` et `PATCH .../status`.
