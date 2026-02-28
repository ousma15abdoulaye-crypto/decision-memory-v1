# ADR-M2-001 — Unification du système auth (UNIFY SYSTEM)

**Statut :** Accepté
**Date :** 2026-02-27
**Milestone :** M2 UNIFY SYSTEM
**Auteur :** Abdoulaye Ousmane — CTO/Founder
**Branche :** feat/m2-unify-auth-system
**Prérequis :** v4.1.0-m1b-done · CI 573 passed · alembic head 038_audit_hash_chain

---

## Contexte

### État des deux systèmes auth au PROBE M2

#### Système legacy — `src/auth.py`

| Attribut | Valeur |
|---|---|
| Algorithme | HS256 |
| Variable ENV secret | `JWT_SECRET` |
| Secret fallback hardcodé | `"CHANGE_IN_PRODUCTION_USE_OPENSSL_RAND_HEX_32"` |
| TTL access | 480 min (8h) |
| Refresh token | Absent |
| Claims | `sub` (user_id str) · `exp` |
| Claims absents | `jti` · `role` · `iat` · `type` |
| Modèle user retourné | `dict` : `id` (INTEGER) · `username` · `email` · `full_name` · `role_name` · `is_active` · `is_superuser` |
| Dépendances | python-jose · passlib/bcrypt · SQLAlchemy (text) |
| Révocation | Absente |

#### Moteur V4.1.0 — `src/couche_a/auth/`

| Attribut | Valeur |
|---|---|
| Algorithme | HS256 |
| Variable ENV secret | `SECRET_KEY` (primaire) puis `JWT_SECRET` (fallback) |
| Secret absent | `ValueError` levée au démarrage |
| TTL access | 30 min (env `JWT_ACCESS_TTL_MINUTES`) |
| TTL refresh | 7j (env `JWT_REFRESH_TTL_DAYS`) |
| Claims | `sub` (user_id str) · `role` · `jti` (UUID4) · `iat` · `exp` · `type` |
| Modèle user retourné | `UserClaims(user_id: str, role: str, jti: str)` — dataclass frozen |
| Dépendances | python-jose · psycopg (pas passlib) |
| Révocation | `token_blacklist` DB (migration 037) |

### Point d'entrée réel de l'application

**`main.py` (racine)** — confirmé par PROBE.

- Les tests font `from main import app`
- `main.py` importe directement les routers et monte l'app FastAPI
- `src/api/main.py` est un second point d'entrée indépendant (non utilisé par les tests ni Railway)

### Liste exhaustive des dépendances legacy auth dans src/

| Fichier | Symboles importés | Impact |
|---|---|---|
| `main.py` (racine) | `CurrentUser` | Import orphelin — non utilisé dans les routes de main.py |
| `src/auth_router.py` | `ACCESS_TOKEN_EXPIRE_MINUTES`, `CurrentUser`, `authenticate_user`, `create_access_token`, `create_user` | Cœur des 3 endpoints `/auth/*` |
| `src/api/cases.py` | `CurrentUser` | Injection dans 3 endpoints `/api/cases*` |
| `src/api/routes/extractions.py` | `get_current_user` | `Depends(get_current_user)` dans `POST /documents/{id}/corrections` |
| `src/couche_a/routers.py` | `CurrentUser`, `check_case_ownership` | Upload DAO/offer + contrôle ownership |
| `src/couche_a/scoring/api.py` | `CurrentUser` | `POST /api/scoring/calculate` |

### Liste des tests legacy à migrer

| Fichier | Import legacy | Impact |
|---|---|---|
| `tests/test_auth.py` | `from src.auth import ALGORITHM, SECRET_KEY` | `test_token_expiration` décode le token avec la clé legacy |
| `tests/test_rbac.py` | Aucun import direct | Teste les endpoints via TestClient — adapté si `UserResponse` change |

### Risques identifiés

1. **Incompatibilité tokens** — Les tokens legacy sont rejetés par `verify_token()` (jti absent). Toute session active en production sera invalidée lors de la bascule.
2. **Modèle user dichotomique** — `dict` legacy vs `UserClaims` dataclass — les endpoints doivent être adaptés individuellement.
3. **check_case_ownership** défini dans `src/auth.py` — logique à déplacer in-line dans `src/couche_a/routers.py`.
4. **authenticate_user / create_user** — fonctions DB dans `src/auth.py`. Si ce fichier est supprimé en ÉTAPE 3, elles doivent être extraites dans `src/api/auth_helpers.py`.

