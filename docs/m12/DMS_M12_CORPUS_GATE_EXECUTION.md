# DMS — Document A : M12 Corpus Gate — Exécution immédiate

**Référence** : DMS-M12-CORPUS-GATE-A  
**Statut** : **GATE FRANCHI** (RÈGLE-23 satisfaite) — le chantier prioritaire passe à Document B (multipasses) selon mandat.  
**Date** : 2026-03-24 · **Mise à jour terrain** : 2026-03-24  
**Subordonné à** : [DMS_V4.1.0_FREEZE.md](../freeze/DMS_V4.1.0_FREEZE.md) (RÈGLE-23, RÈGLE-25), [DETTE_M12.md](../mandates/DETTE_M12.md)

---

## Preuve de clôture (AO)

| Élément | Valeur |
| --- | --- |
| Statut `annotated_validated` | **22** documents (seuil minimal 15 dépassé) |
| Stockage corpus | **Cloudflare R2** (objets dérivés du flux Label Studio / webhook corpus — aligné `CORPUS_SINK` / sink S3-compatible annotation-backend). **Opérations** : [M12_CORPUS_R2_RAILWAY.md](./M12_CORPUS_R2_RAILWAY.md) |
| Conformité | Export / lignes conformes politique M12-v2 ; traçabilité via hashes côté bucket |

Les **22** documents comptent pour le gate M12 ; les **15** restent le minimum réglementaire V4.1 — le surplus renforce la baseline sans changer la règle.

---

## Objet

Ce document **scinde** la stratégie M12 / industrialisation en deux flux exécutables :

- **Document A (ce fichier)** : franchir le **seuil corpus** M12 — **15 × `annotated_validated`** — avec le **pipeline actuel** (Label Studio + `services/annotation-backend/backend.py` + Mistral).
- **Document B** : [`DMS_ANNOTATION_MULTIPASS_POST_M12.md`](./DMS_ANNOTATION_MULTIPASS_POST_M12.md) — architecture multipasses **après** le gate.

**Règle historique** : tant que le comptage `annotated_validated` &lt; 15, l’annotation humaine prime sur l’infra multipasses. **Aujourd’hui** : comptage ≥ 15 — cette règle de blocage est **levée** pour le corpus courant.

---

## Critère de sortie (binaire)

| Métrique | Cible | Source de vérité |
| --- | --- | --- |
| `annotated_validated` | ≥ **15** | Label Studio + export M12 v2 ([M12_EXPORT.md](./M12_EXPORT.md)) |

Seul **`annotated_validated`** compte (RÈGLE-23). Aucun statut intermédiaire ne débloque M12.

---

## Périmètre technique autorisé (Document A)

- **Autorisé** : corrections **chirurgicales** sur `services/annotation-backend/backend.py` si mandat / freeze ([PIPELINE_REFONTE_FREEZE.md](../freeze/PIPELINE_REFONTE_FREEZE.md)), scripts d’import/export (`scripts/extract_for_ls.py`, `scripts/export_ls_to_dms_jsonl.py`), validation golden (`scripts/validate_annotation.py`).
- **Interdit** : introduction du pipeline multipasses canonique (`src/annotation/passes/*`, orchestrateur annotation), nouvelle gateway LLM (OpenRouter) **avant** le gate, refonte `backend.py` type « big bang ».

---

## Exécution opérationnelle (AO)

Workflow détaillé : [M12_AO_WORKFLOW.md](./M12_AO_WORKFLOW.md).

Résumé :

1. Constituer le corpus (familles A/B/C, pas PV/évaluation comme matière M12).
2. Importer les tâches LS (JSON avec `data.text`, optionnel `document_role`).
3. Pour chaque tâche : Predict → corriger `extracted_json` → statut **`annotated_validated`** si et seulement si validation complète.
4. Documenter le découpage train/test (12/3) via `data/annotations/M12_TRAIN_TEST_SPLIT.md` (template : `data/annotations/M12_TRAIN_TEST_SPLIT.template.md`).

---

## Vérification

- Export JSONL conforme [ADR-M12-EXPORT-V2](../adr/ADR-M12-EXPORT-V2.md).
- Comptage : `grep` / script sur champ `annotation_status` ou procédure LS documentée.
- Infra : [M12_INFRA_SMOKE.md](./M12_INFRA_SMOKE.md).

---

## Clôture Document A

**DONE** : **22** enregistrements `annotated_validated`, corpus sur **Cloudflare R2** (preuve opérationnelle AO).

**Suite** : enclencher le périmètre **Document B** — [DMS_ANNOTATION_MULTIPASS_POST_M12.md](./DMS_ANNOTATION_MULTIPASS_POST_M12.md) (contrats PassOutput, FSM, migration strangler, passes, baseline réelle).

---

## Lien avec Document B

Après clôture A → lire [DMS_ANNOTATION_MULTIPASS_POST_M12.md](./DMS_ANNOTATION_MULTIPASS_POST_M12.md) pour la séquence : schéma `PassOutput`, spec FSM orchestrateur, stratégie migration `backend.py`, implémentation passes.
