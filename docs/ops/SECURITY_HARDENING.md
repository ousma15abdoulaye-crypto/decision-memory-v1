# Durcissement sécurité multi-tenant (RLS, `tenant_id`, triggers)

**Référence** : mandat sécurité schéma DMS — 2026-04-11  
**Rapport d’audit** : `docs/security_audit_report.md`

---

## 2026-04-11 — MIG-094-095 appliquée en prod

**Migrations** : `094_security_market_mercurial_tenant_rls` ; `095_tenant_id_default_offers_extractions`  
**Tables** (colonne `tenant_id` + RLS selon 094) : `survey_campaigns`, `survey_campaign_items`, `survey_campaign_zones`, `market_surveys`, `price_anomaly_alerts`, `mercuriale_sources`, `mercurials`, `market_signals_v2`, `offers`, `extractions`, `analysis_summaries`  
**RLS** : `ENABLE` + `FORCE` + politique `*_tenant_uuid_isolation` (`app.current_tenant` / `app.is_admin`)  
**Smoke** (prod, `app.is_admin = true` dans une **transaction** unique — voir ci-dessous) : counts validés — `offers` 25, `extractions` 24, `analysis_summaries` 151, `mercurials` 27 396, `offer_extractions` 6 (hors périmètre 094/095 mais contrôle de non-régression).  
**Correctif 094** : backfill `analysis_summaries` — `DISABLE TRIGGER trg_analysis_summaries_append_only` / `UPDATE` / `ENABLE TRIGGER` (trigger append-only **035** / INV-AS3 bloquait l’UPDATE).  
**Préalable prod** : table `alembic_version` contenait **deux** lignes (`076_fix_offer_extractions_fk_to_bundles` + `v52_p2_001_price_line_market_delta`) alors que **076** est ancêtre de la chaîne menant à **v52** ; suppression de la ligne **076** redondante avant `alembic upgrade head`.  
**SCRIPTS-RLS-01 (2026-04-11)** : `SignalEngine._conn()` appelle `apply_rls_session_vars_to_connection(..., transaction_local=False)` ; `scripts/compute_market_signals.py` et `scripts/batch_signal_from_map.py` posent `set_rls_is_admin(True)` et appliquent les GUC en **session** sur la connexion partagée (sinon les `COMMIT` de `persist_signal` effacent les GUC transactionnels).  
**Rollback** : en cas de retour arrière ciblé, viser la révision **`6ce2036bd346`** (pas `093`) : `alembic downgrade 095` puis `094` puis, si besoin, réparation manuelle de `alembic_version` sous contrôle CTO.

**Note smoke test** : avec `autocommit`, `set_config('app.is_admin', …, true)` (local à la transaction) ne s’applique pas aux `SELECT COUNT` suivants ; utiliser `set_config(..., false)` **ou** une transaction explicite (`autocommit=False` + `commit`).

---

## 1. Migrations `094` + `095`

### `094_security_market_mercurial_tenant_rls`

| Zone | Mesure |
|------|--------|
| Campagnes & enquêtes | `tenant_id` UUID NOT NULL sur `survey_campaigns`, `survey_campaign_items`, `survey_campaign_zones`, `market_surveys`, `price_anomaly_alerts` |
| Mercuriale | `tenant_id` sur `mercuriale_sources` et `mercurials` |
| Signaux M9 | `tenant_id` sur `market_signals_v2` |
| Couche A héritée | `tenant_id` UUID sur `offers`, `extractions`, `analysis_summaries` (backfill **conservateur** : tenant par défaut — voir §4) |
| Isolation | `ENABLE ROW LEVEL SECURITY`, `FORCE ROW LEVEL SECURITY`, politique `*_tenant_uuid_isolation` (`app.current_tenant::uuid` + `app.is_admin`) |
| `score_history` | Trigger `trg_score_history_append_only` si absent et si `public.fn_reject_mutation` existe (souvent déjà créé par **059**) |
| `downgrade` 094 | Ne supprime **pas** ce trigger : il appartient à la chaîne **059**, pas à 094 |

