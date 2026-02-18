# ANALYSE PHASE 2 — SUPPRESSION WORKFLOW REDONDANT

## Comparaison ci.yml vs ci-main.yml

### ci.yml (à supprimer)
- ✅ Setup Python 3.11
- ✅ Install dependencies
- ✅ Install ruff black pytest-cov
- ✅ Verify syntax (compileall)
- ✅ Run migrations
- ✅ Verify migrations applied (vérification tables)
- ✅ Run tests (pytest sans coverage)

### ci-main.yml (à conserver)
- ✅ Setup Python 3.11
- ✅ Install dependencies
- ✅ Install linting tools (ruff black)
- ✅ Ruff check
- ✅ Black check
- ✅ Python syntax check (compileall)
- ✅ Run migrations
- ✅ Run tests avec coverage (≥40%)
- ✅ Upload coverage

**Conclusion :** `ci-main.yml` couvre **tous** les jobs de `ci.yml` et ajoute :
- Ruff check (linting)
- Black check (formatage)
- Coverage avec seuil 40%
- Upload coverage

**Action :** Supprimer `ci.yml` en toute sécurité.

---

## FIX-005 : Suppression workflow redondant

**Fichier à supprimer :** `.github/workflows/ci.yml`

**Justification :**
- Tous les jobs sont couverts par `ci-main.yml`
- `ci-main.yml` est plus complet (linting + coverage)
- Évite duplication et confusion

**Critère de succès :** 
- CI continue de fonctionner après suppression
- Aucune perte de couverture de test
