# ADR-MRD0-GOVERNANCE
# Gouvernance redressement M4→M7
# Date     : 2026-03-08
# Décideur : AO — Abdoulaye Ousmane
# Statut   : ACCEPTÉ — FREEZE

## Contexte

Dérives documentées sur segment M4→M7 :
  MRD-2 sauté par agent sans mémoire persistante
  MRD-3 mergé avec 6 défaillances (DEF-MRD3-01/06)
  Divergence données Local/Railway non documentée
  Absence de verrou de séquence milestone

## Décisions

D1 — Source de vérité par table
  Railway = référence vendors. Local = référence dict_items.
  Baseline duale dans BASELINE_MRD_PRE_REBUILD.md.

D2 — Variables d'environnement
  DATABASE_URL → local. RAILWAY_DATABASE_URL → Railway.
  CONTRACT-02 SYSTEM_CONTRACT.md.

D3 — Séquence figée
  PRE0 → MRD-0 → MRD-1 → MRD-2 → MRD-4 → MRD-5 → MRD-6

D4 — Hash chain documents fondateurs
  FREEZE_HASHES.md = référence centrale.
  Validation de la hash chain à chaque session (procédure manuelle à date ; automatisation future dans validate_mrd_state.py).
  Ordre logique de la hash chain : SYSTEM_CONTRACT → V4 → Framework → MRD_PLAN → BASELINE

D5 — Mémoire persistante externe
  MRD_CURRENT_STATE.md lu par tout agent en premier.
  Modifié uniquement par AO.

## Conséquences

  Dérive structurellement impossible.
  Modification silencieuse détectée automatiquement.
  Milestone sauté bloqué physiquement.
