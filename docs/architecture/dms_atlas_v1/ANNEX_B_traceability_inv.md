# ANNEX B — Traçabilité INV / invariants → code

Extrait produit par recherche ciblée dans `src/` (2026-04-06). Les identifiants **INV-MQL\*** n’apparaissent **pas** dans le grep — **absence de traçage sous ce préfixe**.

| ID | Fichiers / notes |
|----|------------------|
| INV-4 (Constitution DB) | [`src/db/core.py`](../../src/db/core.py), [`pool.py`](../../src/db/pool.py), [`async_pool.py`](../../src/db/async_pool.py) |
| INV-C01 | Projection cognitive — [`src/cognitive/cognitive_state.py`](../../src/cognitive/cognitive_state.py) ; GAP_MATRIX |
| INV-C09 | [`src/cognitive/confidence_envelope.py`](../../src/cognitive/confidence_envelope.py) |
| INV-W06 | [`src/api/routers/workspaces.py`](../../src/api/routers/workspaces.py), [`market.py`](../../src/api/routers/market.py), [`committee_sessions.py`](../../src/api/routers/committee_sessions.py), [`evaluation_frame.py`](../../src/cognitive/evaluation_frame.py) |
| INV-W07 | [`src/api/ws/workspace_events.py`](../../src/api/ws/workspace_events.py) — écart possible vs event_index strict (GAP_MATRIX) |
| INV-W01, INV-W04 | [`src/api/routers/committee_sessions.py`](../../src/api/routers/committee_sessions.py) |
| INV-PROJ-01–03 | [`src/workers/arq_projector_couche_b.py`](../../src/workers/arq_projector_couche_b.py) |
| INV-P7, P8, P11, P16, API-11-01 | [`src/couche_a/pipeline/models.py`](../../src/couche_a/pipeline/models.py), [`router.py`](../../src/couche_a/pipeline/router.py), [`service.py`](../../src/couche_a/pipeline/service.py) |
| INV-AS* | [`src/couche_a/analysis_summary/engine/`](../../src/couche_a/analysis_summary/engine/) |
| INV-9 (scoring trace) | [`src/couche_a/scoring/engine.py`](../../src/couche_a/scoring/engine.py) |

Pour une liste exhaustive à jour, exécuter :

`rg "INV-[A-Z0-9]+" src/`

---

## Complétude clause mandat

- **INV-W01–W07** : partiellement listés — étendre avec résultat `rg` complet au besoin.
- **INV-MQL** : **aucun symbole** dans `src/` au moment de la rédaction.