---

## Vérification encoding user_id dans les tokens V4.1.0

**Grep effectué sur `src/couche_a/auth/*.py` :**

```python
# jwt_handler.py ligne 55
"sub": str(user_id)  # toujours converti en string
```

`create_access_token(user_id: str, ...)` accepte une str quelconque.
En M2, le login endpoint appellera `create_access_token(str(user["id"]), role)` où `user["id"]` est l'INTEGER legacy.

**Conclusion :** `user_id` dans le token = `"123"` (str de l'int DB).
`int(current_user.user_id)` est **safe** — aucun STOP-M2-3 sur cases.py.

---

## Décision

### Stratégie de bascule choisie

Migration endpoint par endpoint, dans l'ordre défini ci-dessous.
Cohabitation transitoire autorisée pendant M2 uniquement.
Pas de feature flag runtime. Pas de proxy intermédiaire.
`src/couche_a/auth/*` non modifié (M1 fermé).

### Compatibilité tokens — tranchée explicitement

**INCOMPATIBLES.** Les tokens legacy ne peuvent pas être validés par le moteur V4.1.0.

- `verify_token()` lève `ValueError("Token sans jti — rejeté")` sur tout token legacy.
- Conséquence assumée : toute session active lors de la bascule `/auth/token` est invalidée.
- Les utilisateurs devront se reconnecter pour obtenir un token V4.1.0.
- Aucune tentative de compatibilité descendante durable.
- Documenté dans TECHNICAL_DEBT.md mise à jour.

### Gestion helpers DB legacy

Si `src/auth.py` est supprimé en ÉTAPE 3, les fonctions suivantes sont déplacées — logique inchangée — dans `src/api/auth_helpers.py` (nouveau fichier autorisé par mandat) :

- `authenticate_user()` — vérification bcrypt + DB
- `create_user()` — INSERT users avec `role_id=2`
- `verify_password()` / `get_password_hash()` — helpers bcrypt
- `get_user_by_username()` / `get_user_by_id()` — queries DB

`src/auth_router.py` importera depuis `src/api/auth_helpers.py` au lieu de `src/auth.py`.
Commit séparé : `"feat(m2): extract DB auth helpers to src/api/auth_helpers.py"`.

`check_case_ownership()` est inlinée directement dans `src/couche_a/routers.py` — logique simple ne justifiant pas un module dédié.

### DETTE-M1-04 — périmètre exact en M2

| Action | Statut M2 |
|---|---|
| Migrations lectures de rôle → `UserClaims.role` | ✅ Fait en M2 |
| `create_user(role_id=2)` | Inchangé pendant M2 — colonne existe en DB |
| `DROP COLUMN role_id` | Reporté M2B (schéma inchangé en M2) |

### Ordre de migration des 6 fichiers

Ordre choisi (décision CTO 2026-02-27) : import orphelin éliminé en premier, cœur legacy (`src/auth_router.py`) touché en dernier. Si un STOP-M2-* survient sur `src/auth_router.py`, les 5 autres fichiers sont déjà propres — scope résiduel minimal.

| Ordre | Fichier | Complexité | Justification |
|---|---|---|---|
| 1 | `main.py` (racine) | Triviale | Import orphelin ligne 31 — éliminé en premier, ne protège rien |
| 2 | `src/couche_a/scoring/api.py` | Minimale | `CurrentUser` utilisé pour présence seulement — cast direct vers `UserClaims` |
| 3 | `src/api/cases.py` | Faible | `user["id"]` → `int(current_user.user_id)` — user_id = str(int) confirmé safe |
| 4 | `src/api/routes/extractions.py` | Faible | `get_current_user` (dict) → `get_current_user` (UserClaims) — adapter `.get("id")` |
| 5 | `src/couche_a/routers.py` | Moyenne | `CurrentUser` + `check_case_ownership` → inline de la logique ownership |
| 6 | `src/auth_router.py` | Haute | 3 endpoints `/auth/*` + rechargement DB pour `GET /me` + émission token V4.1.0 · touché en dernier |

Les tests legacy sont adaptés à chaque étape de migration de l'endpoint correspondant.

### Règle de cohabitation transitoire

- Pendant M2, les fichiers non encore migrés continuent d'importer `src/auth.py`.
- `src/auth.py` n'est pas supprimé avant que tous les imports aient été migrés (ÉTAPE 3).
- À chaque commit, la CI doit être verte sur la suite complète (STOP-M2-5).

### Condition exacte de suppression de `src/auth.py`

```
✓ Tous les 6 fichiers src/ migrés (imports résiduels à zéro)
✓ tests/test_auth.py migré (import ALGORITHM, SECRET_KEY supprimé)
✓ grep "from src.auth import\|from auth import" src/ tests/ → 0 résultat
✓ CI complète verte
✓ src/api/auth_helpers.py créé et importé par src/auth_router.py
```

Si une condition manque → `src/auth.py` conservé, DETTE-M1-02 documentée en réduction partielle.

---

## Compatibilité tokens — détail technique

| Attribut | Legacy | V4.1.0 | Compatible ? |
|---|---|---|---|
| Algorithme | HS256 | HS256 | ✅ |
| Secret ENV | `JWT_SECRET` | `SECRET_KEY` ou `JWT_SECRET` | ✅ si même valeur |
| Claim `jti` | Absent | Obligatoire | ❌ |
| Claim `type` | Absent | Obligatoire (`"access"`) | ❌ |
| Claim `role` | Absent | Obligatoire | ❌ |

`verify_token()` rejette tout token legacy sur la première vérification `jti`.
**Décision assumée : invalidation des sessions actives au moment de la bascule de `/auth/token`.**

---

## Plan de rollback (< 5 minutes)

### Commits visés (ordre inverse d'application)

En cas d'incident sur staging Railway après le merge :

```bash
# Rollback niveau 1 — suppression src/auth.py uniquement
git revert <sha-commit-suppression-auth.py>
git push origin main
# Railway redéploie automatiquement

# Rollback niveau 2 — reroutage auth_router.py + helpers
git revert <sha-commit-auth-router-migration>
git push origin main

# Rollback niveau 3 — retour complet pre-M2
git revert <sha-commit-couche-a-routers>
git revert <sha-commit-extractions>
git revert <sha-commit-cases>
git revert <sha-commit-scoring>
git push origin main
```

### Conditions de rollback

- Smoke staging : `POST /auth/token` retourne 500 ou timeout
- `GET /auth/me` avec token V4.1.0 retourne 401 inattendu
- `POST /api/cases` rejette des requêtes authentifiées valides

### Condition de non-rollback

Si l'erreur n'est pas liée à la couche auth (erreur DB, réseau Railway, autre router), ne pas rollback auth par réflexe.

---

## Alternatives rejetées

| Alternative | Motif de rejet |
|---|---|
| Cohabitation longue (deux systèmes en parallèle) | DETTE-M1-02 — crée de la confusion, complexifie les tests, maintien à double |
| Feature flag runtime (toggle auth par env var) | Complexité inutile, surface d'erreur, contraire à la doctrine M2 |
| Proxy intermédiaire (adapter tokens legacy → V4.1.0) | Cohabitation durable interdite · complexité élevée · STOP-M2 potentiel |
| Modification de `src/couche_a/auth/*` | M1 FERMÉ — STOP-M2-6 |
| Migration en bloc (tous les fichiers en un seul commit) | Impossible à rollback · CI non vérifiée entre chaque endpoint |

---

## Conséquences

### DETTE-M1-02 — statut après M2

Si toutes les conditions de suppression sont remplies :
- DETTE-M1-02 **soldée** — `src/auth.py` supprimé, cohabitation terminée.

Si conditions non remplies sur un endpoint :
- DETTE-M1-02 **partiellement réduite** — motif documenté honnêtement ici et dans TECHNICAL_DEBT.md.

### Tests migrés

| Fichier | Action |
|---|---|
| `tests/test_auth.py` | `from src.auth import ALGORITHM, SECRET_KEY` → utiliser constantes locales ou fixtures V4.1.0 |
| `tests/test_rbac.py` | Adapter si `UserResponse` change (champ `role_name` → `role`) |

### Fichiers créés

- `docs/adr/ADR-M2-001_auth_unification.md` (ce document)
- `src/api/auth_helpers.py` (si suppression `src/auth.py`)

### Fichiers modifiés

- `main.py` (racine) — suppression import orphelin
- `src/auth_router.py` — reroutage vers moteur V4.1.0
- `src/api/cases.py` — `CurrentUser` → `UserClaims`
- `src/api/routes/extractions.py` — `get_current_user` → `UserClaims`
- `src/couche_a/routers.py` — `CurrentUser` + inline `check_case_ownership`
- `src/couche_a/scoring/api.py` — `CurrentUser` → `UserClaims`
- `tests/test_auth.py` — import legacy supprimé
- `TECHNICAL_DEBT.md` — DETTE-M1-02 mise à jour

### Fichiers inchangés (garantis)

- `src/couche_a/auth/*` — M1 fermé
- `src/couche_a/audit/*` — M1B fermé
- `tests/auth/*` — M1 fermé
- `tests/audit/*` — M1B fermé
- `alembic/versions/*` — zéro migration en M2

---

## Séquence de commits M2 (plan)

```
commit 1  feat(m2): ADR-M2-001 auth unification
commit 2  feat(m2): remove orphan import in main.py
commit 3  feat(m2): migrate scoring/api.py to couche_a auth
commit 4  feat(m2): migrate cases.py to couche_a auth
commit 5  feat(m2): migrate extractions.py to couche_a auth
commit 6  feat(m2): migrate couche_a/routers.py — inline check_case_ownership
commit 7  feat(m2): extract DB auth helpers to src/api/auth_helpers.py
commit 8  feat(m2): migrate auth_router.py to couche_a auth — /auth/* endpoints
commit 9  feat(m2): remove legacy src/auth.py — DETTE-M1-02 soldée
commit 10 feat(m2): update TECHNICAL_DEBT.md — DETTE-M1-02 soldée
```

---

## Role mapping legacy → V4.1.0

**Contexte :**
Migration 037 a ajouté `users.role TEXT DEFAULT 'viewer'` avec un CHECK sur les valeurs V4.1.0.
Tous les utilisateurs existants ont `users.role = 'viewer'` (DEFAULT appliqué aux lignes existantes).
La colonne `role_name` issue du JOIN avec `roles` (legacy) contient des valeurs hors VALID_ROLES V4.1.0.

**Table `roles` (legacy) constatée en DB :**

| id | name |
|----|------|
| 1  | admin |
| 2  | procurement_officer |
| 3  | viewer |

**VALID_ROLES V4.1.0 :** `admin`, `auditor`, `buyer`, `manager`, `viewer`

**Mapping officiel — Décision CTO 2026-02-28 :**

| Legacy `roles.name`  | V4.1.0 VALID_ROLES | Justification                              |
|----------------------|--------------------|--------------------------------------------|
| `admin`              | `admin`            | Identique                                  |
| `procurement_officer`| `buyer`            | Agent d'achat → rôle achat générique V4.1.0|
| `viewer`             | `viewer`           | Identique                                  |
| autre / inconnu      | `viewer`           | Fallback défensif                          |

**Implémentation :** `src/auth_router.py` — fonction `login()`, variable `_role_mapping`.

**Comportement `viewer` par défaut :**
Dégradation contrôlée et intentionnelle. Un rôle legacy inconnu obtient `viewer` :
accès préservé (peut créer des cases), admin bypass non accordé.
Ce n'est pas une dégradation silencieuse — le mapping est explicite et versionné.

**Test couvrant la décision :**
`tests/test_auth.py::test_procurement_officer_token_carries_buyer_role`
Assert : `payload["role"] == "buyer"` et `payload["role"] != "viewer"`.
Ce test ne peut pas être supprimé sans décision explicite.

**Commit :** `0cb2a06` — `fix(m2): map procurement_officer to buyer role — DETTE-M1-04`

---

**Date :** 2026-02-27
**Auteur :** Agent DMS V4.1.0 — mandat M2 UNIFY SYSTEM
**Validé par :** Abdoulaye Ousmane — CTO/Founder (après ÉTAPE 0)
**Mis à jour :** 2026-02-28 — correction ordre migration + section role mapping
