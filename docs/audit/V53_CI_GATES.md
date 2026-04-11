# V53 — Registre des gates CI (M-CTO-V53-J)

**Date :** 2026-04-11

## Gates existantes (référence)

- Workflows sous `.github/workflows/` : `ci-main.yml`, `ci-v52-gates.yml`, invariants V5.1, etc.

## Ajouts documentés V53

| Contrôle | Preuve |
|----------|--------|
| Tests unitaires ciblés V53 | `tests/unit/test_market_signal_lookup.py`, `test_guard.py`, `test_langfuse_policy.py`, `tests/procurement/test_m14_workspace_assembler.py`, `tests/api/test_workspace_timeline.py` |
| Règle JWT fallback écriture | `src/auth/guard.py` + `tests/unit/test_guard.py` |
| Gate RAG (pas d’import prod) | `scripts/check_v53_no_rag_import_in_src.py` — job `v53-sovereignty-gate` dans `ci-v52-gates.yml` (branches `cursor/*` incluses) |

## Hors scope immédiat

- Branchement `RAGService` dans `process_info_handler` : option B dans `V53_RAG_DECISION.md` ; la gate assure l’absence d’import fantôme sous `src/`.
