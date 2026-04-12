# ADR — Périmètre UI M16 (roadmap post-stabilisation)

## Statut

**Informationnel — 2026-04-11** (pas de gel implémentation immédiate).

## Contexte

Après stabilisation du **scellement / PV** (PATCH orchestré) et de la **matrice comparative canonique** (`GET …/comparative-matrix` avec `source` M14/M16), le produit peut exposer progressivement le reste du domaine M16 déjà présent côté API :

- Threads de délibération et messages
- Lignes prix / valeurs par bundle
- Coquille HTML comparative (`comparative-shell`)
- Clarifications / notes validées

## Décision

- **Phase UI 1** : matrice + badge source + sync M14→M16 (livré avec le mandat dette FE-BE).
- **Phase UI 2+** : ateliers produit pour prioriser écrans ou panneaux (pas de refonte monolithique).
- Chaque vague UI M16 = mandat CTO + routes déjà sous `/api/workspaces/{id}/m16/...`.

## Références

- `src/api/routers/m16_comparative.py`
- `docs/adr/ADR-V53-COGNITIVE-MATRIX-SCOPE.md` (contexte matrice)
