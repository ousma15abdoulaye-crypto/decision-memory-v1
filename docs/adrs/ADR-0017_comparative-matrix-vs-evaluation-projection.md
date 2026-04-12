# ADR-0017 — Matrice produit vs projection tableau (exports PV / XLSX / PDF)

**Date :** 2026-04-12  
**Statut :** Accepté (implémentation plan §3 — 2026-04-12)  
**Références :** `docs/freeze/CONTEXT_ANCHOR.md` (addendum 2026-04-11), `docs/adr/ADR-V51-M16-UI-SCOPE-ROADMAP.md`, `docs/ops/WORKSPACE_SEAL_COMMITTEE_UX.md`, ADR-0012 (pipeline V5)

---

## 1. Contexte — erreur à corriger (narratif, pas un numéro ADR existant)

Une **piste d’architecture erronée** a été inférée à partir **d’un seul commentaire** dans `src/services/pv_builder.py` (anciennement : *« Source unique de vérité pour le tableau comparatif côté serveur »*). Ce texte **contredisait** les documents canon déjà gelés / adoptés :

| Source canon | Position opposable |
|--------------|-------------------|
| `CONTEXT_ANCHOR.md` addendum 2026-04-11 | `GET /api/workspaces/{id}/comparative-matrix` = matrice **produit / UI** ; `source: m16 \| m14` |
| `ADR-V51-M16-UI-SCOPE-ROADMAP.md` | Même matrice canonique après stabilisation scellement |
| `WORKSPACE_SEAL_COMMITTEE_UX.md` | Écran principal → `comparative-matrix`, forme alignée evaluation-frame |

**Clarification importante :** le fichier **`docs/adrs/ADR-0013_force-recompute-contract.md`** traite **`force_recompute` / ScoringEngine** (pipeline A) et **n’est pas** concerné par cette confusion. **Aucun écrasement** de cet ADR n’est requis. L’ADR présent **0017** enregistre la décision sur **deux rôles d’API distincts** et un **plan de correction** des failles restantes.

**Action documentaire déjà faite dans le code :** docstring de `build_evaluation_projection` corrigée pour renvoyer vers les canons ci-dessus et distinguer **projection exports** vs **matrice UI**.

---

## 2. Décision — deux rôles, pas deux vérités concurrentes

### 2.1 Matrice canonique produit / grille écran

- **Route :** `GET /api/workspaces/{id}/comparative-matrix`
- **Implémentation :** `src/services/comparative_matrix_service.py` (`build_comparative_matrix_payload`)
- **Comportement :** base **evaluation-frame** ; si au moins une ligne dans `criterion_assessments`, **overlay** M16 (scores reconstruits depuis les assessments enrichis) ; sinon **M14** depuis le dernier `evaluation_documents.scores_matrix` (via frame)
- **Consommateur attendu :** `frontend-v51/components/workspace/comparative-table.tsx` (et invalidations React Query associées)

### 2.2 Projection serveur tableau (PV non scellé, cohérence XLSX / PDF)

- **Route :** `GET /api/workspaces/{id}/m16/comparative-table-model`
- **Implémentation :** `src/services/comparative_table_model.py` + `build_evaluation_projection` dans `src/services/pv_builder.py`
- **Comportement :** `criteria` / `bundles` / `scores_matrix` sanitisés depuis la DB ; bloc optionnel `m16` pour extras ; **ne remplace pas** le snapshot scellé (`build_comparative_table_model_from_snapshot` pour rendu post-seal)
- **Consommateur attendu :** chaîne **exports / rendu serveur**, **pas** la grille écran principale

### 2.3 Règle de résolution de conflit

En cas de tension entre **commentaire de code** et **CONTEXT_ANCHOR / ADR-V51 / ops UX** : **les documents canon priment** ; le code ou les commentaires doivent être alignés (comme pour `pv_builder.py`).

---

## 3. Plan de correction des failles architecturales (phases)

Les items ci-dessous sont **proposés** ; chaque phase = mandat / PR dédié, tests et revue.

| ID | Faiblesse | Correction proposée | Priorité |
|----|-----------|---------------------|----------|
| **P1** | Risque de redire « une seule vérité » sans qualifier le **rôle** (UI vs export) | Revue ciblée des docstrings / README qui parlent de « vérité unique » ou « canonique » sans citer l’endpoint ; aligner sur cette ADR ou sur CONTEXT_ANCHOR | **Fait** — docstrings `comparative_matrix_service`, `comparative_table_model`, `pv_builder` (déjà corrigé) |
| **P2** | **Duplication** de logique (sanitisation scores, ordre `evaluation_documents`, critères DAO) entre `workspace_evaluation_frame_assembly`, `pv_builder`, `comparative_matrix_service` | Extraire progressivement des helpers **lecture seule** partagés (ex. « dernier doc d’évaluation », « sanitize scores_matrix ») **sans** fusionner les payloads UI et export en une seule route | **Partiel** — `evaluation_document_query.fetch_latest_*` + lecteurs alignés ; sanitisation profonde reste dans `pv_builder` |
| **P3** | Surface OpenAPI / `types/api.ts` expose `comparative-table-model` **sans** consommateur TSX connu | Documenter dans contrat front (`consumed-paths` ou doc ops) : **optionnel** pour UI ; ou générer un client « internal only » pour éviter l’illusion d’endpoint « mort » | **Fait** — commentaire `consumed-paths.ts` |
| **P4** | **Tests de contrat** : deux JSON peuvent diverger légitimement (même workspace) | Ajouter tests (ou snapshots documentés) qui **affirment** les champs minimaux de chaque route et **interdisent** la confusion « même shape = même endpoint » | **Fait** — `tests/services/test_comparative_endpoints_contract.py` |
| **P5** | Ordre de lecture `evaluation_documents` (`ORDER BY created_at` vs `version DESC, created_at DESC`) entre chemins | Audit unifié : une règle documentée « dernier document d’évaluation » pour **tous** les lecteurs ; migrations si incohérence avérée | **Fait** — `evaluation_document_query.py` + `m14_evaluation_repository.get_latest` tie-break `created_at` |
| **P6** | Onboarding / audit externe | Lier cette ADR depuis `CONTEXT_ANCHOR` (addendum futur) ou annexe atlas **L5 / comparaison** une fois statut **Accepté** | **Fait** — addendum 2026-04-12 |

---

## 4. Hors périmètre (sauf nouveau mandat)

- **Fusionner** en une seule route `comparative-matrix` et `comparative-table-model` sans analyse produit (perte de clarté exports vs frame cognitif).
- Modifier **ADR-0013** (`force_recompute`) : sujet orthogonal.
- Changer la **règle canon** `m16 si assessments sinon m14` sans ADR produit + CTO.

---

## 5. Critères d’acceptation (ADR « Accepté »)

- [x] Référence croisée depuis CONTEXT_ANCHOR (addendum 2026-04-12).
- [x] **P1** + **P4** + **P5** livrés (voir §3).
- [ ] Revue CTO / produit formelle si requise par la gouvernance release.

---

## 6. Historique

| Date | Événement |
|------|-----------|
| 2026-04-12 | Rédaction initiale — suite annulation d’une piste « double vérité » basée sur commentaire `pv_builder` ; docstring corrigée dans le code. |
| 2026-04-12 | Implémentation plan §3 : `evaluation_document_query`, refactor lecteurs, tests contrat, CONTEXT_ANCHOR. |
