# MRD-2 RESULT
milestone            : MRD-2
nom_canonique        : MRD-2-ADR-GENETIC-CONTRACT-TESTS
date_utc             : 2026-03-09
decideur             : AO — Abdoulaye Ousmane
statut               : DONE

---

## Invariants

INV-01  PASS  Séquence milestone respectée (PRE0→MRD-0→MRD-1→MRD-2)
INV-07  N/A   Aucune migration — MRD-2 est doc+tests uniquement
INV-08  PASS  alembic heads = 1 (m7_4b) — CT-02 vert
INV-09  PASS  1 branche = 1 PR = 1 merge = 1 tag — en cours
INV-13  PASS  CASCADE FK absente couche_b — CT-01 vert

---

## Livrables produits

docs/adr/ADR-MRD2-GENETIC.md
  8 définitions canoniques (DEF-01 à DEF-08)
  8 interdits structurels (IS-01 à IS-08)
  Section défaillances MRD-3 et corrections MRD-4

tests/contracts/test_mrd2_contracts.py
  CT-01  IS-02 aucune CASCADE FK couche_b          PASS
  CT-02  IS-06 alembic heads = 1                   PASS
  CT-03  IS-07 DATABASE_URL pas Railway             PASS
  CT-04  DEF-03 aucun trigger DELETE destructif     PASS
  CT-05  DEF-02 fingerprint stable et déterministe  PASS
  CT-ROUGE-01  trg_protect_item_identity absent     XFAIL (DEF-MRD3-06)
  CT-ROUGE-02  trg_protect_item_with_aliases absent XFAIL (DEF-MRD3-06)

Résultat pytest : 5 passed, 2 xfailed — exit(0)

---

## STOPs actifs

STOP-TRG-1 : trg_protect_item_identity absent — bloque MRD-4
STOP-TRG-2 : trg_protect_item_with_aliases absent — bloque MRD-4
Non bloquants pour MRD-2 (doc+tests uniquement)

---

## Défaillances MRD-3

DEF-MRD3-01 à DEF-MRD3-06 : documentées dans ADR-MRD2-GENETIC.md
Correction prévue : MRD-4

---

## Prochaine étape

MRD-4 — Hardening + rebuild canonique
  Corrige DEF-MRD3-01 à DEF-MRD3-06
  CT-ROUGE-01 et CT-ROUGE-02 passent VERT
