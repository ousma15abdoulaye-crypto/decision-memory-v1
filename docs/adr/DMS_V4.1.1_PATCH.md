# DMS V4.1.1 — PATCH NOTE
**Date :** 2026-03-11
**Autorite :** CTO / AO — Abdoulaye Ousmane
**Statut :** OFFICIEL — amende DMS_V4.1.0_FREEZE.md

---

## Objet

Documenter la divergence de slug Alembic entre le Plan
Directeur V4.1.0 (2026-02-26) et l'execution reelle.

## Divergences

| Migration | Plan Directeur V4.1.0 | Realite executee | Decision |
|-----------|----------------------|------------------|----------|
| 043 | extraction_jobs_async | market_signals_v11 | Context Anchor prime |
| 044 | ingestion_real_schema | decision_history | Context Anchor prime |
| 045 | evaluation_documents (M14) | agent_native_foundation (M10B) | Reaffecte |
| 046 | — | evaluation_documents | Decale M13/M14 |

## Justification

L'execution reelle a priorise :
  1. La qualite des signaux marche (M9 -> M10A)
  2. L'infrastructure agents (M10B)
  avant l'ingestion documentaire (prevue M13/M14).

Cette priorisation est validee CTO. Les objectifs business
du Plan Directeur V4.1.0 sont inchanges. Seul le sequencage
des migrations a ete adapte aux contraintes terrain.

## Regles maintenues sans exception

  REGLE-05  Append-only toute table decisionnelle
  REGLE-08  Probe avant toute migration
  REGLE-24  Tracabilite started_at + ended_at + duration_ms
  SEUILS-M15 coverage >=80%, unresolved <=25%,
             vendor >=60%, review_queue <=30%
