# PR: infra/workspace-setup-ci-railway → main

**Create PR at:** https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/compare/main...infra/workspace-setup-ci-railway

---

## Title

infra: Workspace setup, CI hardening, Railway deploy readiness

## Description

### Summary

Full workspace preparation per Constitution V3 and CADRE_TRAVAIL. No functional changes.

### Changes

#### Workspace hardening
- `.gitignore`: Exclude `.env`, `.env.local`, `.env.*.local` (no secrets in repo)
- `.vscode/extensions.json`: Recommended extensions (Python, Pylance, Ruff, YAML, GitLens, EditorConfig, Docker)
- `.editorconfig`: Indent 4, UTF-8, trim trailing whitespace

#### Local execution
- `docs/RUNBOOK.md`: Bootstrap steps (venv, docker compose, migrations, pytest, branch strategy)

#### CI
- Add `python -m compileall src/ -q` step per CADRE_TRAVAIL

#### Railway deploy
- `Procfile`: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- `docs/RAILWAY_DEPLOY.md`: Env vars, migrations, healthcheck

#### Deliverable
- `docs/ENVIRONMENT_STATUS_REPORT.md`: Constitution summary, tooling, CI status, Railway checklist

### Risks

Low. Additive only; no code logic modified.

### Rollback plan

Revert branch or drop commits; no DB or config migrations to undo.
