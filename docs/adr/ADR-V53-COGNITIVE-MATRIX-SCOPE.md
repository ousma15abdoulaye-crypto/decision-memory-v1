# ADR-V53 — Périmètre matrice cognitive E×permission (mode I-doc)

**Statut :** Accepted  
**Date :** 2026-04-11  
**Choix :** **I-doc** — la matrice canonique 17×6 complète n’est pas implémentée dans le code ; le comportement opposable documenté reste celui de `docs/architecture/dms_atlas_v1/P0_L2_cognitive_engine.md` (projection E0–E6 + guards de transition + `m16_guard` sur routes M16).

**Conséquence :** toute évolution vers une matrice exhaustive = mandat **I-impl** distinct avec liste de routers.
