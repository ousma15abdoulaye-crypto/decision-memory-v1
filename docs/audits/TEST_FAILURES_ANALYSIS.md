# ANALYSE DES ÉCHECS DE TESTS – PR #79
**Date :** 2026-02-18  
**Branche :** `fix/audit-urgent`

---

## 🔍 DIAGNOSTIC

### Problème identifié
Les tests échouent en CI car la variable d'environnement `TESTING` n'était pas définie dans les workflows GitHub Actions.

### Impact
- Rate limiting activé en mode test (devrait être désactivé)
- Tests de rate limiting échouent (attendu car rate limiting désactivé en TESTING)
- Configuration incohérente entre local et CI

---

## ✅ CORRECTIFS APPLIQUÉS

### 1. Ajout de `TESTING=true` dans `ci-main.yml`
```yaml
- name: Run tests
  env:
    DATABASE_URL: postgresql+psycopg://postgres:testpass@localhost:5432/dmstest
    TESTING: "true"  # ✅ Ajouté
  run: pytest tests/ -v --cov=src --cov-report=xml --cov-fail-under=40
```

### 2. Ajout de `TESTING=true` dans `ci-invariants.yml`
```yaml
- name: Run invariants tests
  if: steps.gate.outputs.active == 'true'
  env:
    DATABASE_URL: postgresql+psycopg://postgres:testpass@localhost:5432/dmstest
    TESTING: "true"  # ✅ Ajouté
  run: pytest tests/invariants/ -v
```

---

## 📊 TESTS CONNUS À ÉCHOUER (NON-BLOQUANTS)

D'après la documentation existante, 3 tests sont connus pour échouer dans certains cas (non-bloquants) :

### 1. `test_upload_offer_with_lot_id`
- **Statut** : ✅ Déjà skippé avec `@pytest.mark.skip`
- **Raison** : Table `lots` pas encore implémentée (planifiée pour M3A)
- **Impact** : Aucun (test skippé)

### 2. `test_rate_limit_upload`
- **Statut** : ✅ Déjà skippé avec `@pytest.mark.skip`
- **Raison** : Rate limiting désactivé en mode TESTING
- **Impact** : Aucun (test skippé, alternative `test_rate_limit_upload_real` existe)

### 3. `test_case_quota_enforcement`
- **Statut** : ⚠️ Test corrigé (utilise maintenant 40MB au lieu de 100MB)
- **Raison** : Test utilisait 100MB alors que limite = 50MB par fichier
- **Impact** : Test devrait maintenant passer

---

## 🎯 RÉSULTAT ATTENDU

Avec `TESTING=true` ajouté :
- ✅ Rate limiting désactivé en mode test (comportement attendu)
- ✅ Tests de rate limiting skippés ou passent avec alternative
- ✅ Configuration cohérente entre local et CI
- ✅ Tests devraient passer (sauf les 2 tests skippés intentionnellement)

---

## 📝 COMMITS

- `deeada6` : fix(ci): add TESTING environment variable for tests
- `[suivant]` : fix(ci): add TESTING env var to invariants workflow

---

**Statut :** ✅ **CORRECTIFS APPLIQUÉS** - La CI devrait maintenant passer avec `TESTING=true` défini.
