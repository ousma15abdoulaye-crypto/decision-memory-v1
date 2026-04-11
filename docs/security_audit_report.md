# Rapport d’audit sécurité — schéma DMS (RLS, `tenant_id`, triggers)

**Date** : 2026-04-11  
**Périmètre** : inventaire **code + migrations Alembic** du dépôt `decision-memory-v1`.  
**Limite** : les **comptes de lignes** et l’état exact sur une base Railway/prod ne sont pas rejoués ici ; exécuter les requêtes §4 sur l’environnement cible et annexer les résultats.

---

## 1. Synthèse exécutive

| # | Table / sujet | État **attendu après migrations jusqu’au head** | Écart historique (avant correctif) | Action |
|---|----------------|-----------------------------------------------|-----------------------------------|--------|
| 1 | `market_surveys` | `tenant_id` UUID + RLS + FORCE + policy | M042 : `case_id` / `org_id` seulement ; **v52_p1_003** indiquait « différé P2 » sans RLS | **Migration `094_security_market_mercurial_tenant_rls`** |
| 2 | `mercurials` / `mercuriale_sources` | `tenant_id` sur les deux + RLS + FORCE | M040 : **aucun** `tenant_id`, **aucune** RLS | **Idem** |
| 3 | `market_signals_v2` | `tenant_id` + RLS + FORCE | M043 : table **globale** sans tenant | **Idem** |
| 4 | `offers`, `extractions` | `tenant_id` + RLS + FORCE | M002 + suivantes : liées à `cases` mais **pas** dans la boucle RLS 051 (seulement `supplier_scores`, `pipeline_runs`, `criteria`) | **Idem** |
| 5 | `analysis_summaries` | `tenant_id` + RLS + FORCE | M035 : append-only, **sans** RLS | **Idem** |
| 6 | `score_history` | Append-only + RLS | M059 : `trg_*_append_only` si `fn_reject_mutation` existe ; policies **dupliquées** possibles (059 via `cases` + v52 via `workspace_id`) | **Vérifier** en prod ; pas de double UPDATE trigger |
| 7 | `cases` vs `process_workspaces` | Coexistence documentée (CONTEXT_ANCHOR) | Risque de **double vérité** | **Hors scope migration 094** — chantier produit / données |
| 8 | FORCE RLS | Tables sensibles avec RLS doivent avoir **FORCE** | Partiellement corrigé (089, v52_p1_003) | **094** complète les tables marché / mercuriale / offres |

---

## 2. Détail par table (référentiel migrations)

### 2.1 `market_surveys` (M042)

- Colonnes : `item_id`, `zone_id`, `case_id`, `org_id`, pas de `tenant_id` UUID.
- **Pas de RLS** dans M042.
- `073` ajoute `workspace_id` nullable ; `074` laisse `market_surveys.workspace_id` nullable.

### 2.2 `mercurials` / `mercuriale_sources` (M040)

- Aucune colonne `tenant_id`.
- Aucune RLS.

### 2.3 `market_signals_v2` (M043)

- Pas de `tenant_id`.
- Pas de RLS (signaux dérivés, considérés « globaux » à l’origine).

### 2.4 `offers`, `extractions` (M002)

- `case_id` → `cases`.
- **051** : RLS sur `cases`, `supplier_scores`, `pipeline_runs`, `criteria` — **pas** sur `offers` / `extractions`.

### 2.5 `analysis_summaries` (M035)

- `case_id`, trigger append-only.
- Pas de RLS dans la migration.

### 2.6 `score_history` (M059 + 074 + v52_p1_003)

- M059 : RLS + FORCE + policy via `cases.tenant_id` (TEXT) + trigger append-only si `fn_reject_mutation` existe.
- 074 : `workspace_id` NOT NULL, drop `case_id`.
- v52_p1_003 : policy supplémentaire via `process_workspaces.tenant_id` et `app.current_tenant::uuid`.

**Risque** : deux policies `FOR ALL` → visibilité union (souvent acceptable) ; à valider métier.

### 2.7 Tables « orphelines » (`django_*`, etc.)

- **Aucune référence** dans le code Python du dépôt pour `auth_group`, `django_*`, `io_storages_*`, etc.
- Si présentes sur une base externe (import Label Studio / autre), elles sont **hors migrations DMS** : traiter par script de renommage **sur cette base uniquement**.

---

## 3. Variables de session RLS (canon application)

L’application pose (voir `src/db/connection.py`, `src/db/core.py`) :

- `app.tenant_id` (texte)
- `app.current_tenant` (texte, UUID string)
- `app.is_admin`
- `app.user_id`

Les politiques **UUID** utilisent `current_setting('app.current_tenant', true)::uuid`, aligné **v52_p1_003**.

---

## 4. Requêtes SQL à exécuter sur la base cible (preuve)

```sql
-- Remplacer <table> par le nom réel
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = '<table>' AND column_name = 'tenant_id';

SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname = '<table>';

SELECT policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public' AND tablename = '<table>';
```

---

## 5. Livrables associés

| Livrable | Chemin |
|----------|--------|
| Migration Alembic | `alembic/versions/094_security_market_mercurial_tenant_rls.py` |
| Scripts SQL idempotents | `scripts/security/*.sql` |
| Procédure ops | `docs/ops/SECURITY_HARDENING.md` |
| Tests | `tests/security/test_tenant_isolation.py` |

---

## 6. Prochaines étapes (hors 094)

1. **Cartographie `cases` → `process_workspaces`** : mandat données + code séparé (risque métier).
2. **Audit prod** : joindre les résultats des requêtes §4 pour chaque table listée par l’audit « Carte des organes ».
3. **`survey_campaigns` / enfants** : `tenant_id` ajouté en 094 pour cohérence avec `market_surveys.campaign_id`.
