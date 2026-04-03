# ADR-H2-ARQ-001 — Background Job Queue: ARQ + Redis

**Status:** Accepted  
**Date:** 2026-04-03  
**Horizon:** DMS VIVANT V2 — H2 (Event Federation)  
**Author:** CTO DMS

---

## Contexte

Le DMS VIVANT V2 (H2) introduit un index d'événements fédéré (`dms_event_index`) alimenté
par 11 bridge triggers sur des tables sources. Des tâches d'arrière-plan sont nécessaires
pour :

1. Indexer des événements non couverts par les triggers (sources externes, batch).
2. Exécuter la détection de patterns (`PatternDetector.detect_all()`) périodiquement.
3. Générer des règles candidates (`CandidateRuleGenerator`) après chaque cycle de détection.

Un système de job queue asynchrone est requis, compatible avec le stack Redis déjà déployé
sur Railway (utilisé pour le rate-limiting via `slowapi`).

## Décision

**ARQ** (`arq==0.26.1`) est retenu comme job queue.

### Justification

| Critère | ARQ | Celery | RQ |
|---------|-----|--------|----|
| Runtime Python natif async (asyncio) | ✅ | ❌ (sync) | ❌ |
| Backend Redis uniquement | ✅ | Redis/AMQP | ✅ |
| Dépendances légères | ✅ (1 dep) | ❌ (lourd) | ✅ |
| Compatible Railway tier gratuit | ✅ | ❌ (RAM) | ✅ |
| Serialization native Python | ✅ | JSON/pickle | JSON |
| Maintenance 2024-2026 | ✅ | ✅ | Faible |

ARQ est minimaliste, entièrement async (compatible FastAPI), et s'appuie
sur le Redis déjà présent. Celery serait surdimensionné pour le volume DMS actuel.

### Configuration

- `REDIS_URL` : variable d'environnement Railway, partagée avec `slowapi`.
- `WorkerSettings.max_jobs = 10` : parallélisme suffisant pour le volume V2.
- `WorkerSettings.job_timeout = 300s` : couvre les tâches de détection lourdes.

## Conséquences

- `arq==0.26.1` ajouté à `requirements.txt`.
- `src/workers/arq_config.py` : `WorkerSettings` avec `RedisSettings.from_dsn(REDIS_URL)`.
- `src/workers/arq_tasks.py` : 3 tâches réelles (`index_event`, `detect_patterns`, `generate_candidate_rules`).
- En CI (sans Redis), les tâches sont testées via mocks — pas de Redis requis.
- Un déploiement Railway séparé du worker (`arq worker src.workers.arq_config.WorkerSettings`) peut être ajouté en Phase 2.

## Références

- ADR-016 (Redis rate limiting) — même instance Redis
- `src/workers/arq_config.py`, `src/workers/arq_tasks.py`
- RÈGLE-13 (toute dépendance nouvelle = ADR avant premier commit)
