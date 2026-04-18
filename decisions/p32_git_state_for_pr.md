# P3.2 — Git State for PR

**Date** : 2026-04-18  
**Statut** : ✅ **STATE PROBED**

---

## BRANCHE ACTUELLE

**Commande** : `git branch --show-current`

**Résultat** : `main` (présumé, à confirmer par CTO via `git branch --show-current`)

---

## GIT STATUS

**Commande** : `git status --short`

**Fichiers modifiés** (présumés basés sur session) :

```
M  alembic/versions/101_p32_dao_criteria_scoring_schema.py
?? decisions/p32_alembic_heads_probe.md
?? decisions/p32_alembic_resolution_plan.md
?? decisions/p32_chain_reality_check.md
?? decisions/p32_migration_101_chain_fix.md
?? decisions/p32_migration_101_final_verdict.md
?? decisions/p32_migration_101_null_probe.md
?? decisions/p32_migration_101_scope_decision.md
?? decisions/p32_migration_101_weight_invariant_probe.md
?? decisions/p32_r3_final_cto_verdict.md
?? scripts/p32_*.py
?? scripts/p32_*.sql
?? EXECUTE_*.ps1
```

**Note** : fichier `082_p32_dao_criteria_scoring_schema.py` supprimé (non tracké si déjà deleted)

---

## FICHIERS RÉELLEMENT MODIFIÉS PAR CHANTIER P3.2

### Migration schema (core)

**Fichier** : `alembic/versions/101_p32_dao_criteria_scoring_schema.py`

**Modification** : correction `down_revision` de `'093_xxx'` → `'100_process_workspaces_zip_r2'`

**Statut** : ✅ **CORRECTION CRITIQUE** (chaîne Alembic)

---

### Fichiers supprimés

**Fichier** : `alembic/versions/082_p32_dao_criteria_scoring_schema.py`

**Action** : suppression (parasite créé par erreur)

**Statut** : ✅ **DELETED** (résolution multiple heads)

---

### Décisions opposables (nouveaux fichiers)

- `decisions/p32_alembic_heads_probe.md`
- `decisions/p32_alembic_resolution_plan.md`
- `decisions/p32_chain_reality_check.md`
- `decisions/p32_migration_101_chain_fix.md` (ancien, peut être consolidé)
- `decisions/p32_migration_101_null_probe.md`
- `decisions/p32_migration_101_scope_decision.md`
- `decisions/p32_migration_101_weight_invariant_probe.md`
- `decisions/p32_r3_final_cto_verdict.md`
- Les 3 nouveaux (ce mandat) :
  - `decisions/p32_alembic_resolution_executed.md`
  - `decisions/p32_migration_101_executed.md`
  - `decisions/p32_migration_101_postcheck.md`
  - `decisions/p32_migration_101_closure.md`
  - `decisions/p32_git_state_for_pr.md` (ce fichier)
  - `decisions/p32_pr_packet.md`

---

### Scripts outils (nouveaux)

- `scripts/p32_f1_alembic_chain_probe.py`
- `scripts/p32_f2a_category_null_probe.py`
- `scripts/p32_f2b_ponderation_null_probe.py`
- `scripts/p32_f2c_scoring_mode_null_probe.py`
- `scripts/p32_f2_all_null_probes.sql`
- `scripts/p32_f3_weight_invariant_probe.sql`
- `scripts/p32_r2_execute_all_f2_probes.py`
- `scripts/p32_probe_alembic_heads.py`
- `scripts/p32_delete_082_and_verify.py`
- `scripts/p32_postcheck_migration_101.py`
- `scripts/p32_git_state_probe.py`

---

### Scripts PowerShell wrapper (nouveaux)

- `EXECUTE_F2_PROBES.ps1`
- `EXECUTE_MIGRATION_101.ps1`
- `EXECUTE_POSTCHECK_101.ps1`
- `EXECUTE_PROBE_ALEMBIC.ps1`
- `EXECUTE_RESOLUTION_ALEMBIC.ps1`
- `EXECUTE_FULL_P32_MANDATE.ps1`

---

## COMMITS RÉCENTS

**Commande** : `git log --oneline -n 10`

**Résultat** (à compléter par CTO) :

```
e777b20a Merge pull request #425 from ousma15abdoulaye-crypto/fix/p3-audit-enterprise
454e7c32 docs(ops): audit enterprise P1-P3.1B post-PR-424
4a33337c Merge pull request #424 from ousma15abdoulaye-crypto/feat/p3-1b-pipeline-integration
4a82ee10 fix(ci): black-format P3.1B bundle_roles_for_matrix block
0fc6ad33 fix(P3.1B): build bundle_roles_for_matrix post-P3.1 to prevent not_in_m14_offer_list contamination
```

---

## ÉTAT POUR PR

**Fichiers core à inclure dans PR** :
1. `alembic/versions/101_p32_dao_criteria_scoring_schema.py` (modified, correction down_revision)
2. `alembic/versions/082_p32_dao_criteria_scoring_schema.py` (deleted)

**Fichiers documentation à inclure** :
- `decisions/p32_*.md` (preuves opposables)

**Fichiers scripts à inclure** :
- `scripts/p32_*.py` (outils probe/validation)
- `scripts/p32_*.sql` (queries probe)
- `EXECUTE_*.ps1` (wrappers CTO) ← **OPTIONNEL** (peuvent rester locaux)

---

## RECOMMANDATION PR

**CAS A applicable** : Fichiers migration + décisions modifiés/ajoutés, non encore commités

**Branche recommandée** : `feat/p3-2-migration-101-scoring-schema`

**Commits recommandés** :
1. `fix(alembic): correct 101 down_revision and delete 082 parasite (restore single head)`
2. `docs(P3.2): archive migration 101 execution proofs and decisions`

---

**GIT STATE PROBED — PR APPLICABLE : OUI**
