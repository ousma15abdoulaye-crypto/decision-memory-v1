# SYSMAP — Cartographie système opposable (EXIT-PLAN-ALIGN-01)

**Référence :** EXIT-PLAN-ALIGN-01 · Mandat SYSMAP  
**Date :** 2026-03-21  
**Révision :** 2026-03-21 — dualité `main:app` / `src.api.main:app` explicite  
**Statut :** VÉRITÉ REPO — toute ligne ci-dessous est vérifiable par chemin de fichier, montage FastAPI ou commande de déploiement.

**Périmètre exclu de la cartographie détaillée :** rail annotation (Label Studio, `services/annotation-backend/`, exports M12, validate/QA, bridge, STRICT_PREDICT). Ce rail est **sous-système externe** au présent paquet ; seule la **compatibilité** (processus séparé, pas monté dans les apps ci-dessous sauf intégration explicite) est rappelée.

---

## 0. Point critique — deux applications FastAPI

Le dépôt contient **deux** objets `FastAPI` distincts. **Ce n’est pas équivalent** : ensembles de routes différents, risques opérationnels et de sécurité différents.

| Application | Module:attribute | Fichier | Usage documenté / observé |
|-------------|------------------|---------|---------------------------|
| **App_Racine** | `main:app` | [`main.py`](../../main.py) à la racine | **Railway / Procfile / [`start.sh`](../../start.sh)** : `uvicorn main:app` |
| **App_API_Modulaire** | `src.api.main:app` | [`src/api/main.py`](../../src/api/main.py) | Tests d’intégration ciblant l’app « complète » (ex. extraction phase0) ; **pas** la cible du `Procfile` par défaut |

**Preuve déploiement :** [`start.sh`](../../start.sh) ligne `exec uvicorn main:app` ; [`docs/RAILWAY_DEPLOY.md`](../RAILWAY_DEPLOY.md).

**Conséquence opposable :** toute revue sécurité ou couverture auth doit **nommer l’app** (`main:app` vs `src.api.main:app`). Le script [`scripts/audit_fastapi_auth_coverage.py`](../../scripts/audit_fastapi_auth_coverage.py) prend `--app` ; la CI actuelle utilise `main:app` pour un gate (voir `.github/workflows/ci-main.yml`).

---

## 1. Règle de nommage : « pipeline »

Dans ce dépôt, le mot **pipeline** recouvre au minimum **quatre** réalités distinctes :

| Nom SYSMAP | Rôle | Ancrage code |
|------------|------|----------------|
| **Pipeline_A** | Orchestration dossier (préflight → étapes → persistance `pipeline_runs`) | [`src/couche_a/pipeline/service.py`](../../src/couche_a/pipeline/service.py), [`src/couche_a/pipeline/router.py`](../../src/couche_a/pipeline/router.py) |
| **ExtractionEngine** | Extraction documentaire SLA-A/B, jobs, `structured_data` | [`src/extraction/engine.py`](../../src/extraction/engine.py), [`src/api/routes/extractions.py`](../../src/api/routes/extractions.py) |
| **Couche_A_Extraction_ML** | Extraction typée / LLM (TDR, offres) | [`src/couche_a/extraction.py`](../../src/couche_a/extraction.py) |
| **Mercuriale_parse** | Parse lignes mercuriale → queue Couche B | [`src/api/routers/mercuriale.py`](../../src/api/routers/mercuriale.py), [`src/couche_b/mercuriale/`](../../src/couche_b/mercuriale/) |
| **Rail_annotation** (externe) | Processus LS ↔ backend dédié — **hors SYSMAP détaillé** | [`services/annotation-backend/`](../../services/annotation-backend/) |

**Ne pas fusionner** ces lignes dans un seul mandat sans préciser la ligne SYSMAP.

---

## 2. Montage des routes par application

### 2.1 App_Racine (`main:app`) — [`main.py`](../../main.py)

Routers inclus **directement** (pas de try/except sur ces imports dans ce fichier) :

| Router | Module |
|--------|--------|
| Auth | [`src/auth_router.py`](../../src/auth_router.py) |
| Upload / legacy upload | [`src/couche_a/routers.py`](../../src/couche_a/routers.py) |
| Health | [`src/api/health.py`](../../src/api/health.py) |
| Cases | [`src/api/cases.py`](../../src/api/cases.py) |
| Documents | [`src/api/documents.py`](../../src/api/documents.py) |
| Analysis | [`src/api/analysis.py`](../../src/api/analysis.py) |
| Extractions | [`src/api/routes/extractions.py`](../../src/api/routes/extractions.py) |
| Scoring API | [`src/couche_a/scoring/api.py`](../../src/couche_a/scoring/api.py) |

