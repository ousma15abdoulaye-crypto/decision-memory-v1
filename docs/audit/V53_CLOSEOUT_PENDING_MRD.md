# V53 — Clôture MRD (en attente AO)

**Date :** 2026-04-11

Les changements V53 (marché ADR-B, RBAC fallback, historique M16, pipeline M14 assembleur, timeline workspace, M12 corrections API, Langfuse strict optionnel) sont mergés via PR dédiée.

**Action AO :** mettre à jour `docs/freeze/MRD_CURRENT_STATE.md` et addendum `CONTEXT_ANCHOR.md` selon procédure interne (RÈGLE-ANCHOR-01 / -02).

**Suivi post-merge main (ex. #373) :** PR `cursor/pv-v53-proof-ci-gate-6ef8` — PV snapshot **v1.2** (`m14_proof`, `m13_proof`), script `scripts/check_v53_no_rag_import_in_src.py`, job CI `v53-sovereignty-gate`, trigger workflow sur `cursor/*`.
