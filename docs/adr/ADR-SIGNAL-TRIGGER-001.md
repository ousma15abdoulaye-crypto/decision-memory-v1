# ADR-SIGNAL-TRIGGER-001 — Strategie de declenchement automatique du Signal Engine

**Date :** 2026-04-03
**Statut :** ACCEPTE
**Auteur :** CTO DMS
**Contexte :** M15 Phase 3.3 — Activation signal engine

---

## Contexte

Le signal engine (`src/couche_a/market/signal_engine.py` + `FormulaV11`) calcule
les signaux marche pour chaque paire `(item_id, zone_id)` a partir de :
- `public.market_surveys` (poids 0.35)
- `public.mercurials` (poids 0.35)
- `couche_a.mercuriale_raw_queue` (poids 0.15)
- `public.decision_history` (poids 0.15)

Actuellement (post-probe 2026-04-03) : 1108 signaux existants, 90.43% strong+moderate.
Le recalcul n'est pas declenche automatiquement apres ingestion d'un nouveau mercuriel.

---

## Probleme

Deux options de declenchement post-ingestion :

**Option A — Sync (dans la transaction d'ingestion)**
- Avantage : donnees immediatement coherentes
- Inconvenient : alourdit la transaction principale ; si le moteur signal echoue, rollback de l'ingestion

**Option B — Async via ARQ background job**
- Avantage : ingestion rapide, decouplage de responsabilites, retry natif ARQ
- Inconvenient : fenetre de latence entre ingestion et signal recalcule (~30s a 5min)

---

## Decision

**Option B adoptee : ARQ background job.**

Justification :
1. L'ARQ worker est deja deploye (PR #300 H2, `src/workers/tasks.py`)
2. FormulaV11 peut prendre 0.5-5s par item selon la quantite de donnees
3. Le signaux marche ne necessitent pas de coherence immediate (usage: rapport, alerte)
4. Les alertes IPC sont batch-calculees, pas temps-reel
5. Failure isolation : echec recalcul = signal stale, pas rollback ingestion

---

## Implementation

### Declencheur

Dans le service d'ingestion mercuriale (`src/couche_a/market/` ou route FastAPI `/api/market/surveys`) :

```python
# Apres INSERT confirme, fire-and-forget ARQ
from src.workers.tasks import recompute_signal_for_item
await arq_pool.enqueue_job(
    "recompute_signal_for_item",
    item_id=item_id,
    zone_id=zone_id,
)
```

### Task ARQ

```python
# src/workers/tasks.py
async def recompute_signal_for_item(ctx: dict, item_id: str, zone_id: str) -> dict:
    engine = SignalEngine(db_url=ctx["db_url"], allow_railway=True)
    result = engine.compute(item_id=item_id, zone_id=zone_id)
    return {"item_id": item_id, "zone_id": zone_id, "signal_quality": result["signal_quality"]}
```

### Prerequis

1. ARQ + Redis deploye sur Railway (ADR-H2-ARQ-001 — `REDIS_URL` requis)
2. Si Redis absent : batch cron toutes les heures via Railway Cron Service

### Alternative sans Redis (fallback)

Si `REDIS_URL` n'est pas definie, le declenchement se fait via endpoint `/api/signals/recompute`
appele depuis un Railway Cron Service (`0 * * * *`).

---

## Risques

| Risque | Probabilite | Mitigation |
|--------|-------------|------------|
| Redis indisponible | Moyen | Fallback cron, signal stale documenté |
| Job en attente longue | Faible | Timeout ARQ 300s, dead letter queue |
| Signal incoh. pendant fenetre | Attendu | Cache signaux v2 = derniere valeur valide |

---

## Statut Implementation M15

- [ ] ARQ task `recompute_signal_for_item` a implementer dans `src/workers/tasks.py`
- [ ] Wiring dans service ingestion
- [ ] REDIS_URL Railway Dashboard : a configurer (mandat CTO)
- [x] ADR signe — decision documentee

---

## References

- `docs/adr/ADR-H2-ARQ-001.md` — ARQ deployment decision
- `src/couche_a/market/signal_engine.py` — FormulaV11
- `src/workers/arq_config.py` — Worker settings
- Probe 2026-04-03 : `docs/PROBE_2026_04_03.md`
