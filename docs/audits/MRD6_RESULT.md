# MRD6_RESULT
# Cloture milestone MRD-6
# Date     : 2026-03-09
# Decideur : AO — Abdoulaye Ousmane

## Identite

milestone   : MRD-6
branche     : feat/mrd-6-taxonomy-genome
tag         : mrd-6-done (pose par CTO post-merge)

## Alembic

head_repo        : m7_7_genome_stable
current_db       : m7_7_genome_stable
down_revision    : m7_6_item_code
cycle_complet    : upgrade -> downgrade -> upgrade OK
heads_eq_current : OUI

## BRIQUE-1 Taxonomie

coverage_gate     : 86.38% >= 85% PASS
items_classifies  : 1287
items_non_class   : 203
taxo_version      : 1.0
regles            : 299 patterns dans MRD6_TAXONOMY_V1.md

## BRIQUE-2 Label status

label_status cree       : OUI (default='draft')
label_fr protege        : OUI si label_status='validated'
deprecated irreversible : OUI
total_draft             : 1490 (tous en draft apres migration)
total_validated         : 0 (aucun encore valide)

## BRIQUE-3 Collisions

collisions_detectees    : 610
collisions_unresolved   : 610
seuil                   : 85 (REGLE-26)
items_analyses          : 600/1490
resolution_auto         : interdite (humain uniquement)

## M7 recadre

fn_protect_item_identity etendu : label_fr immuable si validated
deprecated irreversible         : OUI
label_status protege            : OUI

## Adaptations schema reel

item_id = PK TEXT (pas item_uid)
label_fr = colonne label (pas label)
dict_collision_log dans public (V4, pas cree ici)
taxo_version pre-existante (pas recrree)
fuzzy_score stocke 0.0-1.0 (echelle V4)
resolution = 'unresolved' (contrainte V4)

## CI compliance

ruff  : PASS (migration + scripts)
black : PASS (migration + scripts)

## Invariants

INV-07 taxo apres registre   : PASS
INV-04 identite stable       : PASS
INV-07 downgrade() fail-loud : PASS
INV-08 alembic heads = 1     : PASS
REGLE-26 seuil 85            : PASS
REGLE-27 collision_log       : PASS
REGLE-29 sequence M5->M6->M7 : PASS

## Statut

DONE
next_milestone : M8 (V4 reprend depuis DMS_V4.1.0_FREEZE.md)
