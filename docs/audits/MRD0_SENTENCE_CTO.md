# MRD0_SENTENCE_CTO
# Sentence CTO — état système 2026-03-08
# Décideur : AO — Abdoulaye Ousmane
# Statut   : FREEZE

---

## 1. Diagnostic

Dernier point sûr           : m6_dictionary_build
Première corruption causale : m7_2_taxonomy_reset
Segment suspect             : m7_2, m7_3, m7_4a
Segment conservable         : M4, M5, M6, m7_3b
Alembic head                : m7_4b (local et Railway)
Divergence données          : baseline duale documentée

---

## 2. Verdicts composants

CONSERVER :
  vendors M4 · mercuriale ingest M5 · dict M6 m6_dictionary_build
  aliases sains · m7_3b_deprecate_legacy_families · m7_4_dict_vivant

FIGER — migration intacte zéro modification :
  m7_2_taxonomy_reset · m7_3_dict_nerve_center
  colonnes structurelles M7 non supprimées

DOCTRINE DÉPRÉCIÉE — migration Alembic intacte :
  m7_4a_item_identity_doctrine · taxonomie imposée comme socle

INTERDIT — CI fail si modifié :
  m7_rebuild_t0_purge.py · tout script DELETE+INSERT registre

---

## 3. Défaillances MRD-3

  DEF-MRD3-01 à DEF-MRD3-06 — documentées — corrigées MRD-4
  Voir DMS_MRD_PLAN_V1.md Section 1.3

---

## 4. STOPs actifs au gel

  STOP-TRG-1 : trg_protect_item_identity absent
               → bloque MRD-4 pipeline si non corrigé
  STOP-TRG-2 : trg_protect_item_with_aliases absent
               → bloque MRD-4 pipeline si non corrigé
  Non bloquants pour MRD-0/1/2

---

## 5. SHA256 documents fondateurs au gel (2026-03-09)

  SYSTEM_CONTRACT.md              : 92acb422b6066db7375e2d7e2b4131c8abe373437c4da6363b8aa8e6735aba27
  DMS_V4.1.0_FREEZE.md            : e892d783471639e67db8fc17c8de9366f81b37172554783b942993b815ea9ad4
  DMS_ORCHESTRATION_FRAMEWORK_V1.md : 66a6961d20f88a51cb9d0efb8bba4531e648cb4e4e5acf40edf3fd2d9f011cf6
  DMS_MRD_PLAN_V1.md              : a0ceb151e36d2eb098d12f9ea6c9d0f712a772fca1db9093492d67464b2854ed
  BASELINE_MRD_PRE_REBUILD.md     : d1093db69e504ae184e15e0ba2db1f9418eada6f2cf79fcb6fac1e51dabab1fd

---

## 6. Ordre de reprise

  PRE0  : DONE ✓
  MRD-0 : en cours → DONE après ce commit
  MRD-1 → MRD-2 → MRD-4 → MRD-5 → MRD-6
