# ADR-V420-004 — Pool de connexions PostgreSQL

**Statut** : ACCEPTÉ  
**Date** : 2026-04-04  
**Auteur** : Abdoulaye Ousmane — CTO  
**Référence** : DMS V4.2.0 ADDENDUM §VIII — Plan pool connexions

---

## Contexte

Le code actuel (`src/db/core.py`) ouvre une connexion `psycopg` individuelle par requête
et la ferme à la fin. Cette approche est fonctionnelle pour des charges faibles mais ne passe
pas à l'échelle du modèle workspace-first (WebSocket persistant, ARQ workers, LangGraph saver).

## Problème

- Chaque requête FastAPI : `psycopg.connect()` + RLS `SET LOCAL` + `conn.close()`
- ARQ workers : 3 workers × connexion individuelle
- LangGraph checkpoint : 3 connexions PostgresSaver
- Langfuse self-hosted : 3 connexions

Sans pool, chaque pic de charge ouvre N connexions simultanées au lieu de les réutiliser.
Railway Hobby plan = 25 connexions max → risque exhaustion dès le premier spike.

## Décision

Introduire `psycopg_pool.ConnectionPool` (synchrone) pour les routes FastAPI existantes,
et `asyncpg.Pool` pour les nouvelles routes workspace (asyncpg requis par LangGraph et AsyncPostgresSaver).

### Allocation pool cible (Railway Pro — 100 connexions)

| Composant | Pool | Taille |
|---|---|---|
| FastAPI existant (psycopg sync) | `psycopg_pool.ConnectionPool` | 10 |
| FastAPI workspace (asyncpg) | `asyncpg.Pool` | 5 |
| ARQ workers | Connexions individuelles | 3 |
| LangGraph AsyncPostgresSaver | asyncpg interne | 3 |
| Langfuse | Interne | 3 |
| Marge | — | 76 |
| **Total alloué** | | **24 / 100** |

### Pattern psycopg_pool (routes existantes)

```python
# src/db/pool.py — nouveau module
import os
from psycopg_pool import ConnectionPool

_pool: ConnectionPool | None = None

def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=os.environ["DATABASE_URL"],
            min_size=2,
            max_size=10,
            kwargs={"autocommit": False},
        )
    return _pool

def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
```

```python
# Utilisation dans src/db/core.py — get_connection() adapté
from src.db.pool import get_pool

@contextmanager
def get_connection() -> Iterator[_ConnectionWrapper]:
    pool = get_pool()
    with pool.connection() as conn:
        wrapper = _ConnectionWrapper(conn)
        # SET LOCAL RLS...
        yield wrapper
```

### Pattern asyncpg (nouvelles routes workspace)

```python
# src/db/async_pool.py — nouveau module
import asyncpg
import os

_async_pool: asyncpg.Pool | None = None

async def get_async_pool() -> asyncpg.Pool:
    global _async_pool
    if _async_pool is None:
        _async_pool = await asyncpg.create_pool(
            dsn=os.environ["DATABASE_URL"],
            min_size=2,
            max_size=8,
        )
    return _async_pool

async def close_async_pool() -> None:
    global _async_pool
    if _async_pool is not None:
        await _async_pool.close()
        _async_pool = None
```

## Lifespan FastAPI

```python
# main.py — lifespan manager
from contextlib import asynccontextmanager
from src.db.pool import close_pool
from src.db.async_pool import close_async_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    close_pool()
    await close_async_pool()

app = FastAPI(lifespan=lifespan)
```

## Dépendances ajoutées

```
psycopg-pool>=3.2.0   # pool sync psycopg
asyncpg>=0.29.0       # pool async pour nouvelles routes
```

Ces dépendances sont ajoutées dans `requirements.txt` lors de Phase 0.

## Contraintes

- SET LOCAL tenant_id : doit rester dans chaque transaction (pas de SET global)
- Pool psycopg : `autocommit=False` pour garantir les transactions
- Pool asyncpg : chaque connexion acquise exécute SET LOCAL avant toute query

## Conséquences

- Semaine 0 : créer `src/db/pool.py` + `src/db/async_pool.py`
- Semaine 0 : adapter `src/db/core.py` `get_connection()` pour utiliser le pool
- Semaine 0 : adapter `main.py` lifespan
- Monitoring : `SELECT count(*) FROM pg_stat_activity` dans gate S3 et pilote
- Alert : pool > 80% = STOP SIGNAL S3

---

*RÈGLE-13 non applicable (psycopg_pool et asyncpg ne sont pas des LLM frameworks).*
*ADR requis par le plan V4.2.0 §VIII pour tout changement infrastructure connexion.*
