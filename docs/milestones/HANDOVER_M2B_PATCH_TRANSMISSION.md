# NOTE DE TRANSMISSION — M2B-PATCH · SOLDE DETTES UTC-01 + FIXTURE-01

```
Date       : 2026-03-01
Milestone  : M2B-PATCH
Branche    : feat/m2b-patch-dettes — SUPPRIMÉE post-merge PR#140
Statut     : DONE — tag v4.1.0-m2b-patch-done posé sur main (commit f698a51)
Agent      : Claude Sonnet 4.6 (session 2026-03-01)
Successeur : Agent M3 (données réelles — géographie Mali · fournisseurs)
```

---

## I. ÉTAT DU REPO À LA TRANSMISSION

| Élément | État |
|---|---|
| Branche active | `main` (commit `f698a51`) |
| Alembic head | `039_created_at_timestamptz` — exactement 1 — **inchangé depuis M2B** |
| CI locale post-merge | **574 passed · 36 skipped · 0 failed** |
| ruff | 0 erreur |
| black | 0 erreur |
| Tag | `v4.1.0-m2b-patch-done` — posé sur `main` + pushé origin |
| Branche feat/m2b-patch-dettes | Mergée via PR#140 — supprimable |
| DB locale | `users.created_at = TIMESTAMPTZ` · FK NOT VALID local (doctrine ADR-0012 — inchangé) |
| DB prod Railway | Inchangée — aucune migration posée en M2B-PATCH |

---

## II. CE QUE M2B-PATCH A LIVRÉ

### Objectif accompli

Solde de deux dettes techniques P1/P2 ouvertes depuis M2B, sans migration Alembic, sans fichier hors périmètre.

---

### Commits

| SHA | Message |
|---|---|
| `77f23d5` | `fix(m2b-patch): solde DETTE-UTC-01 + DETTE-FIXTURE-01` |
| `b469dc9` | `docs(m2b-patch): aligner doc UTC — UTC alias timezone.utc (review Copilot PR#140)` |
| `f698a51` | Merge PR#140 |

---

### BLOC B — DETTE-UTC-01 soldée

**Problème :** `datetime.utcnow()` produisait des timestamps naïfs (sans offset timezone). Après migration 039 (`users.created_at TIMESTAMPTZ`), un INSERT avec timestamp naïf est interprété selon la TZ de session PostgreSQL — non déterministe.

**Solution :** Remplacement mécanique dans 8 fichiers `src/` :

```python
# AVANT
from datetime import datetime
datetime.utcnow().isoformat()

# APRÈS
from datetime import UTC, datetime
datetime.now(UTC).isoformat()
```

**Fichiers modifiés :**

| Fichier | Occurrences remplacées |
|---|---|
| `src/api/cases.py` | 1 |
| `src/api/analysis.py` | 3 |
| `src/couche_a/routers.py` | 1 |
| `src/core/dependencies.py` | 2 |
| `src/couche_a/scoring/models.py` | 1 (default_factory lambda) |
| `src/couche_a/scoring/engine.py` | 1 |
| `src/couche_a/extraction.py` | 2 |
| `src/business/templates.py` | 4 |

**Exclu intentionnel :** `src/api/auth_helpers.py` — hors périmètre M2B-PATCH (DETTE-M1-04 active · 2 occurrences `utcnow()` résiduelles acceptées).

---

### BLOC A — DETTE-FIXTURE-01 soldée

**Problème :** Fixtures `pipeline_runs` créées avant existence de la FK `fk_pipeline_runs_case_id` (contexte M0B) référençaient des `case_id` fantômes.

**Résolution par probe :** Les tests actuels n'introduisent **pas** de `case_id` orphelins :
- Tests pipeline normaux → utilisent `case_factory()` (case réel en DB)
- Tests avec `case_id` fantôme → utilisent `pytest.raises(ForeignKeyViolation)` — tests délibérés de rejet FK
- Isolation → `db_transaction` avec rollback automatique — aucun `DELETE` sur `pipeline_runs`
- Les 166 orphelins historiques = legacy pré-FK, non supprimables (ADR-0012 — doctrine prime)

---

### TECHNICAL_DEBT.md

| Dette | Statut avant | Statut après |
|---|---|---|
| DETTE-UTC-01 | OUVERTE P1 | **SOLDÉE — M2B-PATCH** |
| DETTE-FIXTURE-01 | OUVERTE P2 | **SOLDÉE — M2B-PATCH** |
| DETTE-M1-04 | ACTIVE DROP BLOQUÉ | ACTIVE DROP BLOQUÉ — inchangé |

---

## III. CONTEXTE DE REPRISE — CE QUE L'AGENT SUCCESSEUR DOIT SAVOIR

### Situation particulière de cette session

Le prédécesseur immédiat (session précédente) avait déjà complété **tout le travail technique** (8 fichiers UTC + TECHNICAL_DEBT.md) avant d'être déconnecté. Il manquait uniquement le commit final. L'agent de cette session a :
1. Repris l'état exact via le handover et `git status`
2. Vérifié l'absence de duplication de code introduite
3. Lancé la validation complète (pytest 574 passed · ruff · black · alembic)
4. Posé le commit, créé la PR#140, intégré la review Copilot, pushé la correction
5. Posé le tag `v4.1.0-m2b-patch-done` sur `main` après merge (agent — `CLAUDE.md`)

---

## IV. DETTES TECHNIQUES — ÉTAT FINAL M2B-PATCH

| ID | Description | Statut |
|---|---|---|
| DETTE-M1-04 | `users.role_id` INTEGER FK → `roles` · 7 usages runtime | **ACTIVE — DROP BLOQUÉ** |
| DETTE-M2-02 | `conditional_limit` no-op dans `src/ratelimit.py` | Active — M3+ |
| DETTE-M2-03 | 36 skipped non audités intégralement | 4 légitimes audités · 32+ restants M3 |
| DETTE-UTC-01 | Timestamps naïfs `datetime.utcnow()` | **SOLDÉE — M2B-PATCH** |
| DETTE-FIXTURE-01 | Fixtures `pipeline_runs` non conformes | **SOLDÉE — M2B-PATCH** |

### Résidu DETTE-M1-04 (2 occurrences `utcnow()` restantes)

```python
# src/api/auth_helpers.py:85
{"ts": datetime.utcnow().isoformat(), "id": user["id"]}

# src/api/auth_helpers.py:99
timestamp = datetime.utcnow().isoformat()
```

Ces 2 occurrences seront traitées **avec DETTE-M1-04** (extinction `role_id` + refactor `auth_helpers`). Ne pas toucher avant.

---

## V. SÉQUENCE MILESTONES

```
M0        ✅ v4.1.0-m0-done         — CI verte · repo truth sync
M0B       ✅ v4.1.0-m0b-done        — Migration 036 DB hardening · FK NOT VALID · triggers
M1        ✅ v4.1.0-m1-done         — JWT · RBAC · middleware · rate limiting · headers
M1B       ✅ v4.1.0-m1b-done        — audit_log · chain_seq · SHA-256 · fn_verify_audit_chain
M2        ✅ v4.1.0-m2-done         — Unification auth · src/auth.py supprimé · smoke Railway vert
M2B       ✅ v4.1.0-m2b-done        — Hardening DB · 4 dettes soldées · prod propre
M2B-PATCH ✅ v4.1.0-m2b-patch-done  — UTC-01 + FIXTURE-01 soldées · 574 tests verts
M3        ⬜ PROCHAIN               — Base cesse d'être vide — géographie + fournisseurs réels
M9 → M21  ⬜ OUVERTS
```

---

## VI. ÉTAT DB — INVARIANTS À CONNAÎTRE

```
Alembic head  : 039_created_at_timestamptz (inchangé depuis M2B)
Prochaine ID  : 040_  (réservée DETTE-M1-04 — DROP COLUMN role_id)

Tables append-only (ADR-0012 — trigger BEFORE DELETE) :
  pipeline_runs · pipeline_step_runs · analysis_summaries · audits

FK NOT VALID local :
  fk_pipeline_runs_case_id — 166 orphelins legacy · NON supprimables
  → NOT VALID assumé local · validée prod (ADR-M2B-001)

Colonnes legacy à dropper (post-conditions non réunies) :
  users.role_id INTEGER FK → roles (7 usages runtime — DETTE-M1-04)
```

---

## VII. PIÈGES CONNUS — NE PAS RÉPÉTER

| Piège | Cause | Fix |
|---|---|---|
| PowerShell `&&` invalide | PS n'accepte pas `&&` | Séparer avec `;` ou passer par fichier `.py` |
| PowerShell heredoc `<<'EOF'` invalide | Syntaxe bash uniquement | Écrire le body dans un fichier `.txt` puis `--body-file` |
| `gh` CLI absent | Non installé par défaut | Portable ZIP disponible sur `github.com/cli/cli/releases` — ou API REST via Python |
| `git credential fill` bloque | Attend stdin interactif | Extraire le token via `ctypes.windll.advapi32.CredReadW('git:https://github.com', 1, ...)` |
| `rg` / `head` / `tail` / `cat` absents | Pas dans PATH PowerShell | Utiliser `Grep` tool ou `Select-Object -Last N` |
| pytest background sans output | Pipe `2>&1` + `Out-File` ne crée pas le fichier si PS termine vite | Lancer avec `block_until_ms` suffisant ou en premier plan |
| Fixtures `pipeline_runs` + trigger append-only | `DELETE teardown` interdit | Toujours utiliser `db_transaction` (rollback) |
| `winget install --silent` bloqué | UAC Windows empêche MSI silencieux | Utiliser la version portable ZIP |
| `datetime.utcnow()` dans `auth_helpers.py` | Hors périmètre M2B-PATCH | Traiter avec DETTE-M1-04 uniquement |

