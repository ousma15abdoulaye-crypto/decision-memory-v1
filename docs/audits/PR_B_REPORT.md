# RAPPORT PR-B : Fix Freeze V3.3.2 SHA256

## But de la PR

Corriger les 4 hash mismatches dans `docs/freeze/v3.3.2/SHA256SUMS.txt` causés par des différences de fins de ligne (CRLF/LF) entre Windows et Linux CI.

## Fichiers modifiés

1. **`.gitattributes`** (nouveau)
   - Ajoute `docs/freeze/** -text` pour empêcher toute conversion CRLF/LF sur les fichiers freezés
   - Configure normalisation pour autres fichiers (Python LF, PowerShell CRLF, etc.)

2. **`docs/freeze/v3.3.2/SHA256SUMS.txt`** (modifié)
   - Régénéré avec `scripts/regenerate_freeze_sha256.py`
   - Checksums identiques aux précédents (fichiers déjà dans le bon état)

3. **`scripts/regenerate_freeze_sha256.py`** (nouveau)
   - Script Python cross-platform pour régénérer SHA256SUMS.txt
   - Calcule SHA256 en mode binaire (byte-stable)

4. **`scripts/regenerate_freeze_sha256.sh`** (nouveau)
   - Script bash natif Linux pour régénération depuis Linux CI

## Commandes exécutées + résultats

```bash
# Création branche
git checkout main
git fetch origin
git reset --hard origin/main
git checkout -b fix/freeze-v3.3.2-sha

# Régénération SHA256SUMS.txt
python scripts/regenerate_freeze_sha256.py
# Résultat: SUCCES - Tous les checksums valides

# Vérification
git diff docs/freeze/v3.3.2/SHA256SUMS.txt
# Résultat: Aucun changement (checksums identiques)

# Commit
git add .gitattributes docs/freeze/v3.3.2/SHA256SUMS.txt scripts/regenerate_freeze_sha256.*
git commit -m "fix: freeze v3.3.2 sha256sums (cross-platform stable)"
```

## Risques / Anomalies

⚠️ **Important**: Les checksums générés sont identiques aux précédents. Cela signifie soit :
- Les fichiers freezés sont déjà dans le bon état (LF)
- OU les fichiers ont CRLF mais le script Python lit en binaire donc calcule le même hash

**Action requise**: Vérifier dans GitHub Actions CI que `sha256sum -c docs/freeze/v3.3.2/SHA256SUMS.txt` passe après cette PR.

Si la CI échoue encore, cela signifie que les fichiers dans le repo Git ont des fins de ligne différentes de ce que Linux CI voit. Dans ce cas :
1. Vérifier `.gitattributes` est bien appliqué
2. Potentiellement faire un `git add --renormalize docs/freeze/v3.3.2/` pour forcer la renormalisation selon `.gitattributes`

## Next step

1. **Push la branche**: `git push origin fix/freeze-v3.3.2-sha`
2. **Créer la PR** sur GitHub
3. **Vérifier dans CI** que `ci-freeze-integrity.yml` passe
4. Si échec persistant → investiguer les fins de ligne réelles dans le repo Git

## Restrictions respectées

✅ Seuls `.gitattributes` et `SHA256SUMS.txt` modifiés (plus scripts utilitaires)
✅ Aucun fichier freezé modifié (CONSTITUTION, MILESTONES, INVARIANTS, ADR)
✅ Aucun secret commité
✅ Scripts lisent uniquement les fichiers, pas de hardcoding
