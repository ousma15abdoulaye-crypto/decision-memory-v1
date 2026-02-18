# GUIDE RAPIDE — EXTRACTION DES LOGS PR #79

## 🎯 OBJECTIF
Extraire **TOUS** les logs de **TOUS** les checks de la PR #79 pour analyse complète.

---

## ⚡ MÉTHODE LA PLUS RAPIDE

### Étape 1 : Accéder à la PR
**URL :** https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/pull/79

### Étape 2 : Onglet "Checks"
1. Cliquer sur l'onglet **"Checks"** en haut de la PR
2. Vous verrez une liste de tous les workflows/jobs

### Étape 3 : Pour chaque check (même ceux qui passent)
1. **Cliquer sur le nom du workflow** (ex: "CI Freeze Integrity")
2. **Cliquer sur le job** (ex: "verify-freeze")
3. **Pour chaque step** :
   - Cliquer sur le step
   - Cliquer sur le bouton **"Copy"** (icône copier) en haut à droite
   - Coller dans un fichier texte séparé

---

## 📋 CHECKLIST DES WORKFLOWS À VÉRIFIER

Cocher chaque workflow une fois les logs extraits :

- [ ] **CI Freeze Integrity** (`verify-freeze`)
- [ ] **CI Lint (Ruff)** (`lint`)
- [ ] **CI Main** (`lint-and-test`)
- [ ] **CI Invariants** (`check-invariants`)
- [ ] **Regenerate Freeze Checksums** (`regenerate-checksums`)
- [ ] **Format Code with Black** (`format-check`)
- [ ] **CI Milestones Gates** (`verify-order`)

---

## 🔍 WORKFLOWS PRIORITAIRES (en échec probable)

Ces workflows sont probablement en échec et nécessitent une attention immédiate :

1. **CI Freeze Integrity** — Checksums ne correspondent pas
2. **CI Lint (Ruff)** — Erreurs de linting
3. **CI Main** — Tests ou linting échouent

---

## 📝 FORMAT DE SAUVEGARDE

Créer un fichier par workflow :

```
docs/audits/PR79_LOGS_CI_FREEZE_INTEGRITY.txt
docs/audits/PR79_LOGS_CI_LINT_RUFF.txt
docs/audits/PR79_LOGS_CI_MAIN.txt
docs/audits/PR79_LOGS_CI_INVARIANTS.txt
docs/audits/PR79_LOGS_REGENERATE_CHECKSUMS.txt
docs/audits/PR79_LOGS_FORMAT_BLACK.txt
docs/audits/PR79_LOGS_MILESTONES_GATES.txt
```

---

## 🚀 COMMANDES GITHUB CLI (Alternative)

Si vous avez `gh` installé :

```bash
# Se connecter
gh auth login

# Lister les runs pour la branche
gh run list --branch fix/audit-urgent --limit 20

# Pour chaque run, extraire les logs
gh run view <RUN_ID> --log > docs/audits/PR79_LOGS_RUN_<RUN_ID>.txt

# Ou pour un workflow spécifique
gh workflow view ci-freeze-integrity.yml
gh run list --workflow=ci-freeze-integrity.yml --branch fix/audit-urgent
gh run view <RUN_ID> --log
```

---

## ⚠️ IMPORTANT

- **Ne pas omettre** de logs, même s'ils semblent répétitifs
- **Inclure les erreurs** complètes avec stack traces
- **Inclure les sorties** de toutes les commandes
- **Sauvegarder immédiatement** après extraction (logs disponibles 90 jours)

---

**Une fois tous les logs extraits, les partager pour analyse complète.**
