# MRD_CURRENT_STATE
# Mis à jour uniquement par AO après chaque merge validé
# Un agent ne modifie jamais ce fichier sans mandat explicite
# Dernière mise à jour : 2026-03-09T07:18:49Z (PROBE-MRD0)

plan_version          : DMS_MRD_PLAN_V1
last_completed        : MRD-3 (neutralise CASCADE FK aliases → RESTRICT)
last_completed_at     : 2026-03-08T19:34:49Z
last_commit           : 0f37c23 chore: probe etat systeme + fondation MRD [PROBE-MRD0]
last_tag              : framework-v1-done
next_milestone        : MRD-0
next_status           : NOT_STARTED
blocked_on            : aucun

## Alignement stack

local_alembic_head    : m7_4b
local_alembic_current : m7_4b (head)
railway_alembic_head  : m7_4b
aligned               : OUI — local=m7_4b railway=m7_4b

railway_last_deploy   : INACCESSIBLE (Railway CLI absent, pas de log deploy)

## Données en base

### Local (localhost:5432/dms)

dict_items_actifs          : 1490
dict_items_total           : 1490
aliases                    : 1596
proposals                  : 0
seeds_human_validated      : 53
vendors                    : 0
mercurials                 : 27396

### Railway (maglev.proxy.rlwy.net:35451/railway)

dict_items_actifs          : 0      ← DIVERGENCE — non ingéré en prod
aliases                    : 0      ← DIVERGENCE — non ingéré en prod
proposals                  : 0
seeds_human_validated      : 0      ← DIVERGENCE — non ingéré en prod
vendors                    : 661    ← PEUPLÉ en prod
mercurials                 : 27396  ← ALIGNÉ

## Triggers couche_b (local)

trg_block_legacy_family_insert   : PRÉSENT
trg_block_legacy_family_update   : PRÉSENT
trg_compute_quality_score        : PRÉSENT (INSERT + UPDATE)
trg_dict_compute_hash            : PRÉSENT (UPDATE)
trg_dict_write_audit             : PRÉSENT (UPDATE)
trg_protect_item_identity        : ABSENT  ← défaillance connue
trg_protect_item_with_aliases    : ABSENT  ← défaillance connue

## FK couche_b

cascade_fk                 : AUCUNE ✓ (neutralisé par MRD-3)
fk_mercuriale_raw_queue    : SET NULL (acceptable — non-critique)
toutes autres FK           : RESTRICT ou NO ACTION

## Défaillances MRD-3 connues

mrd3_merged_with_deficiencies : OUI
DEF-MRD3-01 : trg_protect_item_identity absent — à corriger MRD-4
DEF-MRD3-02 : trg_protect_item_with_aliases absent — à corriger MRD-4
DEF-MRD3-03 : dict_items Railway = 0 (ingestion prod non effectuée)
DEF-MRD3-04 : vendors local = 0 (ETL local non exécuté)
DEF-MRD3-05 : pytest-asyncio NON INSTALLÉ — impact tests async
DEF-MRD3-06 : DOCUMENTÉE — voir docs/audits/AUDIT_M4_M7_*

## Structure repo

tests_py                   : 106 fichiers
scripts_py                 : 58 fichiers
alembic_versions           : 59 fichiers (dont doublons 009_* et 040_* historiques)
docs_md                    : ~120 fichiers markdown
workflows_ci               : 7 fichiers

## Règle agent

Si next_milestone ≠ milestone du mandat reçu
→ STOP immédiat. Format Section 8 MRD_PLAN. Poster au CTO.
