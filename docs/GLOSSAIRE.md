# Glossaire — Decision Memory System (DMS) V3.3.2

**Référence :** Constitution V3.3.2 (freeze actif et opposable)  
**Date :** 2026-02-19  
**Phase :** Zéro — Milestone M-DOCS-CORE

---

| Terme | Définition |
|-------|------------|
| **offre brute** | Document original soumis par un fournisseur (PDF, Excel, Word) avant tout traitement par le système. Contient les informations non structurées telles qu'elles ont été déposées. |
| **offre normalisée** | Offre brute après extraction et structuration par la Couche A. Les données sont normalisées selon le dictionnaire Sahel, les items sont résolus, et la structure est conforme au schéma `structured_data` JSONB. |
| **score** | Valeur numérique calculée par la Couche A selon les règles officielles de l'organisation. Les scores sont factuels et non prescriptifs — ils assistent la décision humaine sans la remplacer. Catégories : essentials, capacity, commercial, sustainability, total. |
| **classe A** | Désigne les processus et opérations de la Couche A (scoring, normalisation, extraction, génération d'exports). Soumis au SLA de 60 secondes maximum. Primauté absolue sur la Couche B. |
| **classe B** | Désigne les processus et opérations de la Couche B (résolution, enrichissement, market intelligence). Traitement asynchrone, read-only vis-à-vis de la Couche A. Ne peut jamais modifier un score ou influencer une décision. |
| **dictionnaire Sahel** | Référentiel canonique de normalisation des entités (items, fournisseurs, unités) spécifique au contexte Sahel. Seedé via migration Alembic, minimum 9 familles (carburants, construction_liants, construction_agregats, construction_fer, vehicules, informatique, alimentation, medicaments, equipements). Chaque item doit avoir au moins 3 aliases. |
| **freeze** | Processus de gel d'une version de la Constitution et des documents de référence (ADR, Milestones). Une version freezée est immuable et opposable aux agents et au code. Toute modification nécessite une nouvelle version (ex. v3.3.3) et un nouveau freeze. |
| **milestone** | Unité d'exécution atomique du plan de développement. Format : `M-<ID>` (ex. `M-DOCS-CORE`, `M-SCORING-ENGINE`). Un milestone = un sprint = une branche = une PR = un merge. Statut binaire : DONE ou ABSENT. |
| **invariant** | Règle système opposable à toute évolution. Les invariants V3 sont définis dans la Constitution V3.3.2 §2 et ne peuvent être modifiés que via amendement constitutionnel versionné. |
| **ADR** | Architecture Decision Record — document de décision architecturale gelé et opposable. Format : `ADR-000N.md`. Les ADR sont référencés dans le FREEZE_MANIFEST et ont des checksums SHA256 pour vérification d'intégrité. |
| **couche A** | Couche système responsable de 80-90% du travail cognitif répétitif : ingestion, extraction, normalisation, scoring, génération d'exports. Moteur d'analyse avec SLA 60s. Primauté absolue sur la Couche B. |
| **couche B** | Couche système responsable de la mémoire intelligente et market intelligence : capitalisation automatique, historisation, résolution d'entités, signaux factuels. Strictement read-only vis-à-vis de la Couche A. Ne prescrit jamais. |
| **gate CI** | Point de contrôle dans la chaîne CI/CD GitHub Actions. Un gate bloquant doit être vert pour permettre le merge. Les gates vérifient : tests, couverture, invariants, intégrité freeze, séparation A/B, triggers DB. |
| **phase zéro** | Phase préalable à tout milestone métier. Socle repo : structure dossiers, requirements.txt figé, helpers DB, Makefile, conftest.py, alembic/env.py. Gate : `make test` → tous skipped (0 échec), CI verte sur main. |

---

*© 2026 — Decision Memory System — Glossaire V3.3.2*
