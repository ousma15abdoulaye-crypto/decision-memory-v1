# DMS Worker Railway — Fragment W1 — Spec technique

**Référence** : DMS-W1-WORKER-RAILWAY-SPEC-V1
**Date** : 2026-04-22
**Mandat source** : DMS-MANDAT-W1-WORKER-SPEC-V1
**Chantier** : P3.4-INFRA-WORKER-DEPLOYMENT
**Chantier parent** : P3.4-INFRA-STABILIZATION
**Autorité** : ADR-P34-INFRA-OPTION-C-WORKER-RAILWAY-V1 (SIGNÉ / APPROVED)

---

## 1. Contexte et rappel ADR Option C

Phase 1 I-DEBT-2 a révélé qu'aucune voie L2 (tunnel Railway CLI externe) ne tient 45 min depuis environnement agent. **Option C retenue** : déployer un compute Python dans le réseau Railway (même projet PostgreSQL) pour accéder à `DATABASE_URL` nativement via réseau interne, objectif architectural à tester en W2-W3.

**Références opposables** :
- ADR : `decisions/adr/ADR_P34_INFRA_OPTION_C_WORKER_RAILWAY_V1.md`
- Synthèse Phase 1 : `decisions/phase1/L1_E_phase1_synthesis.md`

---

## 2. Stack technique retenue

### Langage et framework

- **Python 3.11+** (aligné `services/annotation-backend` pour cohérence D-INFRA-5)
- **FastAPI** (framework web léger, validation Pydantic native, async ASGI)
- **uvicorn** (serveur ASGI production-ready)

### Driver PostgreSQL

**Choix** : **`psycopg[binary]`** (psycopg version 3.x)

**Justification** :
- Version moderne (psycopg 3.x, sortie 2021+)
- API async native (`await conn.execute(...)`)
- Aligné dependencies récentes DMS
- Distribution binary wheel disponible (pas de compilation C locale)

**Alternative écartée** : `psycopg2-binary` (version 2.x, API sync uniquement, fin de vie annoncée)

### ORM

**Aucun ORM** (SQLAlchemy, Django ORM, etc.)

