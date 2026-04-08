# Contrat d’entrée M14 — liste `offers[]` (P1-M14-01)

## Problème

Le moteur M14 (`EvaluationEngine.evaluate`) **consomme** une liste d’offres structurées en entrée ; il **ne reconstruit pas** automatiquement les bundles workspace → offres si l’appelant ne les fournit pas.

## Règle produit / intégration

1. Tout appelant de `POST /api/m14/evaluate` (ou équivalent service) doit documenter l’origine des `offers[]` (extraction workspace, documents normalisés, etc.).
2. Les parcours « workspace-first » doivent préciser **quel orchestrateur** assemble les dicts offres avant l’appel M14 (runbook pilote, script, ou UI).
3. En l’absence d’offres complètes, le résultat M14 peut être **incomplet** sans erreur bloquante — à traiter comme risque fonctionnel, pas seulement technique.

## Références

- [`src/procurement/m14_engine.py`](../../src/procurement/m14_engine.py)
- Dette : [`docs/audit/DMS_TECHNICAL_DEBT_P0_P3.md`](../audit/DMS_TECHNICAL_DEBT_P0_P3.md) — P1-M14-01
