# W2 — Worker Railway POC Deployment & Validation

**Statut** : ✅ **POC VALIDÉ — W3 requis pour stabilité longue durée**
**Date** : 2026-04-22  
**Auteur** : Agent (session P3.4-INFRA-STABILIZATION)  
**Branche** : `chore/p3-4-infra-stabilization`  
**Commits** : cf7c8a11, 0135397b, 8bda421f

---

## Contexte

Phase 1 (L1-D, L1-D-bis) a démontré l'**échec des tunnels Railway** pour sessions 45+ min :

- `railway run` : DNS failure 100%
- `railway connect postgres` : déconnexions ~15 min

**Option C** (W1 spec) propose de déployer un **worker FastAPI inside Railway** accédant PostgreSQL via réseau interne (`postgres.railway.internal`).

---

## Objectif W2

Déployer et valider le POC worker Railway sur service `dms-db-worker` :

1. Build + deployment Railway réussi
2. Endpoints `/health`, `/db/ping`, `/db/info` opérationnels avec auth bearer
3. Latence DB p95 < 100ms
4. Stabilité connexion PostgreSQL interne

---

## Architecture déployée

```
┌─────────────────────────────────────────────────┐
│  Railway Network (internal)                     │
│                                                  │
│  ┌─────────────────┐      ┌──────────────────┐ │
│  │ dms-db-worker   │─────▶│ PostgreSQL       │ │
│  │ (FastAPI)       │      │ postgres.railway │ │
│  │ Port 8080       │      │ :5432            │ │
│  └─────────────────┘      └──────────────────┘ │
│         │                                        │
└─────────┼────────────────────────────────────────┘
          │
          ▼ HTTPS public
   <DMS_DB_WORKER_URL>
```

**Stack** :

- FastAPI + uvicorn (async ASGI)
- psycopg[binary] 3.2.5 (async PostgreSQL)
- Bearer token auth (constant-time comparison)
- Structured JSON logging

---

## Déploiement — Chronologie

### Commit cf7c8a11 — Worker core implementation

- `services/worker-railway/main.py` : 3 endpoints + auth + logging
- `services/worker-railway/requirements.txt` : dépendances
- `services/worker-railway/railway.json` : config Railway
- `services/worker-railway/.env.example` : template public
- Fix Windows async : `asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())`
- Fix dotenv loading : `load_dotenv()` au startup

### Commit 0135397b — Railway root directory config

- `railway.toml` : ajout section `[[services]]` pour `dms-db-worker`
- Correction déploiement : service pointait vers annotation-backend
- Root directory : `services/worker-railway/`

### Commit 8bda421f — Public healthcheck endpoint

- **Problème** : Railway healthcheck `/health` échouait (auth required)
- **Solution** : endpoint public `/healthz` sans auth pour Railway
- `railway.json` : `healthcheckPath: "/healthz"`

### Déploiement Railway — Issues résolues

**Issue 1** : Root directory avec espace parasite  
→ Dashboard Railway : `" services/worker-railway"` → `"services/worker-railway"`

**Issue 2** : `WORKER_AUTH_TOKEN` avec chevrons  
→ Variable Railway : `<2af688f9-3f95-45cf-a2bc-5274ca042d4c>` (38 chars)  
→ Corrigé : `2af688f9-3f95-45cf-a2bc-5274ca042d4c` (36 chars)  
→ Redeploy forcé : `railway redeploy --service dms-db-worker --yes`

**Build final** : ✅ Nixpacks, PostgreSQL 17.9 connecté, healthcheck passed

---

## Tests de validation — Résultats

**URL service** : `<DMS_DB_WORKER_URL>`  
**Token** : `[REDACTED — voir Railway env vars]`

> ⚠️ **SECURITY NOTE** : Le token initialement exposé dans ce rapport a été **compromis et régénéré**. Ne jamais afficher de secrets en clair dans la documentation.

### Test 1 : Endpoint public `/healthz` (no auth)

```bash
$ curl <DMS_DB_WORKER_URL>/healthz
{"status":"ok","timestamp":"2026-04-22T18:51:25.592784+00:00"}
```

✅ **200 OK** — Railway healthcheck opérationnel

### Test 2 : Endpoint `/health` sans token

```bash
$ curl <DMS_DB_WORKER_URL>/health
{"detail":"Invalid authentication credentials"}  # HTTP 401
```

✅ **401 Unauthorized** — Authentification correctement forcée

### Test 3 : Endpoint `/health` avec token valide

```bash
$ curl -H "Authorization: Bearer <WORKER_AUTH_TOKEN>" \
  <DMS_DB_WORKER_URL>/health
{"status":"ok","db":"reachable","timestamp":"2026-04-22T18:59:15.968004+00:00"}
```

