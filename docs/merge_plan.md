# Operation "Clean Merge" — Merge Plan

Generated: 2026-02-10

## Inventory (Open PRs)

| PR | Branch | mergeable_state | CI status (latest) | P0 touched | Category | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| #14 | `copilot/resolve-git-conflicts` | `unstable` (mergeable) | DMS CI **action_required** (run 21879471152) | `.github/workflows/ci.yml`, `src/db.py` | A | Small stabilisation PR, CI must turn green. |
| #5 | `copilot/implement-single-agent-execution` | `dirty` | DMS CI – Core Stability **success** (run 21878518591) | `ci.yml`, `alembic/**`, `requirements.txt`, `scripts/smoke_postgres.py`, `src/db.py` | B | Conflicts; contains DB/migration fixes. |
| #3 | `copilot/restructure-repo-for-cursor-speed` | `dirty` | DMS CI – Core Stability **success** (run 21860734203) | `ci.yml`, `alembic/**`, `requirements.txt`, `scripts/smoke_postgres.py`, `src/db.py` | B | Large infra bundle; conflicts with PR5. |
| #8 | `copilot/audit-couche-b-minimal-fixes` | `dirty` | DMS CI – PostgreSQL Online-Only **failure** (run 21877178858) | `ci.yml`, `scripts/smoke_postgres.py` | C | CI fails (missing `psycopg2` in smoke test). Overlaps with PR5/PR3. |

### Category Key
- **A** = mergeable clean/small (candidate merge)
- **B** = conflicts but unique value
- **C** = conflicts + redundant (prefer close or cherry-pick)

## Merge Strategy (Source of Truth)
1. **Base CI/DB source of truth**: PR **#14** for minimal CI workflow + PR **#5** for DB/migrations.
2. **Merge order** (recommended):
   1) **#14** (small stabilization)
   2) **#5** (DB/CI/migrations socle)
   3) **#3** (large infra bundle, only after #5 stable)
   4) **#8** (rebase + fix CI, or close if redundant)

## Alembic Rule Notes
- PR #5 introduces `alembic/versions/001_add_couche_b.py`.
- PR #3 introduces `alembic/versions/001_initial.py`.
- **Action required**: after merging #14 + #5, rebase #3 and regenerate/rename migrations so there is **one Alembic head**.

## Required Actions (Maintainer)
- Rebase/merge main into PRs #5/#3/#8 and resolve conflicts following CI-minimal rules.
- Resolve PR #8 CI failure (`psycopg2` missing in smoke test).
- Verify Alembic heads = 1 after consolidation.
