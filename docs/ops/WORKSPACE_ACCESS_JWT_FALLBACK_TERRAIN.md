# Accès workspace en pilote terrain — `WORKSPACE_ACCESS_JWT_FALLBACK`

## Problème

`require_workspace_access` refuse l’accès (**403** — `workspace.read requis`) si l’utilisateur n’a ni ligne dans `workspace_memberships`, ni rôle tenant RBAC avec la permission `workspace.read`, et n’est pas **JWT `admin`**.

Les comptes terrain connectés avec les rôles JWT legacy (`buyer`, `viewer`, etc.) peuvent donc être bloqués alors que le produit n’a pas encore provisionné les memberships.

## Solution pragmatique (opt-in)

Variable d’environnement **`WORKSPACE_ACCESS_JWT_FALLBACK`** (alias **`DMS_WORKSPACE_ACCESS_JWT_FALLBACK`**), **bool**, défaut **`false`**.

Si **`true`** : après vérification **404 workspace** + **alignement tenant**, tout utilisateur dont le **rôle JWT** est l’un de `admin`, `manager`, `buyer`, `viewer`, `auditor` (ensemble `rbac.ROLES`) et qui, une fois projeté sur la matrice V5.2, possède **`workspace.read`**, reçoit l’accès **sans** requête membership.

- Un **log WARNING** est émis à chaque autorisation par ce chemin (grep `JWT_FALLBACK` en prod).
- **Ne pas** activer en production finale si la gouvernance exige des memberships par workspace.

## Activation (ex. Railway)

1. Service **API FastAPI** : ajouter  
   `WORKSPACE_ACCESS_JWT_FALLBACK=true`  
   (ou `DMS_WORKSPACE_ACCESS_JWT_FALLBACK=true`).
2. **Redémarrer** le service (pas de rebuild image obligatoire si env runtime lu au démarrage).

## Désactivation (produit prêt)

1. Provisionner `workspace_memberships` (et/ou `user_tenant_roles` + `workspace.read`) pour les utilisateurs réels.
2. Passer la variable à **`false`** ou la supprimer.
3. Redémarrer l’API.

## Limites (à connaître avant prod)

- **`require_rbac_permission`** (ex. routes M16 avec `permission="evaluation.write"`) continue d’exiger une ligne **`user_tenant_roles`** + permission en base. Le fallback **ne** couvre **pas** ces chemins : pour des tests d’écriture M16 complets, il faut des rôles RBAC provisionnés ou désactiver temporairement ces routes.
- **`guard()`** (agent avec `workspace_id`, uploads, etc.) : si fallback actif, passer **`role`** dans le dict `user` (voir `agent.py`) ; la permission métier est vérifiée sur la matrice V5.2 du rôle projeté. **M-CTO-V53-C** : les permissions listées dans `WRITE_PERMISSIONS` (`guard.py` — écriture / scellement / upload / marché write) **ne** sont **pas** accordées via JWT fallback : une ligne `workspace_memberships` (ou chemin RBAC DB équivalent) reste obligatoire.

## Code

- `src/core/config.py` — champ `WORKSPACE_ACCESS_JWT_FALLBACK`.
- `src/couche_a/auth/workspace_access.py` — mapping legacy → V5.2 + `has_permission(..., "workspace.read")` + `legacy_jwt_to_v52_role`.
- `src/auth/guard.py` — même flag, membership synthétique si la permission JWT/V5.2 est accordée.
- `src/api/routers/agent.py` — `user` enrichi avec `"role"` pour le fallback.

## Tests

- `tests/unit/test_workspace_access_jwt_fallback.py` — mapping des rôles legacy.
