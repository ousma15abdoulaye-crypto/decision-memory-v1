# MRD5_RESULT
# Cloture milestone MRD-5
# Date     : 2026-03-09
# Decideur : AO — Abdoulaye Ousmane

## Identite

milestone   : MRD-5
branche     : feat/mrd-5-identity-canonical
tag         : mrd-5-done (pose par CTO post-merge)

## Alembic

head_repo        : m7_6_item_code
current_db       : m7_6_item_code
down_revision    : m7_5_fingerprint_triggers
cycle_complet    : upgrade -> downgrade -> upgrade OK
heads_eq_current : OUI

## ADR

ADR-MRD5-ITEM-IDENTITY-V1.md : cree
Interdits IS-09 a IS-12 : documentes

## Backfill item_code

total_backfille   : 1490
avec_code         : 1490
sans_code         : 0
errors            : 0
format            : {PREFIX}-{YYYYMM}-{SEQ6}
exemple_premier   : LG-202603-000001
exemple_dernier   : LG-202603-001490
birth_source_dominant : unknown -> PREFIX=LG (corpus initial)

## Trigger protection etendu

fn_protect_item_identity() etendu : item_code immuable ajoute
trg_protect_item_identity BEFORE UPDATE : toujours actif

## Tests

test_mrd2_contracts.py : 7/7 passed — aucune regression

## CI compliance

ruff  : PASS (migration + script)
black : PASS (migration + script)

## Invariants

INV-04 identite item stable  : PASS
INV-07 downgrade() fail-loud : PASS
INV-08 alembic heads = 1     : PASS
INV-09 1 milestone 1 branche : PASS
IS-09  item_code sans taxo   : PASS
IS-10  item_code immuable    : PASS

## Note Railway

m7_5 et m7_6 non appliques sur Railway
railway_migration_pending : OUI — m7_5 + m7_6 a planifier

## Statut

DONE
next_milestone : MRD-6
