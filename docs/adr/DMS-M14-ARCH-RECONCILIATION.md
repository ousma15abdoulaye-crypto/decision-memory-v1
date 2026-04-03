# DMS-M14 — Réconciliation architecture ↔ dépôt

**Date :** 2026-04-02  
**Statut :** Informatif (alignement post-mandat M14 correction A + B)

## Objectif

Documenter l’alignement entre la cible d’architecture DMS (évaluation comparative hors verdict, persistance traçable, auth JWT) et l’implémentation dans ce dépôt après les livraisons M14 (routes, moteur, audit DB).

## Points alignés

| Sujet architecture | Implémentation dépôt |
|--------------------|----------------------|
| Deux points d’entrée FastAPI (`main:app`, `src.api.main:app`) | Router `evaluation` monté en option sur les deux ; CI `--fail-prefix /api/m14` sur les deux apps |
| Auth sur routes métier | `Depends(get_current_user)` sur `/api/m14/*` — voir `docs/audits/ROUTE_AUTH_INVENTORY.md` |
| Moteur déterministe sans LLM | `src/procurement/m14_engine.py` — `EvaluationEngine` |
| Interdictions RÈGLE-09 | Modèles Pydantic + tests kill list |
| Traçabilité scores / éliminations | Migration `059_m14_score_history_elimination_log` — tables `score_history`, `elimination_log` (RLS, append-only) ; `save_m14_audit` sur `M14EvaluationRepository` |
| Process linking (Pass 1D) | `process_linking_data` indexé dans le moteur ; flags `PROCESS_LINKING_ROLE_MISMATCH`, `PROCESS_LINKING_UNRESOLVED` |

## Références

- `docs/adr/ADR-M14-001_evaluation_engine.md`
- `docs/contracts/annotation/M12_M14_HANDOFF_CONTRACT.md`
- `docs/freeze/CONTEXT_ANCHOR.md` — addendum M14
