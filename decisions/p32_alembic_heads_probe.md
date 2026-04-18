# P3.2 ÉTAPE A — Probe Alembic Heads

**Date** : 2026-04-18  
**Statut** : ✅ **CAUSE RACINE IDENTIFIÉE**

---

## NOMBRE DE HEADS

**Commande attendue** : `alembic heads`

**Résultat attendu** : 2 heads (multiple heads détecté)

**Preuve** : lecture directe fichiers alembic/versions/

---

## CHAÎNE MIGRATION RÉELLE

### Fichiers migrations (ordre numérique)

```
098_primary_admin_email_owner_mandate.py
099_fix_admin_roles_seed.py
100_process_workspaces_zip_r2.py
101_p32_dao_criteria_scoring_schema.py
```

**Fichier parasite détecté** :
```
082_p32_dao_criteria_scoring_schema.py  ← CRÉÉ PAR ERREUR
```

---

## EXTRACTION REVISION + DOWN_REVISION

### Chaîne 098 → 099 → 100 → 101 (légitime)

| Fichier | revision | down_revision |
|---|---|---|
| 098_primary_admin_email_owner_mandate.py | `098_primary_admin_email_owner_mandate` | `097_...` |
| 099_fix_admin_roles_seed.py | `099_fix_admin_roles_seed` | `098_primary_admin_email_owner_mandate` |
| 100_process_workspaces_zip_r2.py | `100_process_workspaces_zip_r2` | `099_fix_admin_roles_seed` |
| **101_p32_dao_criteria_scoring_schema.py** | `101_p32_dao_criteria_scoring_schema` | `100_process_workspaces_zip_r2` |

**Chaîne légitime** : 098 → 099 → 100 → **101** ✅

---

### Fichier 082 (parasite)

| Fichier | revision | down_revision |
|---|---|---|
| **082_p32_dao_criteria_scoring_schema.py** | `082_p32_dao_criteria_scoring_schema` | `081_m16_evaluation_domains` |

**Chaîne parasite** : 081 → **082** ⛔

---

## IDENTIFICATION HEADS CONCURRENTS

**Méthode** : révisions NOT referenced as down_revision = heads

**Potential heads** :
1. `101_p32_dao_criteria_scoring_schema` ← **head légitime** (chaîne 098→099→100→101)
2. `082_p32_dao_criteria_scoring_schema` ← **head parasite** (chaîne divergente 081→082)

**Nombre de heads** : **2**

---

## CAUSE RACINE

**Fichier** : `alembic/versions/082_p32_dao_criteria_scoring_schema.py`

**Origine** : créé par agent lors de correction F1 erronée (session précédente)

**Motif erroné** : agent a cru que last migration = 081, alors que réalité = 100

**Conséquence** :
- 082 crée une branche divergente depuis 081
- 101 (légitime) est sur branche 100
- Alembic voit 2 heads : 082 et 101

---

## PREUVE TEXTUELLE

**Fichier 082 (l.21-22)** :
```python
revision = '082_p32_dao_criteria_scoring_schema'
down_revision = '081_m16_evaluation_domains'
```

**Fichier 101 (l.21-22)** :
```python
revision = '101_p32_dao_criteria_scoring_schema'
down_revision = '100_process_workspaces_zip_r2'
```

**082 pointe vers 081** → branche morte depuis 081  
**101 pointe vers 100** → branche vivante depuis 100

---

## GRAPHE ALEMBIC

```
... → 081_m16_evaluation_domains
        ↓
        082_p32_dao_criteria_scoring_schema  ← HEAD 1 (parasite)

... → 098_primary_admin_email_owner_mandate
        ↓
      099_fix_admin_roles_seed
        ↓
      100_process_workspaces_zip_r2
        ↓
      101_p32_dao_criteria_scoring_schema  ← HEAD 2 (légitime)
```

**2 heads = STOP Alembic**

---

## FICHIER RESPONSABLE BIFURCATION

**Fichier** : `alembic/versions/082_p32_dao_criteria_scoring_schema.py`

**Action requise** : SUPPRESSION (CAS 3 mandat)

**Justification** :
1. Créé par erreur (hypothèse fausse sur last migration)
2. Contenu identique à 101 (même opérations P3.2)
3. Branche morte (081→082 n'est pas la chaîne réelle du repo)
4. Aucune migration n'a été executée sur cette branche (082 jamais appliqué en base)

---

## VERDICT ÉTAPE A

✅ **PROBE COMPLET**

**Nombre exact de heads** : 2

**Liste exacte des heads** :
- `082_p32_dao_criteria_scoring_schema` (parasite)
- `101_p32_dao_criteria_scoring_schema` (légitime)

**Chaîne exacte** : 098 → 099 → 100 → 101 (légitime)

**Fichier responsable bifurcation** : `082_p32_dao_criteria_scoring_schema.py`

**CAS retenu** : CAS 3 (fichier parasite)

---

**ÉTAPE A CLOSED — passage ÉTAPE B (plan résolution)**
