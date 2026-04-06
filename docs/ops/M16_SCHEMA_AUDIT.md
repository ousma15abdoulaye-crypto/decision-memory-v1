# M16 — Audit schéma source (avant migrations M16)

**Branche :** `feature/m16-comparative`  
**Date :** 2026-04-06  
**Objectif :** Ancrer la D1 sur le dépôt réel (pas de table `evaluation_scores` indexée côté Python) et documenter la forme JSONB M14 pour le backfill.

## Constat (code + migrations)

| Objet | Rôle | Source |
|-------|------|--------|
| `public.evaluation_documents` | Stocke la matrice M14 dans `scores_matrix` (JSONB) | `056_evaluation_documents.py` (+ `workspace_id` post-073/074) |
| `public.dao_criteria` | Critères DAO ; `id` **TEXT** PK ; `workspace_id` NOT NULL post-074 | `002`, `073`, `074` |
| `public.supplier_bundles` | Bundles ; `id` **UUID** | `070_supplier_bundles_documents.py` |
| `public.process_workspaces` | Workspace ; `tenant_id` pour RLS | `069_process_workspaces_events_memberships.py` |
| Table `evaluation_scores` | **Aucune occurrence** dans le code Python applicatif indexé | grep — **absente** |

**Décision D1 :** tables M16 relationnelles + **backfill** depuis `evaluation_documents.scores_matrix`.

## Forme de `scores_matrix` (M14 → PV)

- Niveau 1 : clé = identifiant **bundle** (string, souvent UUID).
- Niveau 2 : clé = **critère**.
- Feuille : JSON (souvent `score` / `value`). Clés neutres interdites filtrées au snapshot.

Kill-list : `src/services/pv_builder.py`, `src/cognitive/evaluation_frame.py`.

## Audit PostgreSQL live (optionnel)

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name ILIKE '%score%';
```
