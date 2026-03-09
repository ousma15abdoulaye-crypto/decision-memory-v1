# MRD4_RESULT
# Cloture milestone MRD-4
# Date     : 2026-03-09
# Decideur : AO — Abdoulaye Ousmane

## Identite

milestone   : MRD-4
branche     : feat/mrd-4-hardening-rebuild
tag         : mrd-4-done (pose par CTO post-merge)

## Alembic

head_repo        : m7_5_fingerprint_triggers
current_db       : m7_5_fingerprint_triggers
down_revision    : m7_4b
cycle_complet    : upgrade -> downgrade -> upgrade OK
heads_eq_current : OUI

## Correction peer review integree

fingerprint_formula_avant : sha256(normalize(label)|source_type|source_id)
fingerprint_formula_apres : sha256(normalize(label_fr)|source_type)
source_id_exclu_raison    : identifiant pas identite — INV-04
label_col_reel            : label_fr (pas label — inexistant en DB)

## Defaillances MRD-3

DEF-MRD3-01 : numero migration calcule par agent         CORRIGE
DEF-MRD3-02 : alembic current verifie chaque etape       CORRIGE
DEF-MRD3-03 : downgrade() fail-loud present              CORRIGE
DEF-MRD3-04 : heads repo = current DB verifie            CORRIGE
DEF-MRD3-05 : colonne fingerprint creee                  CORRIGE
DEF-MRD3-06 : triggers protection crees                  CORRIGE

## Triggers crees

trg_protect_item_identity     : PRESENT (BEFORE UPDATE)
trg_protect_item_with_aliases : PRESENT (BEFORE DELETE)

## Colonnes ajoutees

fingerprint     : TEXT — sha256(normalize(label_fr)|source_type)
birth_source    : TEXT CHECK (mercuriale|imc|seed|manual|legacy|unknown)
birth_run_id    : UUID
birth_timestamp : TIMESTAMPTZ DEFAULT now()

## Metriques rebuild execute

run_id                   : 82ed0e73-15dd-4b8e-a02f-0a31e443b813
items_avant              : 1490
items_apres              : 1490
aliases_avant            : 1596
aliases_apres            : 1596
alias_preservation_rate  : 1.0000 >= 0.99
destructive_loss         : 0
duplicate_identity       : 0
sans_fp_restant          : 0

## Tests contrat

CT-01 CASCADE FK                 : PASS
CT-02 alembic heads=1            : PASS
CT-03 DATABASE_URL               : PASS
CT-04 append-only                : PASS
CT-05 fingerprint                : PASS
CT-ROUGE-01 trg_protect_identity : PASS (etait XFAIL)
CT-ROUGE-02 trg_protect_aliases  : PASS (etait XFAIL)

## Invariants

INV-04 identite item stable    : PASS
INV-05 UPSERT fingerprint      : PASS
INV-07 downgrade() fail-loud   : PASS
INV-08 alembic heads = 1 ligne : PASS
INV-09 1 milestone 1 branche   : PASS
INV-13 CASCADE FK absent       : PASS

## CI compliance

ruff  : PASS (migration + script)
black : PASS (migration + script)

## Note Railway

m7_5 non applique sur Railway
railway_migration_pending : OUI
A planifier dans mandat MRD-5 ou dedi

## Statut

DONE
next_milestone : MRD-5