**Justification** : Worker minimaliste, 3 endpoints read-only simples. SQL brut via `psycopg.execute()` suffit. Pas de modèles métier, pas de migrations, pas de relations complexes. Principe YAGNI (You Aren't Gonna Need It).

---

## 3. Endpoints HTTP exposés

Le worker expose **3 endpoints read-only** avec authentification bearer token obligatoire.

### 3.1 GET /health

**Objet** : Health check worker + DB reachability.

**Contrat** :
- **Auth** : Bearer token requis (`Authorization: Bearer <WORKER_AUTH_TOKEN>`)
- **Réponse 200 OK** :
  ```json
  {
    "status": "ok",
    "db": "reachable",
    "timestamp": "2026-04-22T12:34:56Z"
  }
  ```
- **Réponse 503 Service Unavailable** (DB unreachable) :
  ```json
  {
    "status": "degraded",
    "db": "unreachable",
    "error": "connection refused",
    "timestamp": "2026-04-22T12:34:56Z"
  }
  ```
- **Réponse 401 Unauthorized** (token absent ou invalide) :
  ```json
  {
    "detail": "Invalid authentication credentials"
  }
  ```

**Logique** : Tente `SELECT 1` sur DB. Si succès → `db: "reachable"`. Si échec → `db: "unreachable"` + message erreur.

---

### 3.2 GET /db/ping

**Objet** : Exécuter `SELECT 1` + timestamp serveur DB pour validation connectivité + latence.

**Contrat** :
- **Auth** : Bearer token requis
- **Réponse 200 OK** :
  ```json
  {
    "ok": 1,
    "server_time": "2026-04-22T12:34:56.789123+00:00",
    "latency_ms": 15.3
  }
  ```
- **Réponse 500 Internal Server Error** (échec DB) :
  ```json
  {
    "detail": "Database query failed: <error message>"
  }
  ```
- **Réponse 401 Unauthorized** (token invalide)

**Logique** :
- Exécuter `SELECT 1 AS ok, now() AS server_time;`
- Mesurer latence requête (time.perf_counter avant/après)
- Retourner `ok`, `server_time`, `latency_ms`

---

### 3.3 GET /db/info

**Objet** : Informations PostgreSQL (version, taille DB) pour diagnostic.

**Contrat** :
- **Auth** : Bearer token requis
- **Réponse 200 OK** :
  ```json
  {
    "version": "PostgreSQL 17.9 (Debian 17.9-1.pgdg13+1) on x86_64-pc-linux-gnu, compiled by gcc (Debian 14.2.0-19) 14.2.0, 64-bit",
    "database_name": "railway",
    "database_size_bytes": 117440512,
    "database_size_pretty": "112 MB"
  }
  ```
- **Réponse 500 Internal Server Error** (échec DB)
- **Réponse 401 Unauthorized** (token invalide)

**Logique** :
- Exécuter `SELECT version();`
- Exécuter `SELECT current_database(), pg_database_size(current_database());`
- Formater size via `pg_size_pretty()` ou calcul Python

---

## 4. Variables d'environnement requises

| Variable | Source | Obligatoire | Description |
|---|---|---|---|
| **DATABASE_URL** | Railway auto (service link) | ✅ OUI | Connection string PostgreSQL Railway (format: `postgresql://user:pass@host:port/dbname`) |
| **WORKER_AUTH_TOKEN** | Manuel Railway env var | ✅ OUI | Bearer token pour authentification endpoints (généré via `openssl rand -hex 32` ou équivalent) |
| **PORT** | Railway auto | ✅ OUI | Port HTTP worker (Railway injecte automatiquement, généralement 8080 ou dynamique) |
| **LOG_LEVEL** | Manuel (optionnel) | ❌ NON | Niveau logs (`INFO`, `DEBUG`, `WARNING`, default `INFO`) |

**Notes** :
- `DATABASE_URL` injecté automatiquement par Railway si service link configuré entre worker et PostgreSQL
- `WORKER_AUTH_TOKEN` doit être défini manuellement via Railway dashboard ou CLI avant déploiement W2
- `PORT` géré par Railway, worker bind sur `0.0.0.0:${PORT}`

---

## 5. Sécurité et posture réseau

### Authentification

- **Bearer token obligatoire** sur tous les 3 endpoints
- Token vérifié via header `Authorization: Bearer <token>`
- Comparaison constante-time pour éviter timing attacks :
  ```python
  import hmac
  hmac.compare_digest(provided_token, WORKER_AUTH_TOKEN)
  ```

### Endpoints read-only

- **Aucun endpoint d'écriture DB** (pas de POST, PUT, DELETE modifiant données)
- `SELECT` uniquement sur les 3 endpoints
- Pas de paramètres SQL injectables (requêtes statiques)

### Logs structurés

- **Format JSON** pour stdout (compatible Railway logs aggregation)
- **Champs attendus** : `timestamp`, `level`, `message`, `endpoint`, `status_code`, `latency_ms`
- **Pas d'exposition secrets** : `DATABASE_URL` masquée dans logs (afficher host uniquement, pas user/pass)
- Exemple log :
  ```json
  {"timestamp": "2026-04-22T12:34:56Z", "level": "INFO", "message": "GET /health", "status": 200, "latency_ms": 12.3}
  ```

### Posture réseau Railway

- Worker déployé dans **réseau interne Railway** (même projet que PostgreSQL)
- Accès DB via `DATABASE_URL` interne (pas de proxy `maglev.proxy.rlwy.net` externe)
- Worker exposé publiquement via Railway URL (`https://<service-name>.railway.app`)
- **Pas de whitelist IP** côté DB (connexion interne Railway trusted)
- **TLS géré par Railway** (certificat auto-provisionné sur `*.railway.app`)

---

## 6. Fichiers à créer (arborescence prévue W2)

**Répertoire** : `services/worker-railway/`

```
services/
└── worker-railway/
    ├── main.py              # Application FastAPI (endpoints, auth, DB logic)
    ├── requirements.txt     # Dependencies Python (fastapi, uvicorn, psycopg[binary])
    ├── railway.json         # Config déploiement Railway (build command, start command, healthcheck)
    ├── README.md            # Documentation worker (setup local, déploiement, endpoints)
    └── .gitignore           # Ignore __pycache__, .env local
```

### Contenu attendu fichiers

**`requirements.txt`** (à créer W2) :
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
psycopg[binary]==3.2.5
python-dotenv==1.0.0
```

**`railway.json`** (à créer W2) :
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn main:app --host 0.0.0.0 --port ${PORT}",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30
  }
}
```

**`main.py`** (structure attendue W2, pas de code complet ici) :
- Import FastAPI, uvicorn, psycopg, os
- Fonction `verify_token()` (bearer auth dependency)
- Endpoint `/health` avec try/except DB
- Endpoint `/db/ping` avec mesure latence
- Endpoint `/db/info` avec requêtes version + size
- Logs structurés JSON via `logging.basicConfig()`
- Startup event pour test connexion DB initiale

**`README.md`** (à créer W2) :
- Objectif worker
- Setup local (venv, requirements, `.env` avec `DATABASE_URL` + `WORKER_AUTH_TOKEN`)
- Déploiement Railway (CLI `railway up`, env vars à configurer)
- Endpoints disponibles + exemples curl
- Troubleshooting (logs Railway, DB unreachable)

---

## 7. Critères de succès W2 (POC)

W2 (fragment suivant) validera la spec W1 via déploiement concret. **Critères minimaux** :

| # | Critère | Validation |
|---|---|---|
| 1 | Worker déployé Railway service actif | Dashboard Railway montre service UP |
| 2 | `/health` répond 200 avec `db: "reachable"` | `curl -H "Authorization: Bearer <token>" https://<worker>.railway.app/health` → 200 OK |
| 3 | `/db/ping` retourne `SELECT 1` + timestamp | Réponse JSON avec `ok: 1`, `server_time`, `latency_ms` |
| 4 | Auth fonctionne : 401 sans token | `curl https://<worker>.railway.app/health` (sans header) → 401 Unauthorized |
| 5 | Logs Railway visibles | Railway dashboard logs affiche requêtes JSON structurées |
| 6 | `DATABASE_URL` interne connectée | Pas de `getaddrinfo failed`, connexion stable |

**Validation observée** (pas de test automatisé W2, observation directe) :
- Agent exécute 10 requêtes `/db/ping` espacées 5s
- Taux succès = 10/10
- Latence p95 < 100ms (cible interne Railway)
- Aucune erreur DB dans logs

**Échec W2 déclenche escalade** : Si worker Railway ne peut pas se connecter à DB ou si latence dégradée (>500ms p95 interne), cela signifie que le problème n'est pas le tunnel externe mais la DB Railway elle-même → arbitrage CTO principal immédiat, Option C potentiellement invalidée.

---

**Fin W1. Spec opposable complète. W2 implémentera.**