**Absent de ce montage (vérifiable par lecture de `main.py`) :**  
`criteria` (Couche A), `mercuriale`, `price_check`, `pipeline_a`, `analysis_summary`, `geo`, `vendors`, middlewares M1 optionnels de `src/api/main.py`.

**Comité :** le module [`src/couche_a/committee/router.py`](../../src/couche_a/committee/router.py) définit un `APIRouter` mais **aucun** `include_router` vers ce router n’apparaît dans `main.py` ni dans `src/api/main.py` (recherche `committee` + `include_router` — **code présent, non exposé HTTP par défaut**).

### 2.2 App_API_Modulaire (`src.api.main:app`) — [`src/api/main.py`](../../src/api/main.py)

**Obligatoires :** criteria, auth, cases, health.

**Optionnels** (ImportError → `None`, warning log, route non montée) : extraction, documents, analysis, mercuriale, price_check, pipeline_a, analysis_summary, geo, vendors.

**Middlewares M1** (security headers, Redis rate limit) : chargement try/except dans ce fichier.

---

## 3. Couches packages (`src/`)

| Zone | Chemin | Fonction |
|------|--------|----------|
| Couche A | [`src/couche_a/`](../../src/couche_a/) | scoring, pipeline, criteria, committee (**service** utilisé par tests), price_check, audit, auth |
| Couche B | [`src/couche_b/`](../../src/couche_b/) | mercuriale, dictionary, IMC, normalisation |
| API | [`src/api/`](../../src/api/) | cases, documents, analysis, `main`, routes |
| DB | [`src/db/`](../../src/db/) | connexion, curseurs |
| Geo / vendors | [`src/geo/`](../../src/geo/), [`src/vendors/`](../../src/vendors/) | routes dédiées (souvent via app modulaire) |

---

## 4. Frontières sensibles (SEC / RUNTIME-DOC)

- **Accès dossier par `case_id` :** [`src/couche_a/auth/case_access.py`](../../src/couche_a/auth/case_access.py) — `require_case_access` ; la docstring indique les limites vs RLS DB.
- **Price check lit `couche_b.mercuriale_raw_queue` :** [`src/couche_a/price_check/engine.py`](../../src/couche_a/price_check/engine.py) — couplage SQL cross-schema + `importlib` vers normalisation Couche B.
- **Invariant Couche A / B (CI) :** [`tests/invariants/test_no_couche_b_import_in_couche_a.py`](../../tests/invariants/test_no_couche_b_import_in_couche_a.py) — **skippé** (gate non actif tel quel).
- **Boundary price_check :** [`tests/boundary/test_couche_a_b_boundary.py`](../../tests/boundary/test_couche_a_b_boundary.py) — périmètre **restreint** (price_check + router associé).

---

## 5. CI comme juge

- Workflow principal : [`.github/workflows/ci-main.yml`](../../.github/workflows/ci-main.yml).
- Gate auth heuristique : `python scripts/audit_fastapi_auth_coverage.py --app main:app --fail-prefix /api/extractions` (voir job CI — **portée limitée au préfixe configuré**).

---

## 6. Conditions de sortie SYSMAP

- [ ] Tout nouveau mandat **cite** une ligne du tableau §1 ou un montage §2 en précisant **App_Racine** ou **App_API_Modulaire**.
- [ ] Aucun mandat « pipeline » sans préciser **Pipeline_A**, **ExtractionEngine**, **Mercuriale_parse**, ou **rail externe annotation**.
- [ ] Toute revue SEC indique **quelle app** est en production et si **App_API_Modulaire** est utilisée quelque part (sinon **écarter** les routes « fantômes » de la surface prod ou documenter déploiement dual).

---

## 7. Note README

[`README.md`](../../README.md) a été aligné (2026-03-21) sur `uvicorn main:app` — cohérent avec §0 et Railway. **Il n’existe pas** `src/main.py` dans ce dépôt ; toute régression documentaire sur `src.main:app` = **ÉCART** dans la matrice RUNTIME-DOC.
