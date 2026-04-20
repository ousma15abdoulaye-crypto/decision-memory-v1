# P3.2 ÉTAPE B — Plan Résolution Alembic

**Date** : 2026-04-18  
**Référence** : `decisions/p32_alembic_heads_probe.md`  
**Statut** : ✅ **PLAN VALIDÉ**

---

## CAUSE RACINE

**Fichier parasite** : `alembic/versions/082_p32_dao_criteria_scoring_schema.py`

**Origine** : créé par erreur lors de correction F1 (session précédente)

**Symptôme** : 2 heads Alembic
- Head 1 (parasite) : `082_p32_dao_criteria_scoring_schema` (branche 081→082)
- Head 2 (légitime) : `101_p32_dao_criteria_scoring_schema` (branche 098→099→100→101)

---

## CAS RETENU

**CAS 3** : fichier parasite crée une branche fantôme

**Justification** :
1. 082 n'a jamais été appliqué en base (création erronée, jamais exécuté)
2. Contenu identique à 101 (même migration P3.2)
3. down_revision incorrect (`081_m16_evaluation_domains` au lieu de `100_process_workspaces_zip_r2`)
4. Chaîne réelle du repo : 098→099→100, pas 081→082

---

## OPTION RETENUE

**Action** : SUPPRESSION fichier `082_p32_dao_criteria_scoring_schema.py`

**Justification** :
- Fichier créé par erreur (hypothèse fausse sur last migration)
- Jamais appliqué (current head != 082)
- Branche morte (aucune migration ne référence 082 comme down_revision)
- Suppression restaure single head (101 devient seul head)

---

## COMMANDE EXACTE

**Bash/PowerShell** :
```bash
rm alembic/versions/082_p32_dao_criteria_scoring_schema.py
```

**Git** (après suppression) :
```bash
git add alembic/versions/082_p32_dao_criteria_scoring_schema.py
git commit -m "fix: remove parasite migration 082 (created by error, restores single head 101)"
```

---

## IMPACT ATTENDU

### Avant suppression
```
alembic heads  →  2 heads
  - 082_p32_dao_criteria_scoring_schema (parasite)
  - 101_p32_dao_criteria_scoring_schema (légitime)
```

### Après suppression
```
alembic heads  →  1 head
  - 101_p32_dao_criteria_scoring_schema (seul head)
```

**Chaîne restaurée** : 098 → 099 → 100 → 101 (single head)

---

## VÉRIFICATION POST-RÉSOLUTION

**Commandes obligatoires** :
1. `alembic heads` → doit retourner exactement 1 head
2. `alembic current` → doit retourner `100_process_workspaces_zip_r2` (head actuel avant migration 101)
3. Vérifier `alembic/versions/` ne contient plus 082

**Critère succès** : `alembic heads` retourne 1 ligne uniquement

---

## ALTERNATIVES REJETÉES

### Option A — Corriger down_revision de 082
**Rejetée** : 082 est un doublon de 101, pas une migration distincte. Corriger down_revision créerait une chaîne 100→082→??? incohérente.

### Option B — Merge migration
**Rejetée** : pas de 2 branches légitimes à merger. 082 est un artefact d'erreur, pas une branche de développement parallèle.

### Option C — Renommer 082 en 102
**Rejetée** : 082 et 101 sont identiques (même opérations P3.2). Renommer créerait un doublon de migration.

---

## PLAN EXÉCUTION

1. ✅ Lire `decisions/p32_alembic_heads_probe.md` (preuve 2 heads)
2. ⏳ Supprimer `alembic/versions/082_p32_dao_criteria_scoring_schema.py`
3. ⏳ Exécuter `alembic heads` (vérifier 1 head)
4. ⏳ Exécuter `alembic current` (vérifier head actuel = 100)
5. ⏳ Archiver résultat dans `decisions/p32_alembic_resolution_executed.md`

---

## VERDICT PLAN

✅ **PLAN COHÉRENT, UNIQUE, DÉTERMINISTE**

**Option** : suppression fichier 082 parasite  
**Impact** : restaure single head 101  
**Commande** : `rm alembic/versions/082_p32_dao_criteria_scoring_schema.py`

---

**ÉTAPE B CLOSED — passage ÉTAPE C (exécution résolution)**
