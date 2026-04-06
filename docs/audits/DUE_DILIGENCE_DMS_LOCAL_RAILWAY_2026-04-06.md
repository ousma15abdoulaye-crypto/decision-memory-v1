# Due diligence technique DMS — local à Railway

**Date du rapport :** 2026-04-06  
**Référence code auditée :** `90365aba` (branche `main`)  
**Méthode :** plan « Due diligence DMS locale-Railway » — inventaire dépôt, chaîne d’exécution Docker, audits SEC-MT, Alembic, CI, worker ARQ, service annotation, sondes lecture seule Railway, matrices doc existantes.

**Limites (explicites) :**

- Ce rapport **ne certifie pas** l’absence de défauts ; il consolide des **preuves** à date.
- Les audits d’auth FastAPI sont **heuristiques** (arbres de dépendances), pas une preuve d’absence d’IDOR dans les corps de handlers.
- Charge, latence p99, et incidents runtime **hors logs** ne sont pas mesurés ici.
- Un clone avec `.env.railway.local` a permis **`preflight_cto_railway_readonly.py`** ; sans URL/credentials, les sondes Railway seraient **incomplètes**.

---

## 1. Scope et périmètre d’autorité

| Élément | Valeur |
|--------|--------|
| Commit | `90365aba36245ede69f753535588a1a96be4e974` |
| Branche | `main` |
| Autorité gelée | [`docs/freeze/CONTEXT_ANCHOR.md`](../freeze/CONTEXT_ANCHOR.md), [`CLAUDE.md`](../../CLAUDE.md) |

**Services déployables identifiés :**

| Service | Fichier / commande | Rôle |
|---------|-------------------|------|
| API DMS | [`Dockerfile`](../../Dockerfile) → [`start.sh`](../../start.sh) → `uvicorn main:app` | Production Railway (API) |
| Worker ARQ | [`railway.worker.toml`](../../railway.worker.toml) → `arq src.workers.arq_config.WorkerSettings` | Jobs async (Redis) |
| Annotation | [`services/annotation-backend/Dockerfile`](../../services/annotation-backend/Dockerfile) | Label Studio / prédiction — **monorepo root requis** pour `COPY` |

**Dual FastAPI (décision documentée) :** production = [`main:app`](../../main.py) ; [`src.api.main:app`](../../src/api/main.py) = référence / tests — voir [`docs/adr/ADR-DUAL-FASTAPI-ENTRYPOINTS.md`](../adr/ADR-DUAL-FASTAPI-ENTRYPOINTS.md).

---

## 2. Inventaire dépôt (métriques)

| Zone | Fichiers `.py` (approx.) | Lignes (approx.) |
|------|---------------------------|------------------|
| `src/` + `tests/` + `services/` + `scripts/` + `alembic/` | **833** | **~108 906** |

| Artefact | Détail |
|----------|--------|
| `requirements.txt` | ~68 lignes utiles — **source unique** pour Docker API ([`Dockerfile`](../../Dockerfile) `pip install -r requirements.txt`) |
| `pyproject.toml` | Black, Ruff, pytest — **pas** de liste de deps runtime concurrente |
| Workflows CI | [`.github/workflows/ci-main.yml`](../../.github/workflows/ci-main.yml) : Postgres **15** (`pgvector/pgvector:pg15`), `DATABASE_URL` superuser + `DATABASE_URL_RLS_TEST` pour `dm_app` |

---

## 3. Chaîne d’exécution locale / image = proxy Railway

- **CMD :** `./start.sh` — exige `DATABASE_URL` ; migrations **désactivées** sauf `DMS_ALLOW_RAILWAY_MIGRATE=1` (aligné RÈGLE-ANCHOR-06 / runbook ops).
- **Risque ops :** le code peut être à `alembic head` **080** alors que la base Railway **n’a pas** reçu `upgrade` — voir § Findings **DD-001**.

**Parité OpenAPI `main:app` vs `src.api.main:app` (mesure directe sur `90365aba`) :**

| Application | Nombre de chemins OpenAPI |
|-------------|---------------------------|
| `main:app` | **87** |
| `src.api.main:app` | **71** |

**Chemins présents uniquement dans `main:app` (extrait) :**  
`/health`, `/api/cases/{case_id}/criteria/by-category`, `/api/cases/{case_id}/criteria/validation`, uploads DAO/offre, `/api/m13/status`, `/api/scoring/*`, vues `/views/...`, `/api/memory/{case_id}`, etc.

**Conséquence :** la production **n’est pas** un sous-ensemble strict de `src.api.main` — c’est l’**inverse** : `main:app` est **plus large**. Les tests qui n’importent que `src.api.main` **ne couvrent pas** toute la surface Railway.

**Smoke test :** [`tests/test_main_app_parity_smoke.py`](../../tests/test_main_app_parity_smoke.py) — **2 passed** (criteria + `/api/m14` + geo conditionnel). La DD recommande d’**étendre** ce smoke avec les préfixes W1/W2/W3 (`/api/workspaces`, committee seal, exports PV) si gate merge.

