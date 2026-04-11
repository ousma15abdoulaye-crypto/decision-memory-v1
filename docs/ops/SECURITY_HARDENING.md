# Durcissement sécurité multi-tenant (RLS, `tenant_id`, triggers)

**Référence** : mandat sécurité schéma DMS — 2026-04-11  
**Rapport d’audit** : `docs/security_audit_report.md`

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
| `score_history` | Trigger `trg_score_history_append_only` si absent et si `public.fn_reject_mutation` existe |

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
