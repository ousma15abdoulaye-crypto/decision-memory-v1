# CONTEXT_ANCHOR
# Poser EN PREMIER dans toute nouvelle session Claude.
# Regenere apres chaque milestone DONE.
# Genere : 2026-03-09 — post MRD-6

## IDENTITE PROJET
projet    : DMS — Digital Market Signal
operateur : AO — Abdoulaye Ousmane
lieu      : Mopti, Mali
outil     : Cursor + Claude Sonnet 4.6
role CTO  : CTO senior + systems engineer

## DOCUMENTS GELES — NE PAS REEXPLIQUER
V4        : docs/freeze/DMS_V4.1.0_FREEZE.md
FRAMEWORK : docs/freeze/DMS_ORCHESTRATION_FRAMEWORK_V1.md
MRD_PLAN  : docs/freeze/DMS_MRD_PLAN_V1.md
CONTRACT  : docs/freeze/SYSTEM_CONTRACT.md

## ETAT COURANT
Lire : docs/freeze/MRD_CURRENT_STATE.md

## STACK
local_db  : postgresql+psycopg://dms:dms123@localhost:5432/dms
railway_db: RAILWAY_DATABASE_URL dans .env
alembic   : voir MRD_CURRENT_STATE.md

## MILESTONES
MRD-0  DONE  mrd-0-done  4b2fab8
MRD-1  DONE  mrd-1-done  b939e3b
MRD-2  DONE  mrd-2-done  a3067fb
MRD-3  DONE  (DEF-MRD3-01/06 corriges MRD-4)
MRD-4  DONE  mrd-4-done  831117b
MRD-5  DONE  mrd-5-done  29efbc6
MRD-6  DONE  mrd-6-done  820023fff2db6fa2adc8a4eb309c120d63e2e290
NEXT   : M8 (V4 reprend depuis DMS_V4.1.0_FREEZE.md)

## SCHEMA REEL (important pour agents)
PK items    : item_id (TEXT) — pas item_uid
label       : label_fr — pas label
fingerprint : sha256(normalize(label_fr)|source_type)
item_code   : LG-YYYYMM-NNNNNN (1490 items, tous LG)
label_status: draft | validated | deprecated (tous draft)
taxo_l1/2/3 : presentes (1287/1490 classifies, coverage 86.38%)
collision_log: public.dict_collision_log (V4, 610 unresolved)
railway     : m7_5 + m7_6 + m7_7 pending (schema m7_4b)

## DECISIONS ARCHITECTURALES FIGEES
fingerprint : sha256(normalize(label_fr)|source_type)
normalize() : strip + lower + collapse_whitespace
item_id     : PK TEXT immuable — trg_protect_item_identity
item_code   : LG-YYYYMM-NNNNNN — immuable — IS-10
label_status: draft | validated | deprecated
coverage    : dict=LOCAL(1490) vendors=RAILWAY(661)
taxo_version: 1.0 — derivee corpus reel

## REGLES CRITIQUES
REGLE-26 : collision fuzzy >= 85 — resolution humaine uniquement
REGLE-29 : M5->M6->M7 non inversible
INV-03   : UPSERT fingerprint jamais DELETE+INSERT
INV-11   : alembic heads = 1 ligne
CONTRACT-02 : DATABASE_URL jamais Railway en migration locale

## PIEGES ACTIFS
P-label : colonne = label_fr (pas label)
P-pk    : PK = item_id (pas item_uid)
P-fuzzy : fuzzy_score V4 = 0.0-1.0 (pas 0-100)
P-res   : resolution V4 = 'unresolved'|'auto_merged'|'proposal_created'
P-ruff  : imports dans fonctions = erreur CI — toujours au top
P-black : appliquer black avant commit

## PROCHAINE ETAPE
M8 MARKET SURVEY
  Lire DMS_V4.1.0_FREEZE.md Partie XI pour le mandat

## INSTRUCTION CLAUDE NOUVELLE SESSION
Tu es CTO senior DMS.
Tu lis CONTEXT_ANCHOR + MRD_CURRENT_STATE avant toute action.
Tu ne demandes PAS de reexpliquer V4 ou Framework.
Tu travailles depuis cet anchor.
Si info manquante pour la tache -> demander uniquement ce qui manque.
