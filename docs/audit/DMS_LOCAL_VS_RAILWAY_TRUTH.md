# DMS — Vérité local ↔ Railway ↔ documentation

**Référence :** DMS-MAP-M0-M15-001 — Livrable 4  
**Date probe :** 2026-04-04  
**Branche probe :** `main` @ `ca4c8389` (HEAD au moment du mandat)

---

## 1. Alembic — dépôt (preuve)

| Probe | Commande / résultat |
|-------|---------------------|
| Heads | `alembic heads` → **une seule ligne** : `067_fix_market_coverage_trigger (head)` |
| Chaîne | Fichiers sous `alembic/versions/` — head unique **067** (merge VIVANT V2 + fix trigger matview) |

**Preuve :** sortie CLI locale, 2026-04-04.

---

## 2. Alembic — local `current` (échec connexion)

| Probe | Résultat |
|-------|----------|
| `alembic current` | **Échec** : `psycopg.OperationalError` — connexion `127.0.0.1:5432`, utilisateur `dms`, authentification refusée |

**Interprétation :** l’état de révision **sur disque de travail** n’est pas vérifiable par `alembic current` sans `DATABASE_URL` valide + Postgres local joignable. Cela **ne contredit pas** le head fichier ; cela documente un **gap opératoire** poste Windows/Docker (déjà capitalisé en session M15 : auth TCP host ↔ conteneur).

**Action :** utiliser `docker exec … psql` ou URL Railway via `scripts/with_railway_env.py` pour un `current` prod.

### 2.1. `DATABASE_URL` — alignement docker-compose vs `.env.local`

| Source | Valeur attendue |
|--------|-----------------|
| `docker-compose.yml` (service Postgres du dépôt) | Utilisateur / mot de passe / base **`dms` / `dms` / `dms`**, port **5432** mappé sur l’hôte |
| URL canonique localhost (hôte → conteneur) | `postgresql+psycopg://dms:dms@localhost:5432/dms` (voir aussi `.env.example`, `.env.local.example`) |

**Piège fréquent :** un `.env.local` copié depuis un exemple avec `postgres:postgres@.../decision_memory_dev` alors que seul le conteneur `dms` tourne → échec Alembic / pytest d’intégration (`authentification par mot de passe échouée pour l'utilisateur postgres`). Corriger en alignant `DATABASE_URL` sur l’instance réellement joignable (Compose ou Postgres natif), sans mélanger les deux.

**Port 5432 déjà pris :** si `docker compose up` renvoie « Bind for 0.0.0.0:5432 failed: port is already allocated », un PostgreSQL hôte occupe 5432. Soit l’arrêter temporairement pour lancer le conteneur `dms`, soit adapter le mapping `ports` du service `postgres` dans `docker-compose.yml` (ex. `5433:5432`) et utiliser `...@localhost:5433/dms` dans `DATABASE_URL`.

---

## 3. Railway — vérité attendue (sources repo)

| Source | Contenu |
|--------|---------|
| `docs/freeze/MRD_CURRENT_STATE.md` §ÉTAT ALEMBIC | `railway_alembic_head : 067_fix_market_coverage_trigger`, `migrations_pending_railway: AUCUNE` |
| `docs/freeze/CONTEXT_ANCHOR.md` bloc GIT | Alignement **067** prod après apply M15 |

**Divergence documentaire interne :** la section **PROBE RAILWAY — 2026-04-03** dans `MRD_CURRENT_STATE.md` indique encore `probe_alembic_head : 058_...` et tables P8/P9 « absentes / pending migration » — **contradictoire** avec la section « ÉTAT ALEMBIC » du même fichier (067 appliqué). **Le réel Railway au moment des probes du 03/04 peut avoir divergé ; la doc MRD doit être réconciliée par AO** (une seule ligne de vérité par date).

---

## 4. Routes supposées vs routes réelles (app canon Railway)

| Entrée | Fichier | Rôle |
|--------|---------|------|
| **Canon déploiement** | `main.py` | `FastAPI` : auth, upload, health, cases, documents, analysis, **extractions**, **regulatory_profile (M13)**, committee, scoring, criteria + routers optionnels (geo, vendors, mercuriale, price_check, pipeline, analysis_summary, **M14 evaluation**, vues VIVANT case_timeline, market_memory, learning_console) |
| **Dual-app / CI** | `src/api/main.py` | Même logique « routers optionnels » ; PR #297 a verrouillé l’exposition **M14** sur les deux apps |

**Preuve M14 monté sur `main.py` :** `app.include_router(_m14_evaluation_router)` (bloc try/import lignes ~216–224, boucle L257–270).

**Preuve extractions :** `from src.api.routes.extractions import router as extraction_router` + `app.include_router(extraction_router)`.

**501 documentés :** `main.py` `OPENAPI_DESCRIPTION` — certaines routes peuvent répondre **501** (comportement voulu, pas bug).

---

## 5. Workers / queues

| Composant | Preuve |
|-----------|--------|
| ARQ | `src/workers/arq_config.py` — `WorkerSettings.functions = [index_event, detect_patterns, generate_candidate_rules]` |
| Prérequis | `REDIS_URL` — si absent, `redis_settings` peut être `None` (worker non fonctionnel) |

**Pas de worker « extraction document »** dans ARQ : l’extraction est **API** `POST /api/extractions/documents/{id}/extract` (JWT), pas une task ARQ nommée `process_document`.

---

## 6. Variables d’environnement critiques (non secrets — noms)

| Variable | Usage |
|----------|--------|
| `DATABASE_URL` / `RAILWAY_DATABASE_URL` | Postgres |
| `REDIS_URL` | Rate limit + ARQ |
| `DMS_JWT` / `DMS_API_JWT` | Scripts trigger extraction `--apply` |
| `ANNOTATION_USE_PASS_ORCHESTRATOR` | Backend annotation — orchestrateur M12 Ph.3 |
| `LABEL_STUDIO_SSL_VERIFY` | TLS client scripts LS (`0` = dernier recours) |

Secrets : **jamais** dans le dépôt — `.env.railway.local` gitignored (`docs/ops/RAILWAY_LOCAL_ENV.md`).

---

## 7. Synthèse vérité

| Couche | Local (poste mandat) | Dépôt git | Railway (doc + scripts) |
|--------|----------------------|-----------|-------------------------|
| Head Alembic | **Non lu** via `current` (DB KO) | **067** | **067** (MRD / anchor) |
| API | N/A sans run | `main.py` riche | Aligné code mergé |
| Dette | Auth PG locale | — | Utiliser probes Railway |

**Règle mandat :** si la doc et le réel divergent, **le réel gagne** — ici : **MRD probe 2026-04-03 est obsolète** vs sections ultérieures du même MRD sur 067.
