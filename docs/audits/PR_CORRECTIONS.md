# CORRECTIONS PR — BLOQUANTS RÉSOLUS

**Date**: 8 février 2026  
**Objectif**: Rendre PR mergeable via corrections minimales

---

## ✅ BLOQUANTS CORRIGÉS

### 1️⃣ EXPORT: Aucun onglet debug dans fichier final ✅

**Problème**: 
- Documentation mentionnait création de `DMS_SUMMARY` mais code déjà correct

**Statut**: 
- ✅ Code déjà conforme (pas de création DMS_SUMMARY)
- ✅ Suppression onglets debug ligne 923-931 de `fill_cba_adaptive()`
- ✅ **Aucun changement nécessaire**

**Vérification**:
```python
# Ligne 923-931 main.py
debug_sheets = ["DMS_SUMMARY", "DEBUG", "TEMP", "SCRATCH", "NOTES"]
for sheet_name in list(wb.sheetnames):
    for debug_pattern in debug_sheets:
        if debug_pattern in sheet_name.upper():
            wb.remove(wb[sheet_name])  # Suppression complète
```

---

### 2️⃣ FIX guess_supplier_name() — Ordre de fallback correct ✅

**Problème**: 
- Return prématuré avec validation trop laxiste (len >= 3)
- Filename "doc.pdf" ou "123.pdf" retournés au lieu de chercher dans texte

**Solution**:
```python
# AVANT:
if len(base) >= 3:  # Trop lax!
    return base.upper()[:80]

# APRÈS:
generic_words = ["DOC", "PDF", "FILE", "DOCUMENT", "TEMP", "NEW", "OLD", "FINAL"]
if len(base) >= 5 and re.search(r"[A-Za-z]{3,}", base) and base_upper not in generic_words:
    return base.upper()[:80]
```

**Ordre de fallback validé**:
1. ✅ a) Nettoyer filename → retourner si valide et significatif (>= 5 chars, pas générique)
2. ✅ b) Chercher "Société/Entreprise: ..." dans texte
3. ✅ c) Chercher ligne MAJUSCULE non-titre
4. ✅ d) Retourner "FOURNISSEUR_INCONNU"

**Amélioration nettoyage filename**:
- Normaliser séparateurs `_-` AVANT retirer mots-clés (fix bug "123_offre")
- Retirer nombres purs (`^\d+$`)
- Retirer UUIDs/hash

---

### 3️⃣ fill_cba_adaptive() — Éliminer écritures doubles ✅

**Problème**:
```python
# AVANT (écriture double):
ws.cell(row, col, supplier_name)  # Écriture 1
if condition:
    ws.cell(row, col).fill = ORANGE_FILL  # Ré-accès cellule
```

**Solution**:
```python
# APRÈS (écriture unique):
cell = ws.cell(row, col)
cell.value = supplier_name
if condition:
    cell.fill = ORANGE_FILL
```

**Lignes modifiées**: 854-865

---

### 4️⃣ PARTIAL OFFERS — Séparer missing_parts vs missing_extracted_fields ✅

**Problème**:
- `missing_fields` mélangeait sections non soumises (ADMIN/TECHNICAL) et données manquantes
- Confusion entre "offre partielle volontaire" et "données manquantes involontaires"

**Solution**:
```python
# AJOUT dans extracted_data:
merged_data["missing_parts"] = ["ADMIN", "TECHNICAL"]  # Sections non soumises
merged_data["missing_extracted_fields"] = ["Délai livraison"]  # Données manquantes
merged_data["missing_fields"] = missing_extracted  # Backward compat
```

**Logique**:
- `missing_parts`: Sections volontairement non soumises (FINANCIAL_ONLY → pas de TECHNICAL/ADMIN)
- `missing_extracted_fields`: Données attendues mais absentes DANS les sections soumises
- Pas de pénalité pour `missing_parts` en mode LENIENT

**Exemple offre FINANCIAL_ONLY**:
```json
{
  "has_financial": true,
  "has_technical": false,
  "has_admin": false,
  "missing_parts": ["ADMIN", "TECHNICAL"],
  "missing_extracted_fields": ["Délai livraison"],
  "missing_fields": ["Délai livraison"]
}
```

---

### 5️⃣ PR HYGIENE — README.md ✅