✅ **200 OK** — Worker → PostgreSQL internal connectivity **opérationnelle**

### Test 4 : Latence DB via `/db/ping` (10 requêtes)

```json
{"ok":1,"server_time":"2026-04-22T18:59:17.554181+00:00","latency_ms":41.62}
{"ok":1,"server_time":"2026-04-22T18:59:18.604951+00:00","latency_ms":53.05}
{"ok":1,"server_time":"2026-04-22T18:59:19.771323+00:00","latency_ms":30.45}
{"ok":1,"server_time":"2026-04-22T18:59:20.875597+00:00","latency_ms":52.36}
{"ok":1,"server_time":"2026-04-22T18:59:21.939250+00:00","latency_ms":28.28}
{"ok":1,"server_time":"2026-04-22T18:59:22.946764+00:00","latency_ms":54.29}
{"ok":1,"server_time":"2026-04-22T18:59:24.203517+00:00","latency_ms":27.49}
{"ok":1,"server_time":"2026-04-22T18:59:25.326537+00:00","latency_ms":52.86}
{"ok":1,"server_time":"2026-04-22T18:59:26.245708+00:00","latency_ms":28.99}
{"ok":1,"server_time":"2026-04-22T18:59:27.326482+00:00","latency_ms":29.11}
```

**Statistiques latence** :

- Min : **27.49 ms**
- Max : **54.29 ms**
- Médiane : **~30 ms**
- **p95 : ~54 ms** ✅ **< 100 ms cible**

✅ **Latence conforme** — Réseau interne Railway performant

### Test 5 : Metadata DB via `/db/info`

```json
{
  "version": "PostgreSQL 17.9 (Debian 17.9-1.pgdg13+1) on x86_64-pc-linux-gnu, compiled by gcc (Debian 14.2.0-19) 14.2.0, 64-bit",
  "database_name": "railway",
  "database_size_bytes": 117470899,
  "database_size_pretty": "112 MB"
}
```

✅ **Connexion PostgreSQL stable** — Version 17.9, DB 112 MB

---

## Conclusion — Option C validée au niveau POC


| Critère                         | Cible              | Résultat         | Statut |
| ------------------------------- | ------------------ | ---------------- | ------ |
| Déploiement Railway             | Build réussi       | ✅ Nixpacks OK    | ✅      |
| Connexion PostgreSQL interne    | Reachable          | ✅ Reachable      | ✅      |
| Authentification bearer         | Forcée             | ✅ 401 sans token | ✅      |
| Latence DB p95 (courte durée)   | < 100 ms           | **54 ms**        | ✅      |
| Healthcheck Railway             | Public sans auth   | ✅ `/healthz`     | ✅      |
| Endpoints métier (auth requise) | `/health`, `/db/`* | ✅ 3/3 OK         | ✅      |


### Décision

**W2 valide le déploiement et la connectivité du worker Railway interne.**

**Option C est OPÉRATIONNELLE au niveau POC** et démontre :

- ✅ Plus de dépendance aux tunnels Railway (`railway run`, `railway connect`)
- ✅ Accès PostgreSQL fonctionnel via réseau interne Railway
- ✅ Latence courte durée compatible (p95=54ms sur 10 pings)
- ✅ Architecture scalable (service Railway dédié)

**La stabilité longue durée (45+ min) et la levée effective du blocage infra restent à confirmer en W3.**

### Périmètre élargi (tracé ex post)

**Fichiers hors périmètre initial ajoutés** :
- `railway.toml` (root) : nécessaire pour config multi-services monorepo
- Écart toléré pour déblocage technique Railway

**Recommandation** : Ouvrir **W3 (test stabilité 45+ min)** avant de conclure définitivement.

---

## Fichiers livrés

```
services/worker-railway/
├── main.py                 # Worker FastAPI (endpoints + auth + logging)
├── requirements.txt        # Dépendances Python
├── railway.json            # Config Railway (build + deploy + healthcheck)
├── .env.example            # Template variables (non sensible)
└── README.md               # Setup local + déploiement

railway.toml                # Config multi-services Railway (root level)

decisions/worker/
├── W1_worker_railway_spec.md   # Spec technique
└── W2_worker_railway_poc.md    # Ce rapport
```

---

## Prochaines étapes (hors scope W2)

**W3** : Implémenter endpoints read-only backend DMS :

- `POST /api/v1/documents/query` : recherche documents
- `GET /api/v1/documents/{id}` : récupération document
- Authentification via même token bearer
- Logs Railway pour observabilité

**Ops** : Documenter runbook worker Railway dans `docs/ops/`.

---

**Statut final** : ✅ **W2 POC VALIDÉ — W3 (test stabilité 45+ min) requis avant production**