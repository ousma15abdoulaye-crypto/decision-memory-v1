# EXTRACTION DES LOGS CI — PR #79

**PR :** https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/pull/79  
**Branche :** `fix/audit-urgent`  
**Date :** 2026-02-18

---

## WORKFLOWS À VÉRIFIER

### 1. CI Freeze Integrity
**Workflow :** `.github/workflows/ci-freeze-integrity.yml`  
**Job :** `verify-freeze`  
**URL :** https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/workflows/ci-freeze-integrity.yml

**Steps à vérifier :**
- `Verify freeze checksums` — Commande : `sha256sum -c docs/freeze/v3.3.2/SHA256SUMS.txt`

**Logs à extraire :**
- Sortie complète de `sha256sum -c`
- Code de sortie
- Erreurs éventuelles

---

### 2. CI Lint (Ruff)
**Workflow :** `.github/workflows/ci-lint-ruff.yml`  
**Job :** `lint`  
**URL :** https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/workflows/ci-lint-ruff.yml

**Steps à vérifier :**
- `Run Ruff check` — Commande : `ruff check src tests`
- `Run Ruff format check` — Commande : `ruff format --check src tests`

**Logs à extraire :**
- Sortie complète de `ruff check`
- Liste des erreurs/warnings
- Code de sortie

---

### 3. CI Main
**Workflow :** `.github/workflows/ci-main.yml`  
**Job :** `lint-and-test`  
**URL :** https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/workflows/ci-main.yml

**Steps à vérifier :**
- `Ruff check` — Commande : `ruff check src tests`
- `Black check` — Commande : `black --check src tests`
- `Python syntax check` — Commande : `python -m compileall src -q`
- `Run migrations` — Commande : `alembic upgrade head`
- `Run tests` — Commande : `pytest tests/ -v --cov=src --cov-report=xml --cov-fail-under=40`
- `Upload coverage`

**Logs à extraire :**
- Sortie de chaque step
- Erreurs de compilation Python
- Erreurs de migration Alembic
- Résultats des tests (passés/échoués)
- Couverture de code
- Code de sortie de chaque step

---

### 4. CI Invariants
**Workflow :** `.github/workflows/ci-invariants.yml`  
**Job :** `check-invariants`  
**URL :** https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/workflows/ci-invariants.yml

**Steps à vérifier :**
- `Check invariants gate` — Vérifie si `.milestones/M-CI-INVARIANTS.done` existe
- `Run invariants tests` — Commande : `pytest tests/invariants/ -v`

**Logs à extraire :**
- Statut du gate (actif/inactif)
- Résultats des tests invariants
- Tests passés/échoués
- Erreurs détaillées

---

### 5. Regenerate Freeze Checksums
**Workflow :** `.github/workflows/ci-regenerate-freeze-checksums.yml`  
**Job :** `regenerate-checksums`  
**URL :** https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/workflows/ci-regenerate-freeze-checksums.yml

**Steps à vérifier :**
- `Regenerate SHA256 checksums (Linux)` — Régénère les checksums
- `Verify checksums` — Vérifie les checksums régénérés
- `Commit updated checksums` — Committe automatiquement

**Logs à extraire :**
- Contenu du fichier SHA256SUMS.txt généré
- Résultat de la vérification
- Statut du commit automatique
- Erreurs éventuelles

---

### 6. Format Code with Black
**Workflow :** `.github/workflows/ci-format-black.yml`  
**Job :** `format-check`  
**URL :** https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/workflows/ci-format-black.yml

**Steps à vérifier :**
- `Check formatting` — Commande : `black --check src tests`
- `Format code (if check fails)` — Applique le formatage si échec

**Logs à extraire :**
- Liste des fichiers non formatés
- Diff du formatage appliqué
- Statut du commit automatique

---

## INSTRUCTIONS D'EXTRACTION

### Via GitHub Web Interface

1. **Accéder à la PR :**
   https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/pull/79

2. **Onglet "Checks" :**
   - Cliquer sur "Checks" en haut de la PR
   - Voir tous les workflows/jobs

3. **Pour chaque check :**
   - Cliquer sur le nom du workflow
   - Cliquer sur le job spécifique
   - Pour chaque step :
     - Cliquer sur le step
     - Copier TOUT le contenu du log (bouton "Copy" en haut à droite)
     - Coller dans un fichier séparé

### Via GitHub Actions

1. **Accéder à Actions :**
   https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions

2. **Filtrer par branche `fix/audit-urgent`**

3. **Pour chaque workflow :**
   - Cliquer sur le dernier run
   - Cliquer sur chaque job
   - Copier les logs de chaque step

---

## FORMAT D'EXPORT SOUHAITÉ

Pour chaque workflow, créer un fichier avec :

```
# WORKFLOW: [nom du workflow]
# JOB: [nom du job]
# DATE: [date d'exécution]
# STATUT: [success/failure/cancelled]

## Step: [nom du step]
[logs complets ici]

## Step: [nom du step suivant]
[logs complets ici]

...
```

---

## FICHIERS À CRÉER

1. `docs/audits/PR79_LOGS_CI_FREEZE_INTEGRITY.md`
2. `docs/audits/PR79_LOGS_CI_LINT_RUFF.md`
3. `docs/audits/PR79_LOGS_CI_MAIN.md`
4. `docs/audits/PR79_LOGS_CI_INVARIANTS.md`
5. `docs/audits/PR79_LOGS_REGENERATE_CHECKSUMS.md`
6. `docs/audits/PR79_LOGS_FORMAT_BLACK.md`

---

**Note :** Les logs GitHub Actions sont généralement disponibles pendant 90 jours. Assurez-vous de les extraire rapidement.