### `095_tenant_id_default_offers_extractions`

- Fonction **`public.dms_default_tenant_id()`** : `sci_mali` sinon premier `tenants` par `code`.
- **DEFAULT** sur `tenant_id` pour : `offers`, `extractions`, `analysis_summaries`, `mercuriale_sources`, `mercurials`.
- Évite les **NotNullViolation** sur les fixtures de tests / INSERT sans `tenant_id` tout en conservant le RLS sur les lignes.

---

## 2. Scripts SQL (`scripts/security/`)

| Fichier | Rôle |
|---------|------|
| `add_tenant_id_and_rls.sql` | Pointeur vers la migration 094 (évite duplication DDL) |
| `fix_append_only_triggers.sql` | Idempotent — trigger append-only `score_history` |
| `deprecate_orphan_tables.sql` | Renommage `django_*` / `auth_*` **uniquement si tables présentes** |
| `migrate_cases_to_workspaces.sql` | **Template vide** — mandat CTO requis |

---

## 3. Procédure de déploiement

1. **Sauvegarde** logique ou snapshot avant `alembic upgrade`.
2. `alembic upgrade head` (inclut `094_security_market_mercurial_tenant_rls`).
3. Vérifier qu’au moins une ligne existe dans `public.tenants` (sinon la migration **échoue** volontairement).
4. Exécuter les requêtes du §4 de `docs/security_audit_report.md` sur chaque table critique et archiver les résultats.
5. Lancer les tests :  
   `pytest tests/security/test_tenant_isolation.py -v` (marqueur `db`, DB migrée).

---

## 4. Backfill `offers` / `extractions` / `analysis_summaries`

`cases.tenant_id` est historiquement du **TEXT** (souvent `tenant-{user_id}`), pas un UUID `tenants.id`.  
La migration **094** assigne le **tenant par défaut** (`sci_mali` si présent, sinon premier `tenants` par `code`) pour éviter un jointure faux positive.

**Action recommandée post-déploiement** : mandat données pour réattribuer ligne par ligne selon la cartographie métier réelle.

---

## 5. Précautions pour les futures migrations

- Ne **pas** `DISABLE ROW LEVEL SECURITY` sur les tables tenant-scoped sans ADR + revue sécurité.
- Toute nouvelle table avec données sensibles : **`tenant_id` UUID NOT NULL** + **FK `tenants`** + **RLS + FORCE** + politique alignée sur `app.current_tenant`.
- Après `CREATE TABLE`, ajouter les **GRANT** nécessaires aux rôles applicatifs (`dm_app`, rôles de test RLS).

---

## 6. Tests

- `tests/security/test_tenant_isolation.py` — isolation `market_surveys` et refus INSERT cross-tenant `mercurials`.
- CI : exiger job avec Postgres + `alembic upgrade head` + ce fichier (déjà le cas pour les workflows DB complets).

---

## 7. Smoke E2E (ZIP → bundles en moins de 60 s)

À exécuter après merge / déploiement pipeline (workspace de test connu).

1. **Préparer un ZIP** : dossier local `data/test_zip/` (fichiers `.docx` de test) → archiver en `.zip`.
2. **Upload** : flux UI « import / pipeline » du workspace cible, ou endpoint documenté dans le runbook pipeline (même JWT / tenant que le workspace).
3. **Contrôle** : dans les **60 secondes**, vérifier que des bundles ont été créés pour ce workspace, par ex.  
   `SELECT COUNT(*) FROM supplier_bundles WHERE workspace_id = '<uuid>';`  
   attendu : count strictement positif (ou équivalent via API workspace si exposé).

En échec : file d’attente worker ARQ, logs `arq` / API, et RLS (`app.current_tenant` / `app.is_admin`) sur les routes pipeline.
