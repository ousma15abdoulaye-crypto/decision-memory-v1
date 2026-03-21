# SEC-MT-00 — Modèle de menace minimal (EXIT-PLAN-ALIGN-01)

**Référence :** EXIT-PLAN-ALIGN-01 · Mandat SEC-MT  
**Date :** 2026-03-21  
**Révision :** 2026-03-21 — post SEC-MT-01 (merge durcissement)  
**Statut :** SOCLE **mis à jour** — SEC-MT-01 **partiellement livré** (voir §4–5) ; suite §7. **Ne pas** mélanger avec le rail annotation (hors périmètre).

---

## 0. Préambule opposable

Ce document **ne** prétend pas que le système est « multi-tenant complet ». Il liste **surfaces réelles** et **barrières vérifiables dans le code**. Toute affirmation forte (RLS, isolation totale) exige un mandat **SEC-MT-01** avec preuves SQL + tests.

---

## 1. Surfaces d’attaque (réelles dans le repo)

| Surface | Description | Ancrage |
|---------|-------------|---------|
| **API HTTP — App_Racine** | `main:app` — surface **prod par défaut** (Railway) | [`main.py`](../../main.py), [`start.sh`](../../start.sh) |
| **API HTTP — App_API_Modulaire** | `src.api.main:app` — routes additionnelles (criteria, pipeline_a, mercuriale, etc.) si montée | [`src/api/main.py`](../../src/api/main.py) |
| **Auth JWT + RBAC** | Émission / validation token, rôles | [`src/auth_router.py`](../../src/auth_router.py), [`src/couche_a/auth/`](../../src/couche_a/auth/) |
| **IDOR dossier / document** | Accès par `case_id` / `document_id` | [`src/couche_a/auth/case_access.py`](../../src/couche_a/auth/case_access.py) ; routes dans [`src/api/cases.py`](../../src/api/cases.py), documents, analysis |
| **Tenant applicatif** | `tenant_id` sur création case et claims | [`src/api/cases.py`](../../src/api/cases.py) (ex. exigence `tenant_id`) |
| **Routers optionnels absents** | Capacité non montée sans échec démarrage | `src/api/main.py` (optionnels) |
| **PostgreSQL** | Données dossiers, schémas public / `couche_b` | [`alembic/`](../../alembic/) |
| **Rate limit / headers** | Dépend Redis + import (app modulaire) | [`src/couche_a/auth/middleware.py`](../../src/couche_a/auth/middleware.py) |

**Multi-tenant DB (RLS) :** **partiellement attesté** (2026-03) — migrations `051` + rôle applicatif `dm_app` (`052`/`053`) + test d’intégration cross-tenant + `set_config` sur connexions dédiées (pipeline, analysis_summary, committee). **CI Postgres superuser** ne prouve pas RLS en prod : voir [`SEC_MT_01_BASELINE.md`](SEC_MT_01_BASELINE.md) et [`OPS_SEC_MT_PRODUCTION.md`](OPS_SEC_MT_PRODUCTION.md). Politique données export M15 : [`DATA-M15.md`](../mandates/DATA-M15.md).

---

## 2. Acteurs

- **Utilisateur authentifié** (buyer, evaluator, committee, admin, viewer).
- **Admin** — bypass `owner` dans `require_case_access` (voir implémentation).
- **Attaquant** — JWT volé, énumération d’UUID, accès direct API, confusion entre les deux apps FastAPI si les deux sont exposées.

---

## 3. Scénarios d’abus (priorisés)

1. **IDOR :** route prenant `case_id` / `document_id` **sans** `require_case_access` (ou équivalent) → lecture / écriture cross-utilisateur.
2. **Surface double :** `App_API_Modulaire` exposée en prod **en parallèle** de `App_Racine` sans inventaire des routes → routes « oubliées » non durcies.
3. **Dépendance à un router optionnel :** garantie métier supposée alors que l’import a échoué (app modulaire).
4. **Rate limit désactivé :** middleware non chargé → abuse brute force / scraping.
5. **Cross-tenant SQL :** requêtes sans filtre organisationnel si le modèle introduit plusieurs tenants au niveau ligne (à valider par schéma).

