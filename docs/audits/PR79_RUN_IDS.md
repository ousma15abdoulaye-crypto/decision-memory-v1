# RUN IDs — PR #79 — Derniers Workflows

**PR :** https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/pull/79  
**Branche :** `fix/audit-urgent`  
**Date :** 2026-02-18

---

## RUN IDs IDENTIFIÉS (Derniers)

### Run le plus récent (commit `8b720cc`)

1. **CI Main** — Run ID: `22140169803`
   - URL: https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/runs/22140169803
   - Durée: 50s
   - Branche: `fix/audit-urgent`

2. **CI Invariants** — Run ID: `22140169501`
   - URL: https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/runs/22140169501
   - Durée: 42s
   - Branche: `fix/audit-urgent`

3. **CI Milestones Gates** — Run ID: `22140169500`
   - URL: https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/runs/22140169500
   - Durée: 7s
   - Branche: `fix/audit-urgent`

4. **CI Lint (Ruff)** — Run ID: `22140169486`
   - URL: https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/runs/22140169486
   - Durée: 13s
   - Branche: `fix/audit-urgent`

5. **CI Freeze Integrity** — Run ID: `22140169478`
   - URL: https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/runs/22140169478
   - Durée: 6s
   - Branche: `fix/audit-urgent`

6. **Regenerate Freeze Checksums** — Run ID: `22140168216`
   - URL: https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/runs/22140168216
   - Durée: 10s
   - Branche: `fix/audit-urgent`

7. **Format Code with Black** — Run ID: `22140155886`
   - URL: https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/runs/22140155886
   - Durée: 12s
   - Branche: `fix/audit-urgent`

---

## COMMANDES GITHUB CLI POUR EXTRACTION

Si vous avez `gh` installé, utilisez ces commandes pour extraire les logs :

```bash
# Se connecter à GitHub
gh auth login

# Extraire les logs de chaque run
gh run view 22140169803 --log > docs/audits/PR79_LOGS_CI_MAIN_RUN_22140169803.txt
gh run view 22140169501 --log > docs/audits/PR79_LOGS_CI_INVARIANTS_RUN_22140169501.txt
gh run view 22140169500 --log > docs/audits/PR79_LOGS_MILESTONES_GATES_RUN_22140169500.txt
gh run view 22140169486 --log > docs/audits/PR79_LOGS_CI_LINT_RUFF_RUN_22140169486.txt
gh run view 22140169478 --log > docs/audits/PR79_LOGS_CI_FREEZE_INTEGRITY_RUN_22140169478.txt
gh run view 22140168216 --log > docs/audits/PR79_LOGS_REGENERATE_CHECKSUMS_RUN_22140168216.txt
gh run view 22140155886 --log > docs/audits/PR79_LOGS_FORMAT_BLACK_RUN_22140155886.txt
```

---

## ACCÈS DIRECT VIA NAVIGATEUR

Pour chaque run, accéder directement à l'URL et :
1. Cliquer sur le job (ex: "lint-and-test")
2. Cliquer sur chaque step
3. Copier tous les logs

---

## AUTRES RUNS RÉCENTS

### Commit `2e39916` (fix tests)

- **CI Lint (Ruff)** — Run ID: `22140155874`
- **Format Code with Black** — Run ID: `22140155886`
- **Regenerate Freeze Checksums** — Run ID: `22140155893`

### Commit `b8bdb4e` (docs ci)

- **CI Lint (Ruff)** — Run ID: `22140168247`
- **Regenerate Freeze Checksums** — Run ID: `22140168216`

---

**Note :** Les logs sont disponibles pendant 90 jours. Extraire rapidement pour analyse complète.
