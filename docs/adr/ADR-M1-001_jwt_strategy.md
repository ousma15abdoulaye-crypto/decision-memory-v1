# ADR-M1-001 — Stratégie JWT pour le nouveau moteur auth V4.1.0

**Statut :** Accepté
**Date :** 2026-02-27
**Milestone :** M1 Security Baseline
**Auteur :** Abdoulaye Ousmane — CTO/Founder

---

## Contexte

Le repo possède un système auth existant (`src/auth.py`) basé sur `python-jose` +
`passlib`, fonctionnel mais non conforme au freeze V4.1.0 :

- Access token TTL : 8 heures (trop large)
- Pas de `jti` (révocation impossible sans full-scan DB)
- Pas de refresh token
- `SECRET_KEY` avec valeur par défaut hardcodée (risque sécurité)
- Pas de `token_blacklist` en DB

Ce système legacy reste intact (décision humaine 2026-02-27).
`src/couche_a/auth/jwt_handler.py` est un **nouveau moteur isolé** — sans remplacement
du legacy en M1. Le raccordement sera fait via mandat dédié ultérieur.

---

## Décision

### Algorithme
`HS256` — symétrique, suffisant pour la phase beta mono-tenant Mali.
Asymétrique (RS256) envisageable post-beta si multi-tenant.

### Claims obligatoires
| Claim | Valeur | Raison |
|---|---|---|
| `sub` | `user_id` (str) | Identifiant sujet standard RFC 7519 |
| `role` | rôle utilisateur | Vérification RBAC sans aller en DB |
| `jti` | `uuid4` unique | Révocation ciblée via `token_blacklist` |
| `iat` | timestamp émission | Audit, détection anomalies |
| `exp` | timestamp expiration | Invalidation automatique |
| `type` | `'access'` \| `'refresh'` | Rejet d'un refresh là où un access est attendu |

### TTL
- Access token : **30 min** (env `JWT_ACCESS_TTL_MINUTES`, défaut 30)
- Refresh token : **7 jours** (env `JWT_REFRESH_TTL_DAYS`, défaut 7)

Justification : 30 min limite la fenêtre d'exploitation d'un token volé.
Le refresh permet de maintenir la session sans ré-authentification fréquente.

### Révocation
- `logout` → `jti` inscrit dans `token_blacklist` (expires_at = exp du token)
- Chaque validation → vérifie `jti` absent de `token_blacklist`
- Nettoyage TTL via `fn_cleanup_expired_tokens()` appelé par job applicatif

### Rotation refresh
- Refresh valide → émet nouveau access + **nouveau** refresh
- Ancien refresh `jti` → `token_blacklist` immédiatement (one-time use)

### Sécurité démarrage
- `SECRET_KEY` absent de ENV → **`ValueError` levée au démarrage**
- Jamais de secret hardcodé dans le code source

---

## Périmètre M1 — utilitaires uniquement

Fonctions livrées dans `src/couche_a/auth/jwt_handler.py` :
```
create_access_token(user_id, role, db_conn) → str
create_refresh_token(user_id, role, db_conn) → str
verify_token(token, expected_type, db_conn) → dict
revoke_token(jti, expires_at, db_conn) → None
rotate_refresh_token(refresh_token, db_conn) → tuple[str, str]
```

**Pas d'endpoints dans ce module.**
Les endpoints `/auth/*` restent dans `src/auth_router.py` (legacy, non modifié en M1).
Raccordement via mandat dédié ultérieur.

---

## Dépendances

`python-jose[cryptography]==3.3.0` — déjà présent dans `requirements.txt`.
Aucune nouvelle dépendance requise.

---

## Conséquences

| Aspect | Décision |
|---|---|
| `src/auth.py` | Non modifié (legacy toléré) |
| `src/couche_a/auth/jwt_handler.py` | Nouveau moteur — isolé |
| `token_blacklist` | Créée par migration 037 |
| Endpoints existants `/auth/*` | Non modifiés en M1 |
| Tests legacy `tests/test_rbac.py` | Non modifiés |

---

## Cohabitation legacy — stratégie M2

**Situation M1 :**

Deux systèmes auth coexistent intentionnellement (décision CTO 2026-02-27) :

| Système | Fichier | TTL | Claims | Révocation |
|---|---|---|---|---|
| Legacy | `src/auth.py` | 8h | `sub=username`, `role_id=int` | Aucune |
| V4.1.0 | `src/couche_a/auth/jwt_handler.py` | 30min/7j | `sub=user_id`, `role=str`, `jti` | `token_blacklist` |

**Isolation garantie :**
- Aucune dépendance croisée entre les deux modules
- `tests/test_rbac.py` (legacy) : 5 tests sur `/auth/token`, `/auth/register`, `/auth/me`
- `tests/auth/` (V4.1.0) : fixtures propres, zéro appel aux endpoints legacy

**Stratégie de basculement M2 UNIFY SYSTEM :**
1. Raccorder `src/couche_a/auth/` aux endpoints existants (`/auth/token`, `/auth/me`)
2. Migrer les 5 tests legacy vers les nouvelles fixtures
3. Supprimer `src/auth.py` après validation complète
4. `DROP COLUMN role_id` sur `users` (DETTE-M1-04)

**Condition bloquante :** décision humaine explicite avant toute bascule.

---

## Dette documentée

| Item | Réf TECHNICAL_DEBT |
|---|---|
| Raccordement nouveau moteur → endpoints existants | DETTE-M1-02 — M2 UNIFY SYSTEM |
| Remplacement `src/auth.py` par `src/couche_a/auth/` | DETTE-M1-02 |
| Migration `users.id` integer → UUID | DETTE-M1-01 — post-beta |
| `users.created_at` TEXT → TIMESTAMPTZ | DETTE-M1-03 — post-beta |
| `users.role_id` → DROP COLUMN | DETTE-M1-04 — M2 |