---

## 4. Sécurité — audit FastAPI (SEC-MT)

**Commandes exécutées (locale) :**

```text
python scripts/audit_fastapi_auth_coverage.py --app main:app
python scripts/audit_fastapi_auth_coverage.py --app src.api.main:app
```

**Sorties archivées :**

- [`docs/audits/artifacts/sec_mt_01_main_app.txt`](artifacts/sec_mt_01_main_app.txt)
- [`docs/audits/artifacts/sec_mt_01_src_api_main.txt`](artifacts/sec_mt_01_src_api_main.txt)

**CI (référence) :** `ci-main.yml` impose `--fail-prefix` sur `/api/extractions`, `/api/m14`, et gates supplémentaires sur `src.api.main` (mercuriale, vendors, etc.). La DD locale **n’a pas** rejoué `--fail-prefix` avec code de sortie d’échec ; le rapport CI PR/push fait foi pour **bloquer** les régressions.

**Exemple de routes « SENS=yes » sans case-guard détecté dans l’arbre de deps** (à interpréter avec [`docs/audits/SEC_MT_01_BASELINE.md`](SEC_MT_01_BASELINE.md) : RLS / logique métier possible hors deps) :  
`/api/cases/{case_id}/criteria/by-category`, `/api/download/{case_id}/{kind}`, `/api/m14/evaluations/{case_id}`, `/api/memory/{case_id}`, etc.

**Points fixes documentés :**

- **Vert CI ≠ RLS prod** si les tests `DATABASE_URL_RLS_TEST` ne reflètent pas le rôle `dm_app` réel — voir baseline SEC-MT et [`tests/integration/test_rls_dm_app_cross_tenant.py`](../../tests/integration/test_rls_dm_app_cross_tenant.py) (skippés sans variable).

---

## 5. Données — Alembic et dérive schéma

| Vérification | Résultat |
|--------------|----------|
| `alembic heads -v` (dépôt) | **Une seule tête** : `080_market_signals_v2_zone_id_index` |
| `preflight_cto_railway_readonly.py` (Railway RO) | `alembic_version` = **`079_bloc5_confidence_qualification_signal_log`** |

**Écart critique :** le dépôt **080** n’est **pas** appliqué sur la base Railway interrogée — voir finding **DD-001**.

**CI :** garde `HEAD_COUNT=1` + `alembic upgrade head` + contrôles SQL post-migration (forensic `extraction_corrections`, etc.).

---

## 6. Workers ARQ

- **Config :** [`src/workers/arq_config.py`](../../src/workers/arq_config.py) — `REDIS_URL` requis pour `redis_settings` ; si absent, worker potentiellement **non fonctionnel**.
- **Tâches :** `index_event`, `detect_patterns`, `generate_candidate_rules`, `run_pass_minus_1`, `project_workspace_events_to_couche_b`, `project_sealed_workspace`.
- **Risque système :** API et worker partagent **PostgreSQL** et **Redis** — saturation ou indisponibilité Redis impacte rate-limit côté API et jobs côté worker.

---

## 7. Service annotation-backend

- **Build :** monorepo **root** obligatoire (commentaire en tête du [`Dockerfile`](../../services/annotation-backend/Dockerfile)).
- **Coupe :** `COPY` partiel de `src/annotation`, `src/procurement` — surface **réduite** vs API principale ; risque de **ModuleNotFoundError** si nouvel import transversal sans mise à jour Dockerfile.
- **CI :** `pytest services/annotation-backend/tests` + tests export M12 dans `ci-main.yml`.

---

## 8. Railway — preuves (sondes RO)

**Script :** [`scripts/preflight_cto_railway_readonly.py`](../../scripts/preflight_cto_railway_readonly.py)

**Résultat typé (2026-04-06, environnement avec `DATABASE_URL` / Railway) :**

| Sonde | Observation |
|-------|-------------|
| Rôle DB | `postgres` (superuser) sur instance Railway |
| Version PostgreSQL | **17.9** (vs **15** en CI) — écart de version |
| `alembic_version` | **079** (dépôt **080**) |
| Tables cœur | `process_workspaces`, `committee_sessions`, `vendors`, `supplier_bundles` présentes |

**Healthchecks API :** [`main.py`](../../main.py) expose `GET /health` (sonde légère) ; commentaire renvoie à `GET /api/health` pour contrôle DB/Redis — la DD n’a pas invoqué d’URL publique HTTP (non disponible dans cette session) ; à compléter avec `curl` vers le domaine Railway en ops.

**Script seal (hardening) :** [`scripts/hardening_product_sql_checks.py`](../../scripts/hardening_product_sql_checks.py) — nécessite `DATABASE_URL` + `workspace_id` ; non exécuté sans mandat workspace.

---

## 9. Documentation vs runtime (réutilisation matrice existante)

