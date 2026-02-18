# GUIDE COMPLET — EXTRACTION LOGS PR #79

**PR :** https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/pull/79  
**Branche :** `fix/audit-urgent`  
**Dernier commit :** `8b720cc`

---

## ⚡ MÉTHODE LA PLUS RAPIDE

### Via l'onglet "Checks" de la PR

1. **Aller sur :** https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/pull/79
2. **Cliquer sur l'onglet "Checks"** en haut de la PR
3. **Pour chaque workflow/job** (même ceux qui passent) :
   - Cliquer sur le nom du workflow
   - Cliquer sur le job
   - Pour chaque step :
     - Cliquer sur le step
     - Cliquer sur le bouton **"Copy"** (icône copier) en haut à droite
     - Coller dans un fichier texte

---

## 📋 WORKFLOWS À EXTRAIRE (7 workflows)

### ✅ Checklist

- [ ] **CI Freeze Integrity** (Run ID: `22140169478`) — ❌ ÉCHEC
- [ ] **CI Lint (Ruff)** (Run ID: `22140169486`) — ❌ ÉCHEC  
- [ ] **CI Main** (Run ID: `22140169803`) — ❌ ÉCHEC
- [ ] **CI Invariants** (Run ID: `22140169501`)
- [ ] **CI Milestones Gates** (Run ID: `22140169500`)
- [ ] **Regenerate Freeze Checksums** (Run ID: `22140168216`)
- [ ] **Format Code with Black** (Run ID: `22140155886`)

---

## 🔗 URLs DIRECTES DES RUNS

### Workflows en échec (priorité haute)

1. **CI Freeze Integrity**
   - Run: https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/runs/22140169478
   - Job: `verify-freeze`
   - Step à vérifier: "Verify freeze checksums"

2. **CI Lint (Ruff)**
   - Run: https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/runs/22140169486
   - Job: `lint`
   - Steps à vérifier: "Run Ruff check", "Run Ruff format check"

3. **CI Main**
   - Run: https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/runs/22140169803
   - Job: `lint-and-test`
   - Steps à vérifier: "Ruff check", "Black check", "Run migrations", "Run tests"

### Autres workflows

4. **CI Invariants**
   - Run: https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/runs/22140169501

5. **CI Milestones Gates**
   - Run: https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/runs/22140169500

6. **Regenerate Freeze Checksums**
   - Run: https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/runs/22140168216

7. **Format Code with Black**
   - Run: https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/actions/runs/22140155886

---

## 📝 FORMAT DE SAUVEGARDE RECOMMANDÉ

Créer un fichier par workflow dans `docs/audits/PR79_LOGS/` :

```
docs/audits/PR79_LOGS/
├── PR79_LOGS_CI_FREEZE_INTEGRITY.txt
├── PR79_LOGS_CI_LINT_RUFF.txt
├── PR79_LOGS_CI_MAIN.txt
├── PR79_LOGS_CI_INVARIANTS.txt
├── PR79_LOGS_MILESTONES_GATES.txt
├── PR79_LOGS_REGENERATE_CHECKSUMS.txt
└── PR79_LOGS_FORMAT_BLACK.txt
```

---

## 🚀 OPTION AUTOMATIQUE : Script PowerShell

Si vous installez GitHub CLI (`gh`), exécutez :

```powershell
.\scripts\extract_pr79_logs.ps1
```

Le script extraira automatiquement tous les logs dans `docs/audits/PR79_LOGS/`.

**Installation GitHub CLI :**
- Télécharger depuis : https://cli.github.com/
- Ou via winget : `winget install GitHub.cli`

---

## 📖 GUIDES DÉTAILLÉS CRÉÉS

1. **`docs/audits/PR79_QUICK_EXTRACTION_GUIDE.md`** — Guide rapide
2. **`docs/audits/PR79_ALL_LOGS_TEMPLATE.md`** — Template complet avec sections pour chaque workflow
3. **`docs/audits/PR79_LOGS_EXTRACTION.md`** — Instructions détaillées
4. **`docs/audits/PR79_RUN_IDS.md`** — Liste des run IDs identifiés
5. **`scripts/extract_pr79_logs.ps1`** — Script PowerShell d'extraction automatique

---

## ⚠️ IMPORTANT

- **Copier TOUT** : Ne pas omettre de lignes
- **Inclure les erreurs** : Messages d'erreur complets avec stack traces
- **Inclure les sorties** : Toutes les sorties de commandes
- **Sauvegarder rapidement** : Logs disponibles 90 jours seulement

---

## 🎯 PROCHAINES ÉTAPES

1. ✅ Guides créés
2. ✅ Run IDs identifiés
3. ⏳ **VOUS :** Extraire les logs via l'interface web ou le script PowerShell
4. ⏳ **VOUS :** Sauvegarder les logs dans `docs/audits/PR79_LOGS/`
5. ⏳ **MOI :** Analyser les logs une fois extraits

---

**Une fois les logs extraits, partagez-les pour analyse complète et correction des problèmes.**
