# P3.2 DÉVIATION 001 — is_active

**Date** : 2026-04-18  
**Référence** : P3.2 Option A/B confusion  
**Statut** : ⛔ **DÉVIATION CORRIGÉE**

---

## DÉVIATION

**Action non autorisée** : Création fichiers migration/scripts ajoutant colonne `is_active` à `process_workspaces`.

**Décision CTO réelle** : Soft-delete via **`status` existante** (pas nouvelle colonne `is_active`).

---

## CONFUSION

**Contexte** : Deux décisions Option A/B différentes dans le workflow :

1. **Première décision** (nettoyage corpus) : A=DELETE / B=SOFT-DELETE / C=ISOLATION
   - **CTO a choisi : Option B (soft-delete)**

2. **Deuxième décision** (implémentation soft-delete) : A=créer is_active / B=utiliser status
   - **Agent a demandé : "créer is_active ou utiliser status ?"**
   - **CTO a répondu : "GO OPTION A"**
   - **Agent a interprété : "créer is_active"**
   - **CTO voulait dire : "utiliser status existante"**

**Erreur agent** : Mauvaise interprétation "GO OPTION A" → création fichiers non autorisés.

---

## DÉCISION CTO CONFIRMÉE

**Soft-delete P3.2** : via colonne **`status`** existante (pas nouvelle colonne).

**Valeur soft-delete** : `status = 'ARCHIVED_LEGACY'` (ou valeur à définir par probe status).

**Aucune migration colonne** : `status` existe déjà (type TEXT, défaut 'draft').

---

## FICHIERS CRÉÉS PAR ERREUR

1. ❌ `scripts/p32_migration_add_is_active.sql` (migration non autorisée)
2. ❌ `scripts/p32_etape2_legacy_trace_corrected.sql` (basé sur is_active)
3. ❌ `scripts/p32_etape2_legacy_trace.py` (basé sur is_active)

**Action CTO** : Fichiers à supprimer manuellement du repo (bash échoue exit 3221225781).

---

## CORRECTION REQUISE

**Avant toute ÉTAPE 2** : **PROBE STATUS RÉEL** obligatoire

### Fichier créé :
- `scripts/p32_probe_status_column.sql` (4 queries status)

### Queries probe :
1. Valeurs status distinctes (sci_mali workspaces)
2. Contraintes CHECK sur status (valeurs autorisées)
3. Status workspaces LEGACY_90 actuels
4. Status workspace CONFORME (CASE-28b05d85)

**Archivage output** : `decisions/p32_r2_schema_probe_addendum.md`

**Validation CTO requise** avant tout script ÉTAPE 2.

---

## CONSÉQUENCE

⚠️ **Avertissement 1/1** : Prochaine déviation → arrêt complet chantier P3.2.

**Règle absolue réaffirmée** :
- Aucune migration sans GO CTO explicite
- Aucune colonne ajoutée sans mandat
- Aucune interprétation ambiguë (demander clarification CTO)

---

**Déviation archivée. Fichiers créés par erreur à supprimer. Probe status prêt.**
