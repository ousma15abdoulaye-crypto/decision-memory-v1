# PR #234 — alignement après fusion des branches

Branche **active et canonique** : `chore/copilot-tenant-pr-alignment` (PR **#234**).  
Historique : le contenu de l’ancienne branche distante `feat/exit-plan-align-01-enterprise-bundle` (supprimée sur `origin`) a été **fast-forward** ici depuis l’ancêtre `0db837d`, puis commits inv10 / Black / doc d’alignement.

## Rôles respectifs (éviter la redondance)

| Source | Rôle | Pas de doublon avec |
|--------|------|---------------------|
| **Agents / commit `0db837d`** | Bundle tenant : RLS 051, auth extractions, critères, JWT `tenant_id`, `user_tenants`, CI M12 / docs alignement | — |
| **PR Copilot (fermée / non mergée telle quelle)** | Proposait `org_id` JWT + `require_org_id` + filtre liste **owner-only** | **Non repris** : un seul claim **`tenant_id`** ; liste non-admin = **tenant + owner** (cohérent `require_case_access`) |
| **Invariant inv10 + `inv10_tenant_sql_scan.py`** | Scan statique SQL vs tables RLS **051** ; warnings **vendors** ; docstrings / ruff | Complète le bundle ; ne remplace pas RLS runtime |
| **Styles / tests (`31cbd97` → `772acf6`, puis `93f637b`)** | Ruff, Black (CI), critères API / intégration `conftest` | Orthogonal au métier tenant |

## Vérifications rapides

- `ruff check` sur chemins inv10 + `cases.py` : OK  
- `pytest tests/invariants/test_inv_10_tenant_isolation.py` : OK (2 warnings vendors attendus)

## Description PR GitHub

Utiliser le gabarit `docs/audits/PR_BODY_exit_plan_align_01.md` ou le compléter avec le SHA courant de cette branche après push.
