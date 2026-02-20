# Guide de contribution — Decision Memory System (DMS) V3.3.2

**Référence :** Constitution V3.3.2 (freeze actif et opposable) + ADR-0003 + ADR-0004  
**Date :** 2026-02-19  
**Phase :** Zéro — Milestone M-DOCS-CORE

---

## Règles pour humains et agents IA

Ce guide s'applique à **tous les contributeurs**, qu'ils soient humains ou agents IA (Cursor, Claude, Copilot, etc.).

### Prérequis avant toute contribution

**Documents de référence obligatoires (à lire avant tout code) :**
1. `docs/freeze/v3.3.2/CONSTITUTION_DMS_V3.3.2.md`
2. `docs/freeze/v3.3.2/MILESTONES_EXECUTION_PLAN_V3.3.2.md`
3. `docs/freeze/v3.3.2/adrs/ADR-0003.md`
4. `docs/adrs/ADR-0004.md`

**Vérification de l'état du projet :**
```bash
make milestone-status  # Identifier le milestone actif
```

---

## Règles de workflow

### Aucun commit direct sur main

**Règle absolue :** Tous les commits doivent passer par une branche et une Pull Request.

**Interdit :**
- ❌ Commits directs sur `main`
- ❌ Force push sur `main`
- ❌ Merge sans PR

**Obligatoire :**
- ✅ Créer une branche depuis `main`
- ✅ Travailler sur la branche
- ✅ Ouvrir une PR vers `main`
- ✅ Attendre la validation CI et review avant merge

### Branche obligatoire + PR

**Format de nommage des branches :**
```
<type>/<milestone-id>-<description>
```

**Types autorisés :**
- `feat/` — Nouvelle fonctionnalité
- `fix/` — Correction de bug
- `docs/` — Documentation uniquement
- `test/` — Ajout/modification de tests uniquement
- `ci/` — Modification CI/CD uniquement
- `refactor/` — Refactoring sans changement fonctionnel
- `chore/` — Tâches de maintenance

**Exemples valides :**
- `feat/M-DOCS-CORE-architecture-docs`
- `fix/M-SCORING-ENGINE-confidence-calculation`
- `docs/M-DOCS-CORE-glossaire-contributing`
- `test/M-EXTRACTION-ENGINE-magic-bytes-validation`

**Exemples interdits :**
- ❌ `feat/scoring` (milestone manquant)
- ❌ `fix/db` (description trop vague)
- ❌ `wip/improvements` (type invalide, milestone manquant)

**Référence :** ADR-0003 §3.2 — Convention de nommage (gelée)

### CI verte avant merge

**Règle binaire :** Aucune PR ne peut être mergée si la CI est rouge.

**Gates CI bloquants :**
- Tests unitaires (pytest)
- Tests d'intégrité DB (`tests/db_integrity/`)
- Tests d'invariants (`tests/invariants/`)
- Vérification freeze (checksums SHA256)
- Test séparation A/B (`test_couche_a_b_boundary.py`)
- Linting (ruff)
- Couverture de code (selon phase : 0/40/60/75%)

**Procédure :**
1. Pousser la branche sur GitHub
2. Attendre que tous les gates CI soient verts
3. Si rouge → corriger localement → push → réitérer
4. Une fois vert → demander review
5. Après review approuvée → merge autorisé

**Interdit :**
- ❌ Merge avec CI rouge "pour avancer"
- ❌ Masquage d'erreurs avec `|| true` dans CI
- ❌ Désactivation temporaire de tests

**Référence :** ADR-0003 §2.1 — Principe de commandement (opposable)

### Aucun code src/ sans milestone actif validé

**Règle :** Aucun code métier ne peut être écrit en dehors d'un milestone actif.

**Procédure :**
1. Vérifier le milestone actif : `make milestone-status`
2. Lire la séquence interne du milestone dans ADR-0003 §2.2
3. Respecter l'ordre strict : Migration → Tests DB → Service → Endpoint → Tests API → `.done`
4. Ne pas passer à l'étape N+1 si l'étape N est rouge

**Interdit :**
- ❌ Écrire du code métier avant Phase Zéro complète
- ❌ Démarrer un milestone sans que le précédent soit `.done`
- ❌ Travailler sur plusieurs milestones en parallèle

**Référence :** ADR-0003 §2.2 — Ordre d'exécution interne à chaque milestone

### Aucune modification fichiers freeze sans ADR

**Règle absolue :** Les fichiers dans `docs/freeze/v3.3.2/` sont immuables.

**Fichiers freezés :**
- `docs/freeze/v3.3.2/CONSTITUTION_DMS_V3.3.2.md`
- `docs/freeze/v3.3.2/MILESTONES_EXECUTION_PLAN_V3.3.2.md`
- `docs/freeze/v3.3.2/INVARIANTS.md`
- `docs/freeze/v3.3.2/adrs/ADR-*.md`

**Procédure pour modifier un fichier freezé :**
1. Créer un nouvel ADR (ADR-0004+) justifiant la modification
2. Obtenir validation CTO explicite
3. Créer une nouvelle version (ex. v3.3.3)
4. Nouveau répertoire `docs/freeze/v3.3.3/`
5. Nouveau SHA256SUMS.txt
6. Mise à jour du FREEZE_MANIFEST

**Interdit :**
- ❌ Modifier directement un fichier freezé
- ❌ Contourner le freeze "pour corriger une typo"
- ❌ Créer une nouvelle version sans ADR

