# ADR-V53 — Lecture unifiée de l’historique M16 (E18)

**Statut :** Accepted (implémentation M-CTO-V53-E)  
**Date :** 2026-04-11  
**Problème :** Deux flux d’audit — `assessment_history` (trigger V52 sur `criterion_assessments`) et `criterion_assessment_history` (append-only M16) — l’API ne lisait que le second.

**Décision :** La route `GET …/m16/criterion-assessments/{id}/history` expose une **timeline fusionnée** : `UNION ALL` de `assessment_history` et `criterion_assessment_history`, tri chronologique, pagination sur le résultat. Aucune migration : **lecture seule** ; les deux tables restent append-only.

**Schéma de projection des colonnes :**

| Colonne API | `assessment_history` | `criterion_assessment_history` |
|-------------|----------------------|--------------------------------|
| `id` | `id::text` | `id::text` |
| `changed_at` | `created_at` | `changed_at` |
| `actor_id` | `changed_by` | `actor_id` |
| `old_status` / `new_status` | `NULL` | colonnes natives |
| `payload` | `change_metadata` | `payload` |
| `history_source` | `assessment_history` | `criterion_assessment_history` |

**Conséquences :** `count_assessment_history` et `list_assessment_history_paged` dans `m16_evaluation_service.py` uniquement.
