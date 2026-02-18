# LOGS COMPLETS — PR #79 — TEMPLATE D'EXTRACTION

**PR :** https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/pull/79  
**Branche :** `fix/audit-urgent`  
**Dernier commit :** `8b720cc`  
**Date extraction :** [À COMPLÉTER]

---

## INSTRUCTIONS

1. Aller sur : https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/pull/79
2. Cliquer sur l'onglet **"Checks"** en haut de la PR
3. Pour chaque workflow/job listé ci-dessous, copier TOUS les logs

---

## WORKFLOW 1 : CI Freeze Integrity

**URL directe :** https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/workflows/ci-freeze-integrity.yml

### Job: verify-freeze

#### Step: Verify freeze checksums
**Commande :** `sha256sum -c docs/freeze/v3.3.2/SHA256SUMS.txt`

**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP]
```

#### Step: Report status
**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP]
```

---

## WORKFLOW 2 : CI Lint (Ruff)

**URL directe :** https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/workflows/ci-lint-ruff.yml

### Job: lint

#### Step: Set up Python 3.11
**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP]
```

#### Step: Install Ruff
**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP]
```

#### Step: Run Ruff check
**Commande :** `ruff check src tests`

**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP - IMPORTANT : TOUTES LES ERREURS]
```

#### Step: Run Ruff format check
**Commande :** `ruff format --check src tests`

**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP]
```

---

## WORKFLOW 3 : CI Main

**URL directe :** https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/workflows/ci-main.yml

### Job: lint-and-test

#### Step: Set up Python 3.11
**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP]
```

#### Step: Install dependencies
**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP]
```

#### Step: Install linting tools
**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP]
```

#### Step: Ruff check
**Commande :** `ruff check src tests`

**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP - IMPORTANT]
```

#### Step: Black check
**Commande :** `black --check src tests`

**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP - IMPORTANT]
```

#### Step: Python syntax check
**Commande :** `python -m compileall src -q`

**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP]
```

#### Step: Run migrations
**Commande :** `alembic upgrade head`

**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP - IMPORTANT]
```

#### Step: Run tests
**Commande :** `pytest tests/ -v --cov=src --cov-report=xml --cov-fail-under=40`

**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP - TRÈS IMPORTANT : TOUS LES TESTS]
```

#### Step: Upload coverage
**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP]
```

---

## WORKFLOW 4 : CI Invariants

**URL directe :** https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/workflows/ci-invariants.yml

### Job: check-invariants

#### Step: Check invariants gate
**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP]
```

#### Step: Run invariants tests
**Commande :** `pytest tests/invariants/ -v`

**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP - IMPORTANT : TOUS LES TESTS INVARIANTS]
```

---

## WORKFLOW 5 : Regenerate Freeze Checksums

**URL directe :** https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/workflows/ci-regenerate-freeze-checksums.yml

### Job: regenerate-checksums

#### Step: Regenerate SHA256 checksums (Linux)
**Commande :** `cd docs/freeze/v3.3.2 && find . -type f \( -name "*.md" -o -name "*.txt" \) ! -name "SHA256SUMS.txt" | sort | xargs sha256sum > SHA256SUMS.txt`

**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP - IMPORTANT : CONTENU DU FICHIER GÉNÉRÉ]
```

#### Step: Verify checksums
**Commande :** `sha256sum -c docs/freeze/v3.3.2/SHA256SUMS.txt`

**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP]
```

#### Step: Commit updated checksums
**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP]
```

---

## WORKFLOW 6 : Format Code with Black

**URL directe :** https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/workflows/ci-format-black.yml

### Job: format-check

#### Step: Set up Python 3.11
**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP]
```

#### Step: Install Black
**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP]
```

#### Step: Check formatting
**Commande :** `black --check src tests`

**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP - IMPORTANT]
```

#### Step: Format code (if check fails)
**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP]
```

---

## WORKFLOW 7 : CI Milestones Gates

**URL directe :** https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/workflows/ci-milestones-gates.yml

### Job: verify-order

#### Step: Check milestone order
**LOGS À COPIER ICI :**
```
[COLLER TOUS LES LOGS DE CE STEP]
```

---

## MÉTHODE RAPIDE D'EXTRACTION

### Option 1 : Via l'onglet Checks de la PR

1. Aller sur : https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/pull/79/checks
2. Pour chaque workflow en échec (rouge) :
   - Cliquer sur le nom du workflow
   - Cliquer sur le job
   - Pour chaque step :
     - Cliquer sur le step
     - Cliquer sur le bouton "Copy" en haut à droite du log
     - Coller dans ce fichier à l'emplacement approprié

### Option 2 : Via GitHub Actions

1. Aller sur : https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions
2. Filtrer par branche : `fix/audit-urgent`
3. Pour chaque workflow :
   - Cliquer sur le dernier run
   - Cliquer sur chaque job
   - Copier les logs de chaque step

### Option 3 : Via GitHub CLI (si installé)

```bash
# Lister tous les runs pour la branche
gh run list --branch fix/audit-urgent --limit 10

# Pour chaque run ID, extraire les logs
gh run view <RUN_ID> --log > logs_run_<RUN_ID>.txt
```

---

## NOTES IMPORTANTES

- **Copier TOUT** : Ne pas omettre de lignes, même si elles semblent répétitives
- **Inclure les erreurs** : Les messages d'erreur sont cruciaux pour le diagnostic
- **Inclure les timestamps** : Si disponibles dans les logs
- **Inclure les codes de sortie** : Les codes de sortie des commandes sont importants

---

**Une fois tous les logs copiés, sauvegarder ce fichier et le partager pour analyse.**
