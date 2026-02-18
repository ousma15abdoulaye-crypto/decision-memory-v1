# PLAN D'ACTION — CORRECTIFS CI PR #79
**Date :** 2026-02-18  
**Branche :** `fix/audit-urgent`

---

## ✅ CORRECTIFS APPLIQUÉS

### 1. Workflow Freeze Checksums
- ✅ **Modifié :** `.github/workflows/ci-regenerate-freeze-checksums.yml`
- ✅ **Changement :** Supprimé le filtre `paths` pour déclencher sur tous les pushes vers `fix/audit-urgent`
- ✅ **Raison :** Le workflow ne se déclenchait pas car aucun fichier freeze n'avait changé

### 2. Tests Invariants
- ✅ **Corrigé :** Imports `os` redondants dans `test_inv_02_couche_a_primacy.py` et `test_inv_04_online_only.py`
- ✅ **Raison :** Éviter les warnings de linting

### 3. Ruff Configuration
- ✅ **Corrigé :** Supprimé règle inconnue `W503` de `pyproject.toml`
- ✅ **Commit :** `fix(ci): correct Ruff config and improve freeze checksums workflow`

---

## ⏳ ACTIONS EN ATTENTE — CI

### Workflow Freeze Checksums
Le workflow `ci-regenerate-freeze-checksums.yml` devrait maintenant :
1. ✅ Se déclencher automatiquement sur le prochain push
2. ⏳ Régénérer les checksums SHA256 sous Linux
3. ⏳ Committer automatiquement le fichier `SHA256SUMS.txt` mis à jour
4. ⏳ Re-déclencher les autres workflows CI

**Surveillance :** Vérifier GitHub Actions après le push

### Si le workflow ne se déclenche pas automatiquement
**Option manuelle :**
1. Aller sur GitHub Actions
2. Sélectionner workflow "Regenerate Freeze Checksums"
3. Cliquer "Run workflow" → sélectionner branche `fix/audit-urgent`
4. Exécuter

---

## 📋 PROBLÈMES RESTANTS À RÉSOUDRE (après régénération checksums)

### 1. Ruff Lint
- **Action :** Le workflow CI devrait appliquer `ruff check --fix` automatiquement
- **Si échec :** Analyser les logs et corriger manuellement les erreurs non auto-fixables

### 2. Black Formatting
- **Action :** Le workflow `ci-format-black.yml` devrait appliquer automatiquement le formatage
- **Si échec :** Vérifier les logs et appliquer manuellement si nécessaire

### 3. Tests Unitaires
- **Action :** Analyser les logs CI pour identifier les tests en échec
- **Correction :** Ajuster le code ou les tests selon la logique attendue

---

## 🎯 PROCHAINES ÉTAPES

1. ✅ **Pousser les changements** → FAIT
2. ⏳ **Surveiller CI** pour vérifier que le workflow freeze checksums se déclenche
3. ⏳ **Attendre régénération checksums** (automatique ou manuelle)
4. ⏳ **Analyser les autres échecs CI** une fois les checksums corrigés
5. ⏳ **Corriger les erreurs restantes** (Ruff, Black, tests)

---

## 📝 NOTES

- Les checksums doivent être régénérés sous **Linux** pour éviter les différences CRLF/LF
- Le workflow devrait maintenant se déclencher sur **tous** les pushes vers `fix/audit-urgent`
- Une fois les checksums régénérés, les autres workflows CI devraient repasser automatiquement

---

**Statut actuel :** En attente d'exécution CI pour régénération checksums