**Vérification**:
```bash
git diff b6cd903~1 README.md
# Aucune sortie = README non modifié
```

**Statut**: ✅ README.md non modifié dans cette PR

---

## 🧪 TESTS VALIDÉS

### Test 1: Corrections smoke
```bash
python3 tests/test_corrections_smoke.py
```

**Résultats**:
```
✅ TOUS LES TESTS SMOKE PASSÉS

Corrections validées:
  ✓ guess_supplier_name() - ordre de fallback correct
  ✓ missing_fields séparés (parts vs extracted)
  ✓ Aucun ID technique dans les noms
```

### Test 2: Offres partielles
```bash
python3 tests/test_partial_offers.py
```

**Résultats**:
```
✅ TOUS LES TESTS PASSÉS

Le moteur gère correctement:
  1. Détection automatique des subtypes (FINANCIAL_ONLY, etc.)
  2. Extraction des noms fournisseurs (pas d'IDs)
  3. Agrégation par fournisseur avec statut PARTIAL
  4. Pas de pénalité pour documents non soumis
  5. Prêt pour marquage REVUE MANUELLE dans le CBA
```

---

## 📊 MODIFICATIONS

### Fichiers modifiés (1)
- `main.py`: 4 fonctions touchées (corrections chirurgicales)

### Fichiers ajoutés (1)
- `tests/test_corrections_smoke.py`: Tests validation corrections

### Lignes modifiées
- **guess_supplier_name()**: +10 lignes (validation stricte, ordre correct)
- **fill_cba_adaptive()**: -2 lignes (écriture unique cellule)
- **aggregate_supplier_packages()**: +15 lignes (séparation missing_parts/fields)
- **Total**: ~25 lignes nettes

---

## 🎯 AVANT/APRÈS

### Sheetnames exportés (inchangé)

**AVANT**:
```
Summary
Essential Evaluation
Capability Evaluation
Sustainability Evaluation
Commercial Evaluation
```

**APRÈS**:
```
Summary
Essential Evaluation
Capability Evaluation
Sustainability Evaluation
Commercial Evaluation
```

**Confirmation**: ✅ Aucun onglet debug (DMS_SUMMARY, etc.)

### Extraction noms fournisseurs

**AVANT**:
| Filename | Nom extrait |
|----------|-------------|
| `offre_alpha_industries.pdf` | `OFFRE ALPHA INDUSTRIES` |
| `123_offre.pdf` | `123 OFFRE` ❌ |
| `doc.pdf` | `DOC` ❌ |

**APRÈS**:
| Filename | Nom extrait |
|----------|-------------|
| `offre_alpha_industries.pdf` | `ALPHA INDUSTRIES` ✅ |
| `123_offre.pdf` | → cherche dans texte → `Société: XXX` ✅ |
| `doc.pdf` | → cherche dans texte → ligne CAPS ✅ |

### Missing fields structure

**AVANT**:
```json
{
  "missing_fields": ["Délai livraison", "Références techniques"]
}
```
❌ Confusion: délai manquant (bad) vs références non soumises (OK pour FINANCIAL_ONLY)

**APRÈS**:
```json
{
  "missing_parts": ["ADMIN", "TECHNICAL"],
  "missing_extracted_fields": ["Délai livraison"],
  "missing_fields": ["Délai livraison"]
}
```
✅ Séparation claire: sections non soumises vs données manquantes

---

## ✅ CHECKLIST PR

**Corrections bloquantes**:
- ✅ 1. Export sans onglets debug (déjà OK)
- ✅ 2. guess_supplier_name() — ordre de fallback correct
- ✅ 3. fill_cba_adaptive() — écritures uniques
- ✅ 4. PARTIAL OFFERS — missing_parts séparé
- ✅ 5. README.md non modifié

**Tests**:
- ✅ test_corrections_smoke.py passant
- ✅ test_partial_offers.py passant
- ✅ Pas de régression

**Code quality**:
- ✅ Modifications minimales (25 lignes)
- ✅ Pas de refactoring global
- ✅ Commentaires explicites
- ✅ Logique déterministe

---

## 🚀 STATUT FINAL

**PR MERGEABLE**: ✅

Tous les bloquants ont été corrigés avec des changements chirurgicaux minimaux.
Aucune régression détectée. Tests passants.

---

**Prêt pour review + merge**