---

## 4. Barrières déjà présentes (vérifiables)

- **Contrôle applicatif case/document :** `require_case_access`, `require_document_case_access` et dépendances FastAPI **`require_case_access_dep` / `require_document_case_access_dep`** (visibles par l’audit CI) — [`case_access.py`](../../src/couche_a/auth/case_access.py).
- **JWT + dépendances FastAPI** sur les routes qui les déclarent ; app modulaire : gates sur `/mercuriale`, `/price-check`, `/vendors`, `/api/cases` (sensitive), `/api/documents`, `/api/analysis`, `/api/memory`, `/api/scoring`, etc. — voir [`.github/workflows/ci-main.yml`](../../.github/workflows/ci-main.yml).
- **Outil d’audit :** [`scripts/audit_fastapi_auth_coverage.py`](../../scripts/audit_fastapi_auth_coverage.py) — `get_current_user`, garde-fous case/document, `--fail-sensitive-prefix`, rapports MD/CSV.
- **Baseline & dual-app :** [`SEC_MT_01_BASELINE.md`](SEC_MT_01_BASELINE.md) ; ops Redis / health / secrets : [`OPS_SEC_MT_PRODUCTION.md`](OPS_SEC_MT_PRODUCTION.md).
- **RLS + rôle `dm_app` :** migrations Alembic `051`–`053` ; test [`tests/integration/test_rls_dm_app_cross_tenant.py`](../../tests/integration/test_rls_dm_app_cross_tenant.py).

---

## 5. Lacunes explicites (restes honnêtes)

- **Inventaire IDOR « zéro trou » :** la couverture est **forte mais heuristique** (arbre de deps uniquement) ; toute **nouvelle** route sensible doit utiliser `Depends(require_*_dep)` dès l’écriture — `/api/extractions` : gate `--fail-sensitive-prefix` active (refactor deps).
- **RLS en production :** la preuve opposable = connexion **non superuser** + `NOBYPASSRLS` + politiques ; pas seulement CI verte — runbook [`OPS_SEC_MT_PRODUCTION.md`](OPS_SEC_MT_PRODUCTION.md).
- **Une seule app en prod :** décision documentée dans [`SEC_MT_01_BASELINE.md`](SEC_MT_01_BASELINE.md) (`main:app`) ; toute exposition parallèle de `src.api.main:app` = ré-inventaire complet des gates.
- **Export / qualité données M15 :** politique mandat [`DATA-M15.md`](../mandates/DATA-M15.md) — exécution technique et owner produit à finaliser.

---

## 6. Règles anti-dérive

- Ne pas étiqueter « sécurisé multi-tenant » sans preuve DB + tests.
- Ne pas mélanger ce chantier avec Label Studio / export M12 / `annotation-backend`.
- Toute analyse de routes doit commencer par **`main:app`** (vérité Railway) puis **`src.api.main:app`** si applicable.

---

## 7. Suite recommandée (post SEC-MT-01)

1. **SEC-MT-02 — suite :** étendre le même pattern (deps + `--fail-sensitive-prefix`) à toute **nouvelle** surface `{case_id|document_id|job_id}` ; revue périodique des sorties audit.
2. **DATA-M15 :** désigner l’owner (échéance §5 mandat), remplir le rapport [`M15_validation_report.md`](../reports/M15_validation_report.md) au gel — mandat [`DATA-M15.md`](../mandates/DATA-M15.md).
3. **Backlog (priorité produit) :** voir [`SEC_MT_POST_MERGE_BACKLOG_OPTIONAL.md`](SEC_MT_POST_MERGE_BACKLOG_OPTIONAL.md) (`tenant_id` vendors, Compose `dm_app`, invariant `test_couche_a_b_boundary`).
4. **Inventaires :** régénérer les sorties décrites dans [`SEC_MT_01_BASELINE.md`](SEC_MT_01_BASELINE.md) lors des jalons (commandes `audit_fastapi_auth_coverage.py`).
