# Déploiement DMS — Entrypoint canonique Railway

**Mis à jour :** 2026-04-03  
**Autorité :** CTO / ADR-DUAL-FASTAPI-ENTRYPOINTS.md

---

## Entrypoint déployé sur Railway

**L'entrypoint canonique Railway est `main.py` à la racine du dépôt.**

```
main.py (root)  →  app = FastAPI(lifespan=lifespan)
```

### Pourquoi `main.py` (root) et non `src/api/main.py`

| Entrypoint | Routers inclus | Statut |
|-----------|----------------|--------|
| `main.py` (root) | auth, upload, health, cases, documents, analysis, extraction, regulatory_profile, committee, scoring, criteria, geo*, vendors*, mercuriale*, price_check*, pipeline_a*, analysis_summary*, m14_evaluation*, **H4 views (case_timeline, market_memory, learning_console)** | **CANONIQUE Railway** |
| `src/api/main.py` | Sous-ensemble (sans regulatory_profile, sans H4 views) | Secondaire — usage local/tests |

`src/api/main.py` existe pour des raisons historiques (strangler pattern, tests isolés).
Il ne sera **pas supprimé** sans ADR explicite, mais il n'est **jamais** le process déployé.

### Configuration Railway

```
Start Command : uvicorn main:app --host 0.0.0.0 --port $PORT
(ou via Procfile : web: uvicorn main:app --host 0.0.0.0 --port $PORT)
```

### Vérification

```bash
# Vérifier que /views/case/{case_id}/timeline est exposé (H4)
curl https://<railway-url>/views/case/CASE-001/timeline
# Vérifier que /api/m13/status est exposé
curl -H "Authorization: Bearer <token>" https://<railway-url>/api/m13/status
```

---

## Variables d'environnement Railway

| Variable | Obligatoire | Description |
|----------|-------------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL Railway |
| `SECRET_KEY` | ✅ | JWT signing key |
| `REDIS_URL` | ✅ | Redis (rate-limit + ARQ) |
| `MISTRAL_API_KEY` | ✅ | Mistral OCR + LLM |
| `LANGFUSE_PUBLIC_KEY` | Non | Langfuse observabilité (si enabled) |
| `LANGFUSE_SECRET_KEY` | Non | Langfuse observabilité |
| `BGE_MODEL_PATH` | Non | Path modèle BGE-M3 local (RAM 4GB requis) |
| `BGE_RERANKER_MODEL` | Non | Path BGE-reranker-v2-m3 |
| `DMS_ALLOW_RAILWAY_MIGRATE` | Non | Active migrations Railway (RÈGLE-ANCHOR-06) |

---

## Workers ARQ

Le worker ARQ (background tasks) est un **processus séparé**, pas intégré dans l'API :

```
Start Command (worker process) : arq src.workers.arq_config.WorkerSettings
Environment : REDIS_URL, DATABASE_URL
```

Sur Railway, créer un service "Worker" distinct avec la même image Docker mais
la commande ARQ worker.

---

## Référence ADR

- `docs/adr/ADR-DUAL-FASTAPI-ENTRYPOINTS.md` — justification de la coexistence des deux entrypoints
- `docs/adr/ADR-H2-ARQ-001.md` — justification ARQ worker séparé
