# Mercuriale → dict — couverture & mapping (P1-DATA-01)

## Objectif

Atteindre le seuil documentaire **70 %** de couverture `mercurials_item_map` (vs métriques M15 / signal engine).

## Données de travail

- Export items non mappés : `docs/data/unmapped_items.csv` (réf. MRD / CONTEXT).
- Scripts : `scripts/probe_mercurials_coverage.py` (mesure courante).

## Processus suggéré

1. Lancer la sonde sur l’environnement cible (DB prod read-only ou copie) ; noter le pourcentage.
2. Prioriser les items par volume / impact métier ; proposer mappings dans le référentiel dict (process humain + validation).
3. Réinjecter via les outils ETL / mandats vendors déjà documentés (`scripts/README_VENDOR_IMPORT.md`).
4. Re-mesurer jusqu’à franchissement du seuil ou décision produit d’accepter l’écart.

## Références

- Dette : [`docs/audit/DMS_TECHNICAL_DEBT_P0_P3.md`](../audit/DMS_TECHNICAL_DEBT_P0_P3.md) — P1-DATA-01
