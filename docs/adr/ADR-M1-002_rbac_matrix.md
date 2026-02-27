# ADR-M1-002 — Matrice RBAC V4.1.0

**Statut :** Accepté
**Date :** 2026-02-27
**Milestone :** M1 Security Baseline
**Auteur :** Abdoulaye Ousmane — CTO/Founder

---

## Contexte

Le système legacy (`src/auth.py`) utilise un modèle `role_id` (integer FK → table `roles`)
avec les rôles `admin`, `procurement_officer`. Ce modèle ne correspond pas au freeze V4.1.0
qui définit 5 rôles avec colonne `role TEXT CHECK(...)` directement sur `users`.

**Décision humaine 2026-02-27 :** `src/auth.py` et la table `users` legacy restent intacts.
`src/couche_a/auth/rbac.py` définit la matrice cible V4.1.0 comme **nouveau module isolé**.
Le raccordement legacy → nouveau moteur = mandat dédié ultérieur.

---

## Rôles V4.1.0

| Rôle | Description |
|---|---|
| `admin` | Accès total — gestion système, users, toutes opérations |
| `manager` | Gestion dossiers + fournisseurs + comités, pas d'ops admin |
| `buyer` | Création dossiers + lecture référentiels |
| `viewer` | Lecture seule — toutes ressources non sensibles |
| `auditor` | Lecture seule — accès lecture pour audit, pas d'admin_ops |

---

## Matrice de permissions

```
role      | cases | vendors | committees | admin_ops
──────────┼───────┼─────────┼────────────┼──────────
admin     |  CRUD |  CRUD   |    CRUD    |   ALL
manager   |  CRUD |  CRU    |    CRUD    |    -
buyer     |  CR   |  READ   |    READ    |    -
viewer    |  READ |  READ   |    READ    |    -
auditor   |  READ |  READ   |    READ    |    -
```

**Légende :**
- `C` = Create · `R` = Read · `U` = Update · `D` = Delete
- `ALL` = toutes opérations admin (gestion users, migrations, config)
- `-` = accès interdit

---

## Implémentation M1 — `src/couche_a/auth/rbac.py`

```python
ROLES = {"admin", "manager", "buyer", "viewer", "auditor"}

PERMISSIONS = {
    "admin":   {"cases": {"C","R","U","D"}, "vendors": {"C","R","U","D"},
                "committees": {"C","R","U","D"}, "admin_ops": {"ALL"}},
    "manager": {"cases": {"C","R","U","D"}, "vendors": {"C","R","U"},
                "committees": {"C","R","U","D"}, "admin_ops": set()},
    "buyer":   {"cases": {"C","R"}, "vendors": {"R"},
                "committees": {"R"}, "admin_ops": set()},
    "viewer":  {"cases": {"R"}, "vendors": {"R"},
                "committees": {"R"}, "admin_ops": set()},
    "auditor": {"cases": {"R"}, "vendors": {"R"},
                "committees": {"R"}, "admin_ops": set()},
}
```

---

## Dépendances FastAPI — `src/couche_a/auth/dependencies.py`

```python
get_current_user(token, db_conn) → UserClaims
    # Extrait + valide JWT (via jwt_handler.verify_token)
    # Vérifie jti absent de token_blacklist
    # Retourne UserClaims(user_id, role, jti)

require_role(*roles) → Callable
    # Retourne une dépendance FastAPI
    # Vérifie que current_user.role ∈ roles
    # Lève HTTPException 403 si non autorisé

require_any_role(*roles) → Callable
    # Idem avec logique OR explicite
```

---

## SOD Comité — hors scope M1

La règle "sourcing lead ≠ membre votant" (SCI §5.4) est une **contrainte métier comité**,
pas une contrainte RBAC générique.

**Décision :** non implémentée dans `require_role()` en M1.
Réservée **M16B** — logique métier comité dédiée.
Documentée dans `TECHNICAL_DEBT.md` section M16B.

---

## Audit log permissions — hors scope M1

Les permissions sur `audit_log` sont réservées **M1B**.
La matrice ci-dessus ne couvre pas `audit_log`.

---

## Conséquences

| Aspect | Décision |
|---|---|
| 5 rôles V4.1.0 | Définis dans `src/couche_a/auth/rbac.py` |
| Matrice permissions | Centralisée, non dispersée dans les endpoints |
| Rôles legacy (`procurement_officer`) | Non modifiés — dans `src/auth.py` legacy |
| SOD comité | TECHNICAL_DEBT, M16B |
| `audit_log` permissions | TECHNICAL_DEBT, M1B |
| Raccordement legacy | Mandat dédié post-M1 |

---

## Migration DB associée — 037

La colonne `role TEXT` est ajoutée sur `users` de manière non destructive :
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS organization TEXT;
```

Pas de `CHECK` contrainte en M1 : les données legacy existantes (`role_id` integer)
ne sont pas encore alignées. Contrainte ajoutée via mandat dédié après backfill.

---

## Dette documentée

| Item | Réf TECHNICAL_DEBT |
|---|---|
| Rôle `procurement_officer` legacy → mapper vers 5 rôles V4.1.0 | Section M1 — mandat dédié |
| CHECK constraint sur `users.role` | Après backfill données legacy |
| SOD comité dans RBAC | M16B |
| `audit_log` permissions | M1B |