**Référence :** `docs/freeze/v3.3.2/FREEZE_MANIFEST.md` — Règle d'opposabilité

### Format commit conventionnel

**Format :**
```
<type>(<milestone>): <description>
```

**Types autorisés :**
- `feat` — Nouvelle fonctionnalité
- `fix` — Correction de bug
- `docs` — Documentation uniquement
- `test` — Ajout/modification de tests
- `ci` — Modification CI/CD
- `refactor` — Refactoring sans changement fonctionnel
- `chore` — Tâches de maintenance
- `migration` — Migration Alembic
- `seed` — Données de seed
- `trigger` — Trigger PostgreSQL

**Exemples valides :**
- `feat(M-DOCS-CORE): migration cases + documents`
- `test(M-DOCS-CORE): magic bytes validation`
- `fix(M-EXTRACTION-ENGINE): confidence score rules`
- `trigger(M-COMMITTEE-CORE): lock irréversible DB-level`
- `docs(M-DOCS-CORE): architecture glossaire contributing`

**Exemples interdits :**
- ❌ `fix: bug` (milestone manquant)
- ❌ `update db` (type invalide, format incorrect)
- ❌ `WIP: working on scoring` (format non conventionnel)

**Référence :** ADR-0003 §3.2 — Convention de nommage (gelée)

### Référence à ADR-0003 pour les règles d'escalade

**Règles d'escalade (ADR-0003 §7.3 + ADR-0004) :**

Toute modification du plan d'exécution (durées, séquence, règles agent, gates) nécessite :
1. Un nouvel ADR (ADR-0004+)
2. Validation CTO explicite
3. Nouveau tag git + SHA256 dans FREEZE_MANIFEST.md

**Cas d'escalade courants :**
- **Milestone bloqué :** Ne pas improviser → créer ADR justifiant la modification
- **CI rouge non résolvable :** Ne pas masquer → analyser la cause racine → ADR si changement de règle nécessaire
- **Dépendance non prévue :** Ne pas contourner → documenter dans ADR → valider avec CTO

**Principe :** Toute déviation du plan est une erreur. Toute erreur doit être corrigée par ADR numéroté, pas par improvisation en cours de session.

**Référence :** 
- `docs/freeze/v3.3.2/adrs/ADR-0003.md` §7.3 — Sur les modifications futures  
- `docs/adrs/ADR-0004.md` §2 et §4 — Phase 0 corrigée & exception migration 011

---

## Checklist avant ouverture de PR

Avant d'ouvrir une PR, vérifier :

- [ ] Branche nommée selon convention : `<type>/<milestone-id>-<description>`
- [ ] Tous les commits suivent le format : `<type>(<milestone>): <description>`
- [ ] Code aligné avec Constitution V3.3.2
- [ ] Aucun import Couche B dans modules Couche A
- [ ] Requêtes SQL paramétrées exclusivement (pas de f-string SQL)
- [ ] Aucun ORM utilisé
- [ ] Tests DB-level écrits avant tests API (si applicable)
- [ ] Migration SQL avant service Python (si applicable)
- [ ] `make test` vert localement
- [ ] `make lint` sans erreurs
- [ ] Aucun fichier freezé modifié (sauf avec ADR validé)
- [ ] Milestone actif identifié et respecté

---

## Règles spécifiques par type de contribution

### Code métier (src/)

**Obligations :**
- Migration Alembic AVANT service Python
- Trigger PostgreSQL DANS la migration (pas dans le code)
- Test DB-level AVANT test API
- Requêtes paramétrées exclusivement
- Aucun ORM

**Interdictions :**
- ❌ ORM (SQLAlchemy, Tortoise, Beanie)
- ❌ Requêtes SQL non paramétrées
- ❌ Import Couche B dans Couche A
- ❌ Trigger PostgreSQL écrit en Python

### Tests

**Ordre d'exécution :**
1. Tests DB-level (`tests/db_integrity/`, `tests/invariants/phase0/`)
2. Tests unitaires (`tests/couche_a/`, `tests/couche_b/`)
3. Tests API (`tests/api/`)

**Obligations :**
- Squelette test activé AVANT le code qu'il teste
- Tests DB-level verts avant de passer aux tests API
- Couverture selon phase : 0% (Phase Zéro) → 40% (Phase 1) → 60% (Phase 3) → 75% (Phase 5+)

### Documentation

**Fichiers autorisés :**
- `docs/*.md` (hors `docs/freeze/`)
- Commentaires dans le code
- Docstrings Python

**Fichiers interdits :**
- Modification de `docs/freeze/v3.3.2/*` sans ADR

### CI/CD

**Modifications autorisées :**
- Ajout de nouveaux gates CI
- Correction de bugs dans les workflows
- Amélioration de la lisibilité

**Modifications interdites :**
- Masquage d'erreurs avec `|| true`
- Désactivation de tests "temporairement"
- Modification des checksums freeze sans nouvelle version

---

## Support et questions

**Pour toute question sur :**
- Les règles de contribution → Relire ce document + ADR-0003
- Un milestone spécifique → Consulter `docs/freeze/v3.3.2/MILESTONES_EXECUTION_PLAN_V3.3.2.md`
- La Constitution → Consulter `docs/freeze/v3.3.2/CONSTITUTION_DMS_V3.3.2.md`
- Une escalade nécessaire → Créer un ADR selon ADR-0003 §7.3

---

*© 2026 — Decision Memory System — Guide de contribution V3.3.2*
