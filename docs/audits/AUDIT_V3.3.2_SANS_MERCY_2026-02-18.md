# Audit V3.3.2 — Sans merci

**Date :** 2026-02-18  
**Référence :** docs/freeze/v3.3.2 (Constitution, Milestones, Invariants, FREEZE_MANIFEST, ADR-0001)  
**Objectif :** État des lieux exact — ce qui est fait, ce qui reste à faire, statut de la CI.

---

## 1. Documents V3.3.2 lus et pris en compte

| Document | Contenu synthétique |
|----------|---------------------|
| **CONSTITUTION_DMS_V3.3.2.md** | Identité DMS, Couche A/B, invariants §2, stack (FastAPI, PostgreSQL, pas d'ORM), doctrine d'échec explicite, freeze canonique. |
| **MILESTONES_EXECUTION_PLAN_V3.3.2.md** | Ordre figé : 1. M2-EXTENDED (DONE), 2. M4A-FIX (DONE), 3. M-REFACTOR, 4. M-TESTS, 5. M8 Couche B MVP, puis M3A, M3B, etc. |
| **INVARIANTS.md** | 9 invariants opposables : charge cognitive, primauté Couche A, mémoire non prescriptive, online-only, CI verte, append-only, ERP-agnostique, survivabilité, fidélité & neutralité. |
| **FREEZE_MANIFEST.md** | Scope freezé (4 fichiers + ADR), checksums, procédure de vérification (Linux/Windows). |
| **ADR-0001.md** | Constitution V3.3.2 = référence canonique ; toute évolution constitutionnelle = nouvelle version + nouveau freeze. |

---

## 2. CI — Réponse directe : oui, la CI a été refondue

La CI est **refondue** au sens V3.3.2 : pas de `|| true` ni de `continue-on-error` masquant des échecs (aligné avec Invariant 5 et doctrine d’échec explicite).

### 2.1 Workflows en place (7 fichiers)

| Workflow | Rôle | Déclencheur | Bloquant |
|----------|------|--------------|----------|
| **ci-main.yml** | Python 3.11, Postgres 15, deps, compileall, migrations, **Ruff check**, **Black check**, pytest (coverage dynamique) | PR/push sur `main` | Oui (sauf coverage si gate inactive) |
| **ci-freeze-integrity.yml** | Vérifie présence SHA256SUMS.txt + FREEZE_MANIFEST.md, exécute `sha256sum -c` | PR/push sur `main` | Oui (échec = exit 1) |
| **ci-invariants.yml** | Si `.milestones/M-CI-INVARIANTS.done` absent → mode report (exit 0) ; présent → exige `tests/invariants/` et `pytest tests/invariants -v` | PR/push sur `main` | Oui uniquement si gate active |
| **ci-milestones-gates.yml** | Vérifie l’ordre des milestones (M0-BOOT → … → M-CI-INVARIANTS) ; aucun `.done` après un manquant = violation | PR/push sur `main` | Oui |
| **ci-lint-ruff.yml** | Ruff check seul | PR/push sur `main` (+ fix/audit-urgent) | Oui |
| **ci-format-black.yml** | Black check ; si échec, format + commit + push (workflow_dispatch + push sur fix/audit-urgent) | Manuel + push branches ciblées | Non (correctif auto) |
| **ci-regenerate-freeze-checksums.yml** | Régénère SHA256SUMS.txt si besoin | (à vérifier selon config) | Non (maintenance) |

### 2.2 Gates dynamiques (Conformes au plan)

- **Coverage :** `ci-main.yml` utilise `.milestones/M-TESTS.done` → si présent : `--cov-fail-under=40` ; sinon `--cov-fail-under=0` (reporting seul).
- **Invariants :** `ci-invariants.yml` exige les tests invariants seulement si `.milestones/M-CI-INVARIANTS.done` existe.
- **Freeze :** Vérification stricte des checksums ; pas de contournement.

### 2.3 Points de vigilance

- **Doublon possible :** `ci-main.yml` fait déjà Ruff + Black ; `ci-lint-ruff.yml` refait Ruff. Pas bloquant, mais redondant.
- **Ordre des milestones :** `ci-milestones-gates.yml` utilise une liste (M0-BOOT, M1-DATABASE, …) qui ne correspond pas à l’ordre du plan d’exécution (M2-EXTENDED, M4A-FIX, M-REFACTOR, M-TESTS, M8…). À aligner si on veut que la gate reflète exactement le plan figé.

---

## 3. Ce qui est fait (aligné V3.3.2)

| Élément | Statut | Preuve / remarque |
|---------|--------|--------------------|
| **Freeze V3.3.2** | Fait | `docs/freeze/v3.3.2/` présent ; SHA256SUMS.txt à jour (4 fichiers) ; FREEZE_MANIFEST.md décrit la procédure. |
| **CI sans masquage d’échecs** | Fait | Aucun `|| true` / `continue-on-error` sur les steps critiques dans les workflows lus. |
| **CI Main (lint + test + migrations)** | Fait | Postgres 15, Python 3.11, Ruff, Black, alembic upgrade head, pytest avec gate coverage. |
| **CI Freeze Integrity** | Fait | Vérification existence + checksums. |
| **CI Invariants (gate conditionnelle)** | Fait | Gate M-CI-INVARIANTS.done ; Postgres + DATABASE_URL pour les tests invariants. |
| **CI Milestones Gates** | Fait | Vérification ordre des `.done` (liste à aligner avec le plan, voir ci-dessus). |
| **Tests invariants (structure)** | Fait | `tests/invariants/` existe avec 9 fichiers (inv_01 à inv_09). |
| **Stack Constitution** | Fait | FastAPI, Python 3.11, PostgreSQL, pas d’ORM dans les parties vues ; helpers DB synchrones. |
| **Couche A / Couche B** | Fait | Séparation nette (routers Couche A, `src.couche_b` pour résolution fuzzy). |
| **main.py allégé** | Partiel | `main.py` ~67 lignes (bootstrap + routers) ; logique déléguée aux modules. M-REFACTOR peut encore viser à déplacer le bootstrap dans `src` si le plan l’exige. |

---

## 4. Ce qui reste à faire (plan d’exécution strict)

D’après **MILESTONES_EXECUTION_PLAN_V3.3.2.md** (ordre figé) :

| # | Milestone | Statut plan | À faire |
|---|-----------|-------------|---------|
| 1 | M2-EXTENDED – Références & catégories | DONE | — |
| 2 | M4A-FIX – Chaîne Alembic 002→003→004 | DONE | — |
| 3 | **M-REFACTOR – Découpage de main.py** | À faire | Découper / déplacer si nécessaire (main.py déjà court ; vérifier CADRE_TRAVAIL pour le périmètre exact). |
| 4 | **M-TESTS – Remonter la qualité des tests** | À faire | Atteindre coverage cible ; créer `.milestones/M-TESTS.done` quand ≥ 40 % pour activer la gate. |
| 5 | **M8 – Couche B MVP – Mémoire vivante minimaliste** | À faire | Implémentation MVP Couche B (mémoire marché, sans décision). |
| 6 | Ensuite | — | M3A, M3B, M2B, M5, M6, M7, etc. |

### 4.1 Détails utiles

- **Aucun `.done` dans `.milestones/`** (hors README) : les gates coverage et invariants sont en mode « report » (non bloquantes). Pour les activer : créer `M-TESTS.done` et/ou `M-CI-INVARIANTS.done` quand les objectifs sont atteints.
- **Stub connu :** `src/api/analysis.py` contient un stub `extract_dao_criteria_structured` (retourne `[]`) ; à implémenter ou à retirer les appels (bug documenté dans le code).
- **Alignement gate milestones :** La liste dans `ci-milestones-gates.yml` (M0-BOOT, M1-DATABASE, …) ne reflète pas l’ordre du plan (M2-EXTENDED, M4A-FIX, M-REFACTOR, M-TESTS, M8…). À harmoniser avec le plan si la gate doit être la source de vérité.

---

## 5. Synthèse

- **CI :** Refondue. Stricte, sans masquage d’échecs, avec freeze integrity, gates dynamiques (coverage, invariants) et vérification d’ordre des milestones.
- **Fait :** Freeze V3.3.2, CI Main/Freeze/Invariants/Milestones, structure tests invariants, stack et séparation Couche A/B, main.py déjà réduit.
- **Reste à faire (ordre du plan) :** M-REFACTOR (clarifier périmètre), M-TESTS (coverage + M-TESTS.done), M8 Couche B MVP, puis M3A, M3B, etc. Corriger le stub `extract_dao_criteria_structured` et aligner la liste des milestones dans `ci-milestones-gates.yml` avec le plan d’exécution si souhaité.

---

*Audit réalisé sur la base des docs freezés V3.3.2 et de l’état actuel du dépôt (workflows, code, tests).*
