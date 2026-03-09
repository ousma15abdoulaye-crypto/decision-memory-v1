# MRD_CURRENT_STATE
# Mis à jour uniquement par AO après chaque merge validé
# Un agent ne modifie jamais ce fichier
# Exception unique MRD-0 : l'agent met à jour ce fichier
# car MRD-0 est le mandat de fondation
# Dernière mise à jour : 2026-03-09

plan_version          : DMS_MRD_PLAN_V1
last_completed        : MRD-0
last_completed_at     : 2026-03-09
last_commit           : 7b8e3083ab1af633bc98f24d793ce12a365d6564
last_tag              : mrd-0-done
next_milestone        : MRD-1
next_status           : NOT_STARTED
blocked_on            : aucun

## Alignement stack

local_alembic_head      : m7_4b
local_alembic_current   : m7_4b
railway_alembic_head    : m7_4b
aligned_schema          : OUI
aligned_data            : NON — baseline duale BASELINE_MRD_PRE_REBUILD.md
railway_access_method   : RAILWAY_DATABASE_URL direct (.env)
railway_cli             : ABSENT

## Divergence données

local_dict_items_actifs  : 1490
railway_dict_items_actifs: 0
local_vendors            : 0
railway_vendors          : 661
décision_baseline        : DUALE — voir BASELINE_MRD_PRE_REBUILD.md

## Défaillances MRD-3

mrd3_merged_with_deficiencies : OUI
DEF-MRD3-01 à DEF-MRD3-06    : DOCUMENTÉES — correction MRD-4

## STOPs actifs

STOP-TRG-1 : trg_protect_item_identity absent — bloque MRD-4
STOP-TRG-2 : trg_protect_item_with_aliases absent — bloque MRD-4

## Hash chain

FREEZE_HASHES.md              : docs/freeze/FREEZE_HASHES.md
DMS_V4.1.0_FREEZE.md          : hashé ✓
DMS_ORCHESTRATION_FRAMEWORK_V1: hashé ✓
SYSTEM_CONTRACT.md             : hashé ✓ MRD-0
DMS_MRD_PLAN_V1.md             : hashé ✓ MRD-0
BASELINE_MRD_PRE_REBUILD.md    : hashé ✓ MRD-0

## Règle agent

Si next_milestone ≠ milestone du mandat reçu
→ STOP immédiat. Format Section 8 MRD_PLAN. Poster au CTO.
