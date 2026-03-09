# BASELINE_MRD_PRE_REBUILD
# RÉFÉRENCE MATHÉMATIQUE IMMUABLE
# Générée par PROBE-MRD0 + MRD-0
# NE PAS MODIFIER APRÈS COMMIT — JAMAIS
# Commit probe : 018c7f6fb60673f0d574f0d84553b4c8c6df3b59

---

## Architecture baseline duale

| Table                  | Local  | Railway | RÉFÉRENCE | Justification           |
|------------------------|--------|---------|-----------|-------------------------|
| dict_items actifs      | 1490   | 0       | LOCAL     | Dict développé local    |
| dict_items total       | 1490   | 0       | LOCAL     | idem                    |
| aliases                | 1596   | 0       | LOCAL     | idem                    |
| proposals              | 0      | 0       | LOCAL     | idem                    |
| seeds human_validated  | 53     | 0       | LOCAL     | idem                    |
| vendors                | 0      | 661     | RAILWAY   | Vendors prod Railway    |
| mercurials             | 27396  | 27396   | RAILWAY   | Source données réelles  |

---

## Valeurs de référence rebuild

dict_items_actifs_ref     : 1490
aliases_ref               : 1596
proposals_ref             : 0
seeds_human_validated_ref : 53
vendors_ref               : 661
mercurials_ref            : 27396

---

## Alembic

alembic_head_local   : m7_4b
alembic_head_railway : m7_4b
aligned              : OUI

---

## Règle rebuild

alias_preservation_rate = aliases_après / aliases_ref (LOCAL) >= 0.99
dict_items ne descendent pas sous la valeur dict_items_actifs_ref (1490)
vendors ne descendent pas sous vendors_ref (661)
