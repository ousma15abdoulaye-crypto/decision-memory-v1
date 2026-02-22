Voici la **VERSION FINALE** d’ADR-0008, intégrant **les 2 micro-corrections** que je recommande (clarification ARCH-001 vs localisation, et exception contrôlée pour les mandats `fix/` quand les tests sont rouges au départ), **sans changer le fond**.

Tu peux **copier-coller et geler** tel quel.

---

# ADR-0008 — PROTOCOLE D'EXÉCUTION MILITAIRE (V1.2)

**Status** : ACCEPTED — **GEL IMMÉDIAT**
**Date** : 2026-02-22
**Décideur** : CTO (Abdoulaye Ousmane)
**Contexte** : Post M-CRITERIA-FK + M-NORMALISATION-ENGINE (DT-001/DT-002 liquidées)
**Opposabilité** : Tous milestones, tous agents (humains & IA), sans exception.

---

## 1) STATUT

**ACCEPTED — GEL IMMÉDIAT**
Opposable sur tous les milestones, tous les agents.

---

## 2) CONTEXTE ET PROBLÈME

Les milestones **M-CRITERIA-FK** et **M-NORMALISATION-ENGINE** ont révélé trois pathologies récurrentes :

| Pathologie            | Manifestation                                       |
| --------------------- | --------------------------------------------------- |
| **Saut de séquence**  | Agent pose du code avant preuve DB / migrations     |
| **Contrat implicite** | `None` retourné là où un objet structuré est requis |
| **Clôture fantôme**   | CI verte sans `.done` ⇒ milestone non opposable     |

Ces pathologies sont **structurelles** : sans protocole gravé, un agent optimise localement et dégrade globalement.

---

## 3) DÉCISION

Le **Protocole d’Exécution Militaire V1.2** est la séquence **canonique et obligatoire** pour tout milestone DMS.

---

## 4) PROTOCOLE — TEXTE NORMATIF

### 4.1 — 8 ÉTAPES, AUCUN SAUT

#### **ÉTAPE 0 — Pré-flight (Reconnaissance terrain)**

Obligatoire avant tout changement.

