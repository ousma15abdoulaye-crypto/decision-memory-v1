# P1 — Livrable 5 : Schéma de base de données

## 1. Méthode DDL « complet »

Le DDL effectif en production est la **composition de toutes les migrations** Alembic dans l’ordre du graphe de révisions.

- **Répertoire** : [`alembic/versions/`](../../../alembic/versions/) — **106** fichiers `.py` (mesure 2026-04-06).
- **Commande de vérité** : `alembic upgrade head` sur une base PostgreSQL vierge, puis `pg_dump --schema-only` (ou inspection `information_schema`).

**Note honnête** : tout DDL « prod » peut diverger si des correctifs manuels ont été appliqués hors migrations — **NON TRANCHÉ** sans audit DBA.

---

## 2. Schémas PostgreSQL

Les migrations créent des objets sous :

- `public` (majorité)
- `couche_a`, `couche_b` (dictionnaires, agents, files)
- partitions / tables dérivées (`dms_event_index_2025_h2`, etc.)

---

## 3. Tables — inventaire (extrait migrations `CREATE TABLE`)

Liste non exhaustive mais couvrant les **soupçons du mandat** :

| Nom (mandat) | Présence |
|--------------|----------|
| `tenants` | Oui — `068_create_tenants.py` |
| `users` | Oui — `004_users_rbac.py` |
| `roles` / `permissions` / `role_permissions` | Oui — `004` |
| `user_tenants` | Oui — `051_cases_tenant_user_tenants_rls.py` |
| `process_workspaces` | Oui — `069_process_workspaces_events_memberships.py` |
| `workspace_memberships` | Oui — `069` |
| `workspace_events` | Oui — `069` |
| `workspace_state_transitions` | **NON** (nom exact) — utiliser `workspace_events` |
| `supplier_bundles` / `bundle_documents` | Oui — `070_supplier_bundles_documents.py` |
| `evaluation_documents` | Oui — `056_evaluation_documents.py` |
| `source_package_documents` | Oui — `078_source_package_documents_bloc5.py` |
| `committee_sessions` / `committee_deliberation_events` | Oui — `071_committee_sessions_deliberation.py` |
| `m12_correction_log` / `m13_correction_log` | Oui — `054`, `057` |
| `extraction_corrections` | Oui — `015`/`019_consolidate_extraction_corrections.py` |
| `extraction_jobs` / `extraction_errors` | Oui — `012`–`014` |
| `market_signals_v2` / `survey_campaigns` / `market_surveys` | Oui — `043_market_signals_v11.py`, `042_market_surveys.py` |
| `dms_embeddings` / `candidate_rules` | Oui — `064`, `063` |
| `dms_event_index` | Oui — `061_dms_event_index.py` |
| `llm_traces` | Oui — `065_llm_traces.py` |
| `audit_log` | Oui — `038_audit_hash_chain.py` |
| `m13_regulatory_profile_versions` | Oui — `057` |
| `agent_checkpoints` / `agent_runs_log` | Oui — `045_agent_native_foundation.py` (schéma `couche_a`) |
| `notifications` | **NON** trouvé sous ce nom exact dans le grep `CREATE TABLE` initial |

**Autres tables majeures** : `cases`, `artifacts`, `pipeline_runs`, `pipeline_step_runs`, `score_runs`, `committee_*` (legacy `028`), `vendors`, `items`, `geo_*`, `mercuriale_*`, etc. — voir grep `CREATE TABLE` dans `alembic/versions`.

---

## 4. Vues, triggers, fonctions

- **RLS** : migrations `051`–`055`, `052_dm_app_rls_role`, `053_dm_app_enforce_security_attrs`, etc.
- **Triggers comité / append-only** : `030`, `031`, `071`, scripts d’intégrité dans `tests/db_integrity/`.
- **Refresh marché** : `060_market_coverage_auto_refresh.py`, etc.

Le détail SQL est **dans chaque fichier de migration** — recopier l’intégralité ici serait une duplication ; la procédure §1 produit le DDL agrégé.

---

## 5. Liste ordonnée des migrations

Voir `alembic heads` et `alembic history` sur la branche courante — **tête unique** imposée par CI ([`.github/workflows/ci-main.yml`](../../../.github/workflows/ci-main.yml) garde « single head »).

---

## 6. Limitations

- **RLS** : politiques exactes par table dans migrations dédiées — lecture fichier par fichier requise pour une copie « conforme avocat ».
- **schema_validator.py** (annotation) : **gelé** — ne pas modifier pour la doc.
