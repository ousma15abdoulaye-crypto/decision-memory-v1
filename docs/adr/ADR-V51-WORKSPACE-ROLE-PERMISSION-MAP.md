# ADR — Carte rôles workspace × permissions (V5.1)

**Statut** : accepté (documentation de la source de vérité code)  
**Implémentation canonique** : [`src/services/workspace_access_service.py`](../../src/services/workspace_access_service.py)

## Contexte

Les rôles workspace sont stockés en base (`workspace_memberships.role`, alignés migration **092**). Les permissions métier sont des chaînes stables consommées par `require_workspace_permission`, `guard`, et les routers V5.1 / W1 / W3.

## Rôles (`WorkspaceRole`)

| Valeur DB | Description courte |
|-----------|-------------------|
| `committee_chair` | Présidence comité — périmètre élargi + scellage PV. |
| `committee_member` | Membre comité — délibération, pas gestion membres par défaut. |
| `procurement_lead` | Pilotage procurement — gestion workspace / comité / membres. |
| `technical_reviewer` | Revue technique — matrix + clarifications. |
| `finance_reviewer` | Revue financière — `financial.read` / `financial.comment`. |
| `observer` | Lecture large sans mutations sensibles. |
| `auditor` | Lecture + `audit.full`. |

## Matrice (résumé)

La table complète est `WORKSPACE_PERMISSIONS` dans le module service : chaque rôle → `frozenset` de permissions autorisées.

Permissions notables :

- **Lecture / analyse** : `matrix.read`, `deliberation.read`, `financial.read`, `pv.read`, `agent.query`.
- **Écriture délibération** : `deliberation.write`, `deliberation.validate`, `matrix.comment`, `financial.comment`.
- **Comité / PV** : `committee.manage`, `pv.seal` (chair).
- **Membres** : `member.invite`, `member.revoke`.
- **Fichiers** : `bundle.upload`.
- **Audit** : `audit.full` (auditor).

## Écritures sous workspace scellé

`WORKSPACE_WRITE_PERMISSIONS` liste les permissions considérées comme **mutations** : `guard` refuse (HTTP **409**) si le workspace est `sealed`, `closed` ou `cancelled`.

## Conflit d’intérêts (COI)

Pour les permissions `deliberation.validate` et `pv.seal`, une ligne `workspace_memberships` avec `coi_declared=true` **ne compte pas** comme autorisée (logique `_permission_granted_by_rows`).

## Références

- [`src/couche_a/auth/workspace_access.py`](../../src/couche_a/auth/workspace_access.py) — `require_workspace_access`, `require_workspace_permission`
- [`src/auth/guard.py`](../../src/auth/guard.py) — `guard` async (RLS + seal)
- [`docs/ops/V51_ROUTE_GUARD_INVENTORY.md`](../ops/V51_ROUTE_GUARD_INVENTORY.md)