* `git status` + `git branch --show-current` + `git log -5`
* `Get-ChildItem .milestones\`
* `alembic heads` + `alembic current`
* `pytest tests/ -q --tb=short`

**STOP immédiat** si :

* `alembic` cassé / incohérent
* `alembic heads > 1`
* tests rouges avant milestone (hors skips connus)

**Exception contrôlée (mandat `fix/<...>`) :**
Si la branche est un **correctif** (`fix/`), les tests peuvent être rouges au départ. Dans ce cas :
🛑 STOP uniquement si **le nombre de fails augmente**, ou si un **fail hors scope** apparaît.

---

#### **ÉTAPE 1 — Branche + Preuve DB (preuve, pas intuition)**

* `git checkout -b feat/<MILESTONE>` (ou `fix/<...>` si correctif)
* Exécuter une **preuve DB** (psycopg direct) contre `information_schema` et/ou `pg_catalog`

**DB-PROOF-001 — preuve DB minimale obligatoire :**

1. état migrations : `alembic heads/current`
2. existence des tables du milestone (schema + table)
3. contraintes concernées (FK/UNIQUE/CHECK)
4. index attendus (ou absence assumée)
5. seed/coverage si milestone dict/normalisation

**STOP** si la DB contredit le plan ⇒ remonter CTO avant tout code.

---

#### **ÉTAPE 2 — Décision migration (Alembic)**

Règle :

* **Si DB conforme → aucune migration**
* **Si DB non conforme → migration obligatoire**

Commandes :

* Vérifier `revision_id ≤ 32 chars` **avant** upgrade (ALEMBIC-001)
* `alembic upgrade head` → `alembic current` → `alembic heads`

**STOP** si :

* erreur Alembic
* head multiple
* ID > 32 chars
* chaîne incohérente

---

#### **ÉTAPE 3 — Tests DB-level (invariants DB avant API)**

* `pytest tests/db_integrity -q --tb=short`

**STOP si rouge.**
Aucun endpoint / router n’est touché tant que DB-level n’est pas vert.

---

#### **ÉTAPE 4 — Service (logique métier minimale)**

* SQL paramétré uniquement (SQL-001)
* Doctrine d’échec : **jamais catch-all**
* **Zéro import Couche B** dans modules décisionnels Couche A (ADR-0002)

---

#### **ÉTAPE 5 — Router / API**

* `ForeignKeyViolation` **discriminée** (jamais catch-all)
* Le router **ne ment jamais** sur la cause (case vs canonical_item vs autre)

---

#### **ÉTAPE 6 — Tests ciblés milestone**

* `pytest tests/api/test_<milestone>.py -v --tb=short` (ou tests normalisation dédiés)

**STOP si rouge.**

---

#### **ÉTAPE 7 — Suite complète + clôture**

Vérité finale (obligatoire) :

* `pytest tests/ -q --tb=short` → **0 failed**
* `ruff check src tests` → **All checks passed**
* `black --check src tests` → **unchanged**

Puis seulement :

* Créer `.milestones/<MILESTONE>.done`
* `git add` fichier par fichier (STAGING-001)
* `git diff --cached --stat` (preuve scope)
* `git commit` + `git push` + PR

---

### 4.2 — RÈGLES PERMANENTES (CANONIQUES)

| ID               | Règle                 | Contenu                                                                                                                                                                                                                               |
| ---------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **ALEMBIC-001**  | revision_id           | ≤ 32 chars — vérifier avant upgrade                                                                                                                                                                                                   |
| **CONFTEST-001** | TESTING flag          | `TESTING=true` avant tout import `src.*` dans tests                                                                                                                                                                                   |
| **STAGING-001**  | `git add`             | fichier par fichier — `git add .` interdit                                                                                                                                                                                            |
| **SEED-001**     | `ON CONFLICT`         | `ON CONFLICT (col_exacte) DO NOTHING` — jamais vague                                                                                                                                                                                  |
| **SCHEMA-001**   | FK cross-schema       | référence explicite `schema.table(col)`                                                                                                                                                                                               |
| **SQL-001**      | SQL paramétré         | jamais f-string avec user input                                                                                                                                                                                                       |
| **ARCH-001**     | Autorité données      | moteur adossé à une autorité de données → Couche B                                                                                                                                                                                    |
| **ARCH-001clar** | Autorité ≠ dossier    | **ARCH-001 fixe l’autorité (DB Couche B), pas le répertoire.** La localisation du code est libre tant que ADR-0002 est respecté (pas d’import Couche B dans Couche A; lecture SQL paramétrée OK).                                     |
| **ARCH-001bis**  | Couplage autorisé     | Couche A peut référencer Couche B **uniquement** via **contraintes DB (FK)** ou **lecture SQL paramétrée**. Interdit : importer modules Python Couche B, ou faire dépendre la logique décisionnelle (scoring) d’une mémoire Couche B. |
| **ARCH-002**     | Signature retour      | résultat métier exposé = toujours objet structuré — jamais None                                                                                                                                                                       |
| **ARCH-002bis**  | Scope “jamais None”   | s’applique aux résultats métier exposés (API/pipeline/normalisation/scoring). Helpers internes peuvent retourner None seulement si jamais sérialisés, jamais franchissement de frontière.                                             |
| **ARCH-003**     | Schémas inter-couches | Pydantic obligatoire dès qu’un résultat traverse une frontière                                                                                                                                                                        |
| **GIT-LOCK-001** | index.lock            | si `.git/index.lock` existe → STOP, kill processus git/python, supprimer lock, reprendre                                                                                                                                              |

---

### 4.3 — TECHNIQUE D’ISOLATION C1/C2/C3

**C1** : Liste exacte des fails

* `--tb=no` + `Select-String FAILED|ERROR`

**C2** : Test A/B “pré-existant”

* `main` vs branche, DB cohérente (pas de DB “avancée” localement)

**C3** : Patch minimal

* Une cause, un patch
* Jamais refactor, jamais skip

---

### 4.4 — DÉFINITION OF DONE (IMMUABLE)

✅ `alembic current` = head attendu
✅ Gates milestone = verts
✅ `pytest tests/` = **0 failed**
✅ `ruff` + `black` = clean
✅ `.milestones/<MILESTONE>.done` présent **et complet**
✅ `git diff --cached --stat` = scope exact
✅ PR ouverte — merge interdit sans review CTO

**DONE-001 — Contenu minimal `.done` obligatoire :**

* `milestone_id`
* `date`
* `branch`
* `commit_sha`
* `db_head` (sortie `alembic heads`)
* `tests` (passed/failed/skipped + preuve `0 failed`)
* `ruff` (pass/fail)
* `black` (pass/fail)
* `files` (liste exacte `git diff --cached --name-only`)
* `verdict` : DONE (binaire)

---

### 4.5 — SIGNAUX D’ARRÊT UNIVERSELS

🛑 `alembic heads > 1`
🛑 tests rouges avant milestone (hors skips connus)
🛑 DB contredit le plan
🛑 `pytest tests/` repasse au-dessus de 0 failed
🛑 un service métier exposé retourne `None`
🛑 surprise non couverte par mandat → remonter CTO

---

## 5) CONSÉQUENCES

### Positives

* Chaque milestone est auditable sans contexte verbal
* Les `.done` deviennent un journal cumulatif d’opposabilité
* Les agents ne peuvent plus optimiser localement au détriment du système

### Négatives acceptées

* Séquence plus longue qu’un “quick fix”
* Pré-flight obligatoire même sur milestone trivial

### Non-conséquences

* Ne remplace pas ADR-0001/ADR-0002
* Ne définit pas l’architecture : définit **comment exécuter**

---

## 6) ALTERNATIVES REJETÉES

| Alternative                                  | Raison du rejet                                 |
| -------------------------------------------- | ----------------------------------------------- |
| Protocole optionnel selon complexité         | crée jugement local ⇒ dégrade globalement       |
| Pas de `.done` sur milestones sans migration | `.done` = opposabilité, pas preuve de migration |
| `None` autorisé sur UNRESOLVED               | muet, non traçable, non auditable               |
| “On skip pour avancer”                       | masque dette, casse invariants                  |

---

## 7) FORMULE GRAVÉE

**"On ne fait pas passer les tests. On contraint le système jusqu'à ce qu'il n'ait plus d'autre choix."**
— CTO, DMS V3.3.2

---

## 8) RÉFÉRENCES

* **ADR-0001** : Architecture Couche A / Couche B
* **ADR-0002** : Frontières et contrats inter-couches
* **M-CRITERIA-FK** : origine DT-001 + guard alembic multi-head
* **M-NORMALISATION-ENGINE** : origine DT-002 (ARCH-001/002/003)

---

## ÉTAT GLOBAL — POST ADR-0008

* Constitution : V3.3.2
* ADR actifs : 0001 ✅ | 0002 ✅ | **0008 ✅ (GELÉ)**
* Protocole exec : Militaire V1.2 — ADR-0008 ✅
* DB head : 023_m_criteria_fk
* CI : `pytest tests/ = 0 failed` (compteurs passed/skipped informatifs)
* DT-001 : ✅ LIQUIDÉE
* DT-002 : ✅ LIQUIDÉE
* DT-003 : ACTIVE — prochaine cible

**ADR-0008 : GELÉ.**

---
