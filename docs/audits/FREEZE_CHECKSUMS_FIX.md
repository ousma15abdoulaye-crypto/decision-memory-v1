# CORRECTION CHECKSUMS FREEZE — INSTRUCTIONS

## Problème identifié

Les checksums SHA256 dans `docs/freeze/v3.3.2/SHA256SUMS.txt` ne correspondent pas car générés sous Windows (CRLF) au lieu de Linux (LF).

## Solution automatique (recommandée)

Le workflow `ci-regenerate-freeze-checksums.yml` devrait automatiquement régénérer les checksums lors du prochain push sur `fix/audit-urgent` et les committer.

**Vérification :** Après le push, surveiller le workflow `ci-regenerate-freeze-checksums` dans GitHub Actions.

## Solution manuelle (si workflow ne fonctionne pas)

### Option 1 : GitHub Codespaces (recommandé)

1. Allez sur https://github.com/ousma15abdoulaye-crypto/decision-memory-v1
2. Branche `fix/audit-urgent`
3. Cliquez sur `Code` → `Codespaces` → `Create codespace on fix/audit-urgent`
4. Dans le terminal du Codespace :
   ```bash
   cd docs/freeze/v3.3.2
   find . -type f \( -name '*.md' -o -name '*.txt' \) ! -name SHA256SUMS.txt | sort | xargs sha256sum > SHA256SUMS.txt
   cd ../../..
   git add docs/freeze/v3.3.2/SHA256SUMS.txt
   git commit -m "fix(freeze): regenerate SHA256SUMS.txt on Linux"
   git push origin fix/audit-urgent
   ```

### Option 2 : Docker (Windows)

```powershell
docker run --rm -v ${PWD}:/workspace -w /workspace alpine:latest sh -c "apk add coreutils && cd docs/freeze/v3.3.2 && find . -type f \( -name '*.md' -o -name '*.txt' \) ! -name SHA256SUMS.txt | sort | xargs sha256sum > SHA256SUMS.txt"
git add docs/freeze/v3.3.2/SHA256SUMS.txt
git commit -m "fix(freeze): regenerate SHA256SUMS.txt on Linux via Docker"
git push origin fix/audit-urgent
```

## Fichiers concernés

Les checksums doivent être régénérés pour :
- `docs/freeze/v3.3.2/CONSTITUTION_DMS_V3.3.2.md`
- `docs/freeze/v3.3.2/MILESTONES_EXECUTION_PLAN_V3.3.2.md`
- `docs/freeze/v3.3.2/INVARIANTS.md`
- `docs/freeze/v3.3.2/adrs/ADR-0001.md`

## Vérification

Après régénération, vérifier :
```bash
cd docs/freeze/v3.3.2
sha256sum -c SHA256SUMS.txt
```

Tous les fichiers doivent afficher `OK`.
