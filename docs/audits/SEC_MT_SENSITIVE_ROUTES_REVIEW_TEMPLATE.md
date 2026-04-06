# Gabarit de revue — routes « sensibles » sans case-guard dans l’arbre deps (DD-005)

**Contexte :** [`scripts/audit_fastapi_auth_coverage.py`](../../scripts/audit_fastapi_auth_coverage.py) marque des routes avec `SENS=yes` et `GUARD=no` lorsque `require_case_access` (ou variantes listées dans le script) n’apparaît pas dans l’**arbre des dépendances FastAPI**. La mitigation peut être **RLS**, **logique dans le corps du handler**, ou **guard manquant réel**.

**Source brute :** [`docs/audits/artifacts/sec_mt_01_main_app.txt`](artifacts/sec_mt_01_main_app.txt) (régénérer après changement de routes).

## Pour chaque route listée

| Champ | Question |
|-------|----------|
| Path | Copier depuis l’audit. |
| Auth | JWT / session requis ? |
| Mitigation | RLS `dm_app` ? filtre `tenant_id` / `workspace_id` en SQL ? autre ? |
| Verdict | **OK** / **À corriger** / **À tester** |
| Test | Référence test d’intégration ou manuel (ex. cross-tenant). |

## Routes typiques à clarifier (exemples DD)

- Chemins `/api/cases/{case_id}/...` sans guard dans deps — vérifier accès case côté handler ou RLS.
- `/api/download/{case_id}/{kind}`, `/api/memory/{case_id}`, `/api/m14/evaluations/{case_id}` — même discipline.

## Barrière CI

Ne pas assouplir les `--fail-prefix` dans [`.github/workflows/ci-main.yml`](../../.github/workflows/ci-main.yml) sans ADR et validation CTO.
