# P3 — Livrable 8 : Stratégie offline et résilience

## 8.1 État actuel

- **Constitution** : [`src/core/config.py`](../../../src/core/config.py) — `INVARIANTS["online_only"] = True` — le produit cible **PostgreSQL online**.
- **Mode extraction offline** : [`src/couche_a/extraction_models.py`](../../../src/couche_a/extraction_models.py) définit un `Tier.T4_OFFLINE` — signal de conception, **NON** une garantie de sync offline complète pour l’UI.

## 8.2 File d’attente / reconciliation

- **Workers ARQ** : [`src/workers/`](../../../src/workers/) — jobs asynchrones ; pas une « queue offline client ».
- **Reconciliation mutations client** type PWA : **NON IMPLÉMENTÉ** dans ce dépôt backend.

## 8.3 Mesures terrain (Mopti → Railway)

**NON MESURÉ** dans ce livrable — aucun fichier de benchmark réseau versionné ici. À produire par campagne ops dédiée si requis.

## 8.4 Cohérence avec la state machine cognitive

Les transitions **E0–E6** sont **serveur-authoritatives** via `process_workspaces.status` — pas de modèle de fusion de conflits offline décrit dans le code.