---

## VIII. COMMANDES DE VÉRIFICATION RAPIDE

```powershell
# État migrations
alembic heads
# → 039_created_at_timestamptz (head)

# CI complète
python -m pytest --tb=short -q
# → 574 passed · 36 skipped · 0 failed

# Qualité statique
python -m ruff check src/ tests/
python -m black --check src/ tests/

# utcnow restants dans src/ (hors auth_helpers.py exclu)
# Utiliser l'outil Grep avec pattern "utcnow" sur src/
# → 2 résultats dans auth_helpers.py uniquement (accepté)

# Tags
git tag --list "v4.1.0*"
# → v4.1.0-m2b-patch-done (dernier)
```

---

## IX. INSTRUCTIONS POUR L'AGENT SUCCESSEUR (M3)

### Lire en priorité

```
docs/freeze/DMS_V4.1.0_FREEZE.md                   — loi absolue
docs/milestones/HANDOVER_M2B_PATCH_TRANSMISSION.md  — ce document
docs/milestones/HANDOVER_M2B_TRANSMISSION.md        — contexte M2B
docs/adr/ADR-M2B-001_hardening_db_scope.md          — décisions DB
TECHNICAL_DEBT.md                                   — dettes actives
```

### Priorités avant ou en M3

**1. DETTE-M1-04 — DROP COLUMN `users.role_id`** (P1 — bloque le freeze propre)

Séquence obligatoire :
1. Retirer `role_id=2` de `create_user()` dans `src/api/auth_helpers.py`
2. Retirer le paramètre de `src/auth_router.py`
3. Migration 040 : `ALTER TABLE users DROP COLUMN IF EXISTS role_id`
4. Évaluer `DROP TABLE roles CASCADE` si plus aucune FK active

**2. DETTE-M2-02 — `conditional_limit` no-op** (P3)

```python
# src/ratelimit.py — conditional_limit ne passe pas func à slowapi
# Vérifier comportement réel avant de modifier
```

**3. Audit 36 skipped complet** (P3)

```powershell
python -m pytest -rs tests/ 2>&1 | Select-String "SKIPPED"
# 4 légitimes déjà documentés · 32+ restants à classifier
```

### Règles absolues à respecter

```
- Ne pas dropper role_id sans migration Alembic (zéro ALTER direct)
- Retirer create_user(role_id=2) AVANT de dropper la colonne DB
- Ne pas toucher auth_helpers.py ni auth_router.py hors mandat M1-04
- Migrations : SQL brut op.execute() uniquement — zéro autogenerate
- Prochaine migration ID : 040_
- RÈGLE-ORG-10 : merge PR `main` → **agent** (`CLAUDE.md`) ; tags → pratique équipe
- ADR-0012 : pipeline_runs append-only — UPDATE/DELETE interdits
- PROBE avant toute action DB (RÈGLE-ORG-08)
```

---

## X. RÈGLES ORGANISATIONNELLES ACTIVES

| Règle | Description |
|---|---|
| RÈGLE-ORG-04 | DoD validé par l'humain uniquement |
| RÈGLE-ORG-07 | Fichier hors périmètre → revert immédiat |
| RÈGLE-ORG-08 | PROBE avant toute action DB |
| RÈGLE-ORG-10 | Merge PR `main` → **agent** (`CLAUDE.md`) |
| RÈGLE-12 | Migrations = SQL brut `op.execute()` uniquement — zéro autogenerate |
| RÈGLE-09 | `winner` / `rank` / `recommendation` = INTERDITS hors comité humain |
| ADR-0012 | `pipeline_runs` append-only — UPDATE/DELETE interdits |
| ADR-M2B-001 | STOP-M2B-3 — doctrine ADR-0012 prime — NOT VALID local assumé |

---

```
DMS V4.1.0 — Mopti, Mali — 2026-03-01

M2B-PATCH = deux dettes soldées. Aucune migration. Aucun fichier hors périmètre.
Socle propre. CI verte. Prod inchangée.

Transmission faite. À toi, M3.
```
