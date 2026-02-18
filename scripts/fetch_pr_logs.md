# Instructions pour extraire les logs CI de la PR #79

## Méthode 1 : Via GitHub Web Interface

1. **Aller sur la PR :**
   https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/pull/79

2. **Onglet "Checks" :**
   - Cliquer sur l'onglet "Checks" en haut de la PR
   - Vous verrez tous les workflows/jobs exécutés

3. **Pour chaque check en échec :**
   - Cliquer sur le nom du check (ex: "CI Freeze Integrity / verify-freeze")
   - Cliquer sur le job spécifique (ex: "verify-freeze")
   - Cliquer sur chaque step pour voir les logs détaillés
   - Copier tout le contenu de chaque log

## Méthode 2 : Via GitHub Actions

1. **Aller sur Actions :**
   https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions

2. **Filtrer par branche :**
   - Sélectionner la branche `fix/audit-urgent`
   - Trouver le dernier run

3. **Pour chaque workflow :**
   - Cliquer sur le workflow
   - Cliquer sur chaque job
   - Cliquer sur chaque step pour voir les logs

## Workflows à vérifier

1. **CI Freeze Integrity** (`ci-freeze-integrity.yml`)
   - Job: `verify-freeze`
   - Step: "Verify freeze checksums"

2. **CI Lint (Ruff)** (`ci-lint-ruff.yml`)
   - Job: `lint`
   - Steps: "Run Ruff check", "Run Ruff format check"

3. **CI Main** (`ci-main.yml`)
   - Job: `lint-and-test`
   - Steps: "Ruff check", "Black check", "Python syntax check", "Run migrations", "Run tests"

4. **CI Invariants** (`ci-invariants.yml`)
   - Job: `check-invariants`
   - Steps: "Check invariants gate", "Run invariants tests"

5. **Regenerate Freeze Checksums** (`ci-regenerate-freeze-checksums.yml`)
   - Job: `regenerate-checksums`
   - Steps: "Regenerate SHA256 checksums", "Verify checksums", "Commit updated checksums"

6. **Format Code with Black** (`ci-format-black.yml`)
   - Job: `format-check`
   - Steps: "Check formatting", "Format code"

## Commande GitHub CLI (si installé)

```bash
gh pr checks 79 --json name,conclusion,detailsUrl
gh run view <run-id> --log
```

## Export des logs

Pour chaque check, copier :
- Le nom du workflow
- Le nom du job
- Le nom du step
- La sortie complète (stdout + stderr)
- Le code de sortie
