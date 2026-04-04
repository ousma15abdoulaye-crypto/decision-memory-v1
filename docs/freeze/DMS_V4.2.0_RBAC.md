# DMS V4.2.0 — RBAC PAR ACTES MÉTIER

**Référence** : DMS-V4.2.0-ADDENDUM-WORKSPACE §V
**Date freeze** : 2026-04-04
**Statut** : FREEZE DÉFINITIF après hash

---

## Permissions (17)

| ID | Label | Description |
|---|---|---|
| `workspace.view` | Voir le workspace | Accès lecture au workspace et ses artefacts |
| `workspace.create` | Créer un workspace | Initier un nouveau processus procurement |
| `workspace.manage_members` | Gérer les membres | Ajouter/retirer des membres du workspace |
| `workspace.view_bundles` | Voir les bundles | Accès lecture aux bundles fournisseurs |
| `workspace.view_scores` | Voir les scores | Accès lecture à la matrice d'évaluation |
| `workspace.view_market` | Voir le contexte marché | Écarts mercuriale dans le contexte du workspace |
| `committee.view_session` | Voir la session | Accès lecture à la session de comité |
| `committee.add_comment` | Commenter en délibération | Ajouter un commentaire tracé |
| `committee.challenge_score` | Contester un score | Émettre une contestation formelle |
| `committee.request_clarif` | Demander clarification | Demander un éclaircissement tracé |
| `committee.declare_conflict` | Déclarer conflit intérêt | Déclarer un conflit d'intérêt formel |
| `committee.seal_session` | Sceller la session | Sceller la délibération — irréversible |
| `committee.manage_members` | Gérer composition comité | Ajouter/retirer des membres du comité |
| `market.view` | Consulter mémoire marché | Accès W2 hors processus — mercuriales, signaux |
| `market.annotate` | Annoter données marché | Contribuer aux données marché |
| `admin.manage_users` | Gérer utilisateurs | Créer, désactiver, modifier les utilisateurs |
| `admin.view_audit` | Consulter audit complet | Accès aux logs d'audit et traçabilité |

---

## Rôles pilote SCI Mali (6)

| ID | Label | Description |
|---|---|---|
| `procurement_officer` | Agent procurement | Crée et gère les workspaces, voit bundles/scores/marché |
| `committee_president` | Président du comité | Toutes permissions comité + scellement + gestion membres |
| `committee_member` | Membre votant | Lecture + commentaire + contestation + conflit |
| `committee_observer` | Observateur | Lecture seule workspace + comité |
| `market_analyst` | Analyste marché | Consulte et annote W2 hors processus |
| `tenant_admin` | Administrateur tenant | Toutes permissions — gestion utilisateurs et audit |

---

## Matrice rôle × permission

| Permission | procurement_officer | committee_president | committee_member | committee_observer | market_analyst | tenant_admin |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| workspace.view | X | X | X | X | X | X |
| workspace.create | X | | | | | X |
| workspace.manage_members | X | | | | | X |
| workspace.view_bundles | X | X | X | X | | X |
| workspace.view_scores | X | X | X | X | | X |
| workspace.view_market | X | X | | | X | X |
| committee.view_session | X | X | X | X | | X |
| committee.add_comment | | X | X | | | X |
| committee.challenge_score | | X | X | | | X |
| committee.request_clarif | | X | | | | X |
| committee.declare_conflict | | X | X | | | X |
| committee.seal_session | | X | | | | X |
| committee.manage_members | | X | | | | X |
| market.view | X | X | | | X | X |
| market.annotate | | | | | X | X |
| admin.manage_users | | | | | | X |
| admin.view_audit | | | | | | X |

---

## Incompatibilités de rôles

| Combinaison | Statut | Raison |
|---|---|---|
| `procurement_officer` + `committee_president` dans le MÊME workspace | **INTERDIT** | Séparation des tâches SCI §5.4 — sourcing lead ≠ président |
| `procurement_officer` + `committee_member` votant dans le MÊME workspace | **WARNING** | Acceptable uniquement si équipe < 5 personnes (terrain Mopti) — tracé |
| `committee_president` + `committee_member` | **INTERDIT** | Un président est un membre par nature — pas de double rôle |
| `tenant_admin` + tout rôle | **AUTORISÉ** | L'admin a toutes les permissions — pas de conflit |

---

## Migration depuis RBAC V4.1.0

### Schéma V4.1.0

```sql
users.role IN ('admin','manager','buyer','viewer','auditor')
```

### Mapping vers V4.2.0

| Rôle V4.1.0 | Rôle V4.2.0 | Notes |
|---|---|---|
| `admin` | `tenant_admin` | Toutes permissions |
| `manager` | `procurement_officer` | Crée et gère les workspaces |
| `buyer` | `procurement_officer` | Même rôle que manager dans le pilote |
| `viewer` | `committee_observer` | Lecture seule |
| `auditor` | `tenant_admin` | Sous-ensemble audit — l'admin couvre |

### Script de migration

```sql
INSERT INTO user_tenant_roles (user_id, tenant_id, role_id)
SELECT
    u.id,
    t.id,
    CASE u.role
        WHEN 'admin'   THEN 'tenant_admin'
        WHEN 'manager' THEN 'procurement_officer'
        WHEN 'buyer'   THEN 'procurement_officer'
        WHEN 'viewer'  THEN 'committee_observer'
        WHEN 'auditor' THEN 'tenant_admin'
    END
FROM users u
CROSS JOIN tenants t
WHERE t.code = 'sci_mali'
ON CONFLICT (user_id, tenant_id, role_id) DO NOTHING;
```

---

*Gelé après hash. Tout amendement → DMS_V4.2.1_PATCH.md*