La matrice [`RUNTIME_DOC_ALIGNMENT_MATRIX_EXIT_01.md`](RUNTIME_DOC_ALIGNMENT_MATRIX_EXIT_01.md) documente déjà des **ÉCARTS** (Couche A/B, dual-app, committee router, etc.). La DD **confirme** la pertinence de traiter **doc / code / ADR** comme sources séparées à réconcilier.

---

## 10. Findings (sévérité S1–S4)

| ID | S | Composant | Description | Preuve / action |
|----|---|-----------|-------------|-----------------|
| **DD-001** | **S1** | Alembic / Railway | Base Railway à **079** ; dépôt à **080** — index / comportement attendu de **080** absents en prod tant que migration non appliquée. | `alembic heads` local + sortie `preflight` § alembic |
| **DD-002** | **S2** | Dual-app / tests | `main:app` **87** routes vs `src.api.main` **71** — parité smoke **minimale** ; risque de régression non détectée sur routes **prod-only**. | Script OpenAPI + `test_main_app_parity_smoke.py` |
| **DD-003** | **S2** | Postgres | CI **15** vs Railway **17** — écarts subtils (index, planner, extensions). | `preflight` `version()` vs `ci-main.yml` service image |
| **DD-004** | **S3** | Ops | `start.sh` ne migre pas par défaut — dépendance au **processus manuel** / flag `DMS_ALLOW_RAILWAY_MIGRATE` / `apply_railway_migrations_safe.py`. | [`start.sh`](../../start.sh) |
| **DD-005** | **S3** | Sécurité | Routes sensibles sans `require_case_access` **dans l’arbre deps** — mitigation possible via RLS / code corps ; **revue manuelle** ou tests d’intégration requis pour verdict final. | `sec_mt_01_main_app.txt` + SEC_MT_01_BASELINE |
| **DD-006** | **S4** | Worker | `REDIS_URL` vide → `redis_settings=None` — comportement ARQ à valider au déploiement. | [`arq_config.py`](../../src/workers/arq_config.py) |

---

## 11. Verdicts séparés

**Produit :** Le DMS couvre **ingestion, extraction, critères, marché, comité, scellage PV, M14, exports** — la surface est **large** et **cohérente** avec un produit en **industrialisation**. Le verdict **AMBRE** documenté (seal pilote, preuves ops) reste **crédible** : la forme produit est là ; la **fiabilité perçue par l’utilisateur final** dépend encore des **boucles prod** (migrations, re-scellage, déploiements).

**Technique :** **Solide sur l’outillage** (CI single-head Alembic, migrations testées, audits d’auth, RLS testable, Docker reproduisible). **Fragilités :** dérive **079/080**, dual-app **asymétrique**, **heuristique** SEC-MT sans substitut automatique à la revue métier.

**Opérations :** Dépendance forte aux **runbooks**, flags (`DMS_ALLOW_RAILWAY_MIGRATE`), et **discipline** (E-98). La DD **ne remplace pas** un monitoring (logs, alertes, SLO) — non évalué ici.

---

## 12. Travaux priorisés

1. **P0 —** Appliquer **080** sur Railway (ou documenter blocage explicite) et revérifier `preflight` + fonctionnalités dépendantes (index `market_signals_v2(zone_id)`).
2. **P1 —** Étendre **smoke OpenAPI** `main:app` pour `/api/workspaces`, committee seal, exports PV.
3. **P1 —** Documenter / automatiser **alignement** version Postgres CI vs prod (au minimum matrice de risque).
4. **P2 —** Revue ciblée des routes **DD-005** avec équipe sécurité / RLS.
5. **P2 —** Vérifier worker ARQ avec **REDIS_URL** réel sur Railway (logs, file d’attente).

---

## 13. Références internes

- [`docs/audits/SEC_MT_01_BASELINE.md`](SEC_MT_01_BASELINE.md)  
- [`docs/audits/SYSMAP_DMS_EXIT_PLAN_01.md`](SYSMAP_DMS_EXIT_PLAN_01.md)  
- [`docs/ci/COVERAGE_GATE.md`](../ci/COVERAGE_GATE.md) (seuil **65 %** si `.milestones/M-TESTS.done`)  
- [`docs/ops/RAILWAY_ARQ_WORKER_SERVICE.md`](../ops/RAILWAY_ARQ_WORKER_SERVICE.md) (réf. worker)

---

---

## Addendum — remédiation 2026-04-06

- **DD-001 :** migration `080_market_signals_v2_zone_id_index` appliquée sur Railway (dry-run puis `apply_railway_migrations_safe.py --apply`) ; `alembic_version` = **080** ; index `idx_msv2_zone_id` vérifié. Détail : [`docs/ops/POST_DD_RISK_REMEDIATION_2026-04-06.md`](../ops/POST_DD_RISK_REMEDIATION_2026-04-06.md).
- **DD-002 à DD-006 :** livrables documentaires et smoke étendu — même référence.

*Fin du rapport — Due diligence DMS local → Railway, 2026-04-06.*
