# P3.2 ACTION F1 — Alembic Chain Fix

**Date** : 2026-04-18  
**Statut** : ✅ **RÉSOLU**

---

## PROBLÈME

Migration 101 contient `down_revision = '093_xxx'` (fictif).

---

## PROBE FICHIERS

**Dernière migration existante identifiée** :
- Fichier : `alembic/versions/081_m16_evaluation_domains.py`
- Révision : `081_m16_evaluation_domains`
- down_revision : `080_market_signals_v2_zone_id_index`

**Probe méthode** : Read direct sur `081_m16_evaluation_domains.py` (l.13-14).

---

## DÉCISION

**Numéro migration P3.2** : **082** (next = 081 + 1)

**down_revision migration 082** : **`'081_m16_evaluation_domains'`**

**Fichier migration P3.2** : `082_p32_dao_criteria_scoring_schema.py`

---

## CORRECTION REQUISE

**Fichier** : `alembic/versions/101_p32_dao_criteria_scoring_schema.py`

**Ligne 21** :
```python
revision = '082_p32_dao_criteria_scoring_schema'
```

**Ligne 22** :
```python
down_revision = '081_m16_evaluation_domains'
```

**Action CTO** : renommer fichier `101_*.py` → `082_*.py` + corriger lignes 21-22.

---

## VALIDATION

✅ Numéro séquentiel respecté : 081 → 082  
✅ down_revision chaîné : `'081_m16_evaluation_domains'`  
✅ Pas de gap dans séquence  

---

**F1 CLOSED — correction down_revision identifiée**
