# NOTE DE TRANSMISSION — M2 UNIFY AUTH SYSTEM

```
Date       : 2026-02-28
Milestone  : M2 — Unify Auth System
Branche    : feat/m2-unify-auth-system (mergée sur main)
Statut     : DONE — tag v4.1.0-m2-done posé sur main
Agent      : DMS V4.1.0
Successeur : Agent M2B (DROP COLUMN role_id + dettes résiduelles)
```

---

## I. ÉTAT DU REPO À LA TRANSMISSION

| Élément | État |
|---|---|
| Branche active | `main` |
| Alembic head | `038_audit_hash_chain` |
| CI locale | **574 passed · 36 skipped · 0 failed** |
| ruff | 0 erreur |
| black | 0 erreur |
| Tag | `v4.1.0-m2-done` — posé sur `main` |
| src/auth.py | **SUPPRIMÉ** (commit `971af4a`) |
| Smoke Railway | **VERT** — 5/5 endpoints validés |

---

## II. CE QUE M2 A LIVRÉ

### Objectif accompli

Décommissionnement complet de `src/auth.py` (système auth legacy).
Tous les endpoints `/auth/*` et dépendants branchés sur `src/couche_a/auth/` (V4.1.0).
DETTE-M1-02 soldée.

---

### Fichiers créés

| Fichier | Rôle |
|---|---|
| `src/api/auth_helpers.py` | Helpers DB extraits de legacy : `authenticate_user`, `create_user`, `get_user_by_username`, `get_user_by_id`, `verify_password`, `get_password_hash` |
| `docs/adr/ADR-M2-001_auth_unification.md` | ADR complète : probe, décisions CTO, ordre migration, rollback |
| `start.sh` | Script de démarrage Railway : `alembic upgrade head` → `uvicorn` |

### Fichiers modifiés

| Fichier | Changement |
|---|---|
| `src/auth_router.py` | Migré vers V4.1.0 — `create_access_token` · `get_current_user` · mapping rôles |
| `src/api/cases.py` | `user["id"]` → `int(user.user_id)` via `UserClaims` |
| `src/api/routes/extractions.py` | `current_user.get("id")` → `current_user.user_id` |
| `src/couche_a/routers.py` | `CurrentUser` → `UserClaims` · `_check_case_ownership` inline |
| `src/couche_a/scoring/api.py` | `CurrentUser` → `UserClaims` |
| `src/ratelimit.py` | `conditional_limit` no-op systématique (bug async/sync wrapper corrigé) |
| `main.py` | Import orphelin `from src.auth import CurrentUser` supprimé · lifespan `RUN_MIGRATIONS_ON_STARTUP` |
| `tests/test_auth.py` | Imports legacy supprimés · `test_procurement_officer_token_carries_buyer_role` ajouté |
| `tests/conftest.py` | `SECRET_KEY` env var explicite |
| `Procfile` | `web: bash start.sh` |
| `TECHNICAL_DEBT.md` | DETTE-M1-02 SOLDÉE · DETTE-M1-04 PARTIELLEMENT SOLDÉE |

### Fichier supprimé

```
src/auth.py  — système auth legacy — SUPPRIMÉ (commit 971af4a)
```

---

### Décision de mapping rôles (ADR-M2-001 §Role mapping)

```python
_role_mapping = {
    "admin":                "admin",
    "procurement_officer":  "buyer",   # ADR-M2-001 décision CTO 2026-02-28
    "viewer":               "viewer",
    # autre / inconnu →     "viewer"   # fallback défensif
}
```

Test couvrant : `test_procurement_officer_token_carries_buyer_role`
→ Claims token : `{"role": "buyer"}` pour un utilisateur `procurement_officer`.

---

### Tokens V4.1.0 — claims obligatoires

```json
{
  "sub":  "10",          // str(users.id) — INTEGER encodé en string
  "role": "buyer",       // VALID_ROLES : admin|manager|buyer|viewer|auditor
  "jti":  "<uuid>",      // révocation blacklist
  "type": "access",
  "iat":  1709000000,
  "exp":  1709001800     // 30 min
}
```

**Tokens legacy et V4.1.0 sont INCOMPATIBLES** (claims manquants côté legacy).
Reconnexion obligatoire après déploiement M2.

---

## III. BUGS RÉSOLUS PENDANT LE DÉPLOIEMENT RAILWAY

Ces bugs n'existaient pas en CI locale (TESTING=true court-circuite les chemins affectés).
Le successeur doit les connaître pour ne pas les reproduire.

| Bug | Symptôme | Cause | Fix |
|---|---|---|---|
| Start Command Railway (`&&`) | `catatonit: failed to exec pid1` | `&&` non interprété sans shell | `Procfile: web: bash start.sh` |
| `RAILWAY_ENVIRONMENT` inexistant | Alembic ne tournait pas | Variable mal nommée (c'est `RAILWAY_ENVIRONMENT_NAME`) | Guard via `TESTING` flag / `RUN_MIGRATIONS_ON_STARTUP` |
| `conditional_limit` wrappait `async def` en `def` | `<coroutine object login>` non awaité → 500 | `def wrapper` sync autour d'une `async def` | No-op systématique (`return func`) |
| `SECRET_KEY` absent Railway | 500 `ValueError: SECRET_KEY absent` | Variable non ajoutée au web service | Ajouter `SECRET_KEY` dans Railway → Variables |
| `passlib` + `bcrypt>=4.0.0` | `verify_password` échoue → 500 | `module 'bcrypt' has no attribute '__about__'` | Remplacé par `bcrypt` direct dans `auth_helpers.py` |
| Hash admin seed migration 004 | 500 sur login `admin/admin123` | Hash tronqué dans migration (52 chars vs 60 requis) | Utiliser `/auth/register` pour le smoke — hash corrigible via M2B UPDATE |

---

## IV. VARIABLES D'ENVIRONNEMENT REQUISES (RAILWAY)

| Variable | Description | Obligatoire |
|---|---|---|
| `DATABASE_URL` | URL PostgreSQL Railway | ✅ |
| `SECRET_KEY` | Clé JWT HS256 — minimum 32 bytes hex | ✅ |
| `JWT_SECRET` | Alias fallback de `SECRET_KEY` | optionnel |
| `TESTING` | `true` = désactive Alembic lifespan + rate limits | CI uniquement |
| `RUN_MIGRATIONS_ON_STARTUP` | `true` = lance `alembic upgrade head` dans lifespan | optionnel (fallback si start.sh indisponible) |

---

## V. SMOKE RAILWAY — RÉSULTAT FINAL

```
=== SMOKE M2 — https://decision-memory-v1-production.up.railway.app ===

[0] POST /auth/register -> HTTP 201 OK
     username  : smoke_0b6609bc
     role_name : procurement_officer

[1] POST /auth/token -> HTTP 200 OK
     jti   : PRESENT OK
     role  : buyer
     type  : access OK
     sub   : 10

[2] GET  /auth/me -> HTTP 200 OK
     username  : smoke_0b6609bc
     role_name : procurement_officer
     id        : 10

[3] POST /api/cases -> HTTP 200 OK
     id       : c035e6fb-f58a-4010-8ba9-cbf18d75b0ca
     owner_id : 10

[4] GET  /api/cases -> HTTP 200 OK

==================================================
SMOKE M2 --- VERT OK --- Token V4.1.0 confirme
==================================================
```

---

## VI. DETTES TECHNIQUES ACTIVES

| ID | Description | Statut M2 | Milestone cible |
|---|---|---|---|
| DETTE-M1-01 | `users.id` = INTEGER (vs UUID freeze) | Inchangé | Post-beta |
| DETTE-M1-02 | Double auth `src/auth.py` vs V4.1.0 | **SOLDÉE** (suppression `971af4a`) | ✅ |
| DETTE-M1-03 | `users.created_at` = TEXT (vs TIMESTAMPTZ) | Inchangé | Post-beta |
| DETTE-M1-04 | `users.role_id` INTEGER FK → roles | **PARTIELLEMENT SOLDÉE** — lectures migrées vers `UserClaims.role` · `DROP COLUMN` reporté | **M2B** |
| DETTE-M2-01 | Hash admin seed migration 004 tronqué (52 chars) | Nouveau | **M2B** — `UPDATE users SET hashed_password = ... WHERE username = 'admin'` |
| DETTE-M2-02 | `@limiter.limit()` par-route désactivé (no-op) | Nouveau | M3+ — audit compat slowapi/FastAPI async |
| DETTE-M2-03 | 36 tests `skipped` non audités | Hérité | M2B ou M3 |

---

## VII. SÉQUENCE MILESTONES

```
M0   ✅ v4.1.0-m0-done    — CI verte · repo truth sync
M0B  ✅ v4.1.0-m0b-done   — Migration 036 DB hardening · FK NOT VALID · triggers
M1   ✅ v4.1.0-m1-done    — JWT · RBAC · middleware · rate limiting · headers
M1B  ✅ v4.1.0-m1b-done   — audit_log · chain_seq · SHA-256 · fn_verify_audit_chain
M2   ✅ v4.1.0-m2-done    — Unification auth · src/auth.py supprimé · smoke Railway vert
M2B  ⬜ PROCHAIN           — DROP COLUMN role_id · fix hash admin · audit 36 skipped
M3   ⬜                    — Base cesse d'être vide — géographie + fournisseurs réels
M9 → M21 ⬜ OUVERTS
```

---

## VIII. INSTRUCTIONS POUR L'AGENT SUCCESSEUR (M2B)

### Lire en priorité

```
docs/freeze/DMS_V4.1.0_FREEZE.md            — loi absolue
docs/milestones/HANDOVER_M2_TRANSMISSION.md — ce document
docs/adr/ADR-M2-001_auth_unification.md     — décisions M2 complètes
TECHNICAL_DEBT.md                           — dettes actives
```

### Périmètre M2B — tâches prioritaires

**1. DROP COLUMN `users.role_id`** (DETTE-M1-04 résiduelle)

```sql
-- Vérifier que role_id n'est plus utilisé dans le code
grep -rn "role_id" src/ tests/
-- Migration Alembic 039 :
ALTER TABLE users DROP COLUMN IF EXISTS role_id;
DROP TABLE IF EXISTS roles CASCADE;  -- si plus utilisée
```

**Attention :** `create_user` dans `auth_helpers.py` utilise encore `role_id=2`.
Il faut retirer le paramètre ET la colonne dans la même migration.

**2. Fix hash admin seed** (DETTE-M2-01)

```sql
-- Dans migration 039 ou script séparé :
UPDATE users
SET hashed_password = '<hash bcrypt valide pour admin123>'
WHERE username = 'admin';
-- Générer avec : python -c "import bcrypt; print(bcrypt.hashpw(b'admin123', bcrypt.gensalt(12)).decode())"
```

**3. Audit des 36 skipped**

```bash
pytest tests/ --collect-only -q 2>&1 | grep SKIP
# Identifier : tests légitimement skippés vs tests qui devraient passer
```

**4. Réactiver `@limiter.limit()` par-route** (DETTE-M2-02)

```python
# src/ratelimit.py — conditional_limit doit passer func à slowapi
# Tester slowapi version : pip show slowapi
# Vérifier si slowapi gère async nativement sur la version installée
# Sinon : pin slowapi + implémentation correcte
```

### Règles absolues à respecter

```
- DETTE-M1-04 : Ne pas DROP role_id sans migration Alembic (zéro ALTER direct en prod)
- create_user : Retirer role_id=2 AVANT de dropper la colonne DB
- tests/ auth/ et audit/ : Ne pas modifier (M1 et M1B fermés)
- src/couche_a/auth/* : Ne pas modifier (M1 fermé)
- src/couche_a/audit/* : Ne pas modifier (M1B fermé)
- alembic/versions/ : Numéroter 039_ (pas de conflit avec 038)
```

---

## IX. ARCHITECTURE AUTH V4.1.0 — ÉTAT FINAL M2

```
src/
├── auth_router.py           ← MIGRÉ M2 — émet tokens V4.1.0
├── api/
│   ├── auth_helpers.py      ← CRÉÉ M2 — DB helpers extraits du legacy
│   ├── cases.py             ← MIGRÉ M2 — UserClaims
│   └── routes/
│       └── extractions.py   ← MIGRÉ M2 — UserClaims
├── couche_a/
│   ├── auth/                ← M1 FERMÉ — ne pas toucher
│   │   ├── jwt_handler.py   — create_access_token · verify_token · blacklist
│   │   ├── rbac.py          — 5 rôles · matrice permissions
│   │   ├── dependencies.py  — get_current_user · UserClaims · require_role
│   │   └── middleware.py    — SecurityHeaders · RateLimit
│   ├── audit/               ← M1B FERMÉ — ne pas toucher
│   └── routers.py           ← MIGRÉ M2 — UserClaims · ownership inline
```

**SUPPRIMÉ :** `src/auth.py` (legacy — commit `971af4a` · 2026-02-28)

---

## X. COMMANDES DE VÉRIFICATION RAPIDE

```bash
# État migrations
alembic heads
# → 038_audit_hash_chain (head) — DOIT rester 038 jusqu'à M2B

# CI complète
pytest --tb=short -q
# → 574 passed · 36 skipped · 0 failed

# Qualité statique
ruff check src/ tests/
black --check src/ tests/

# Zéro import legacy
grep -rn "from src.auth import\|from auth import" src/ tests/
# → 0 résultat attendu

# Smoke Railway (crée un user de test propre)
python scripts/_smoke_m2.py https://decision-memory-v1-production.up.railway.app
```

---

## XI. PIÈGES CONNUS (NE PAS RÉPÉTER)

| Piège | Cause | Fix |
|---|---|---|
| Railway Start Command avec `&&` | Sans shell, `&&` non interprété | Toujours `bash -c "..."` ou `start.sh` |
| `TESTING=false` traité comme truthy | `not os.environ.get("TESTING")` naïf | `.lower() == "true"` strict |
| `conditional_limit` wrappant async | `def wrapper` retourne une coroutine | No-op ou `inspect.iscoroutinefunction` |
| `passlib` + `bcrypt>=4.0.0` | `__about__` disparu en bcrypt 4.x | Utiliser `bcrypt` direct (déjà corrigé) |
| Hash tronqué en migration seed | Copy-paste mal coupé | Vérifier la longueur du hash (60 chars) |
| PowerShell `&&` invalide | PS ne supporte pas `&&` au niveau commande | Séparer les commandes ou utiliser `;` |
| `SECRET_KEY` absent → 500 opaque | Variable non ajoutée au web service | `try/except ValueError` dans login (déjà corrigé) |

---

## XII. RÈGLES ORGANISATIONNELLES ACTIVES

| Règle | Description |
|---|---|
| RÈGLE-ORG-04 | DoD validé par l'humain uniquement |
| RÈGLE-ORG-07 | Fichier hors périmètre → revert immédiat |
| RÈGLE-ORG-08 | PROBE avant toute action DB |
| RÈGLE-ORG-10 | Merge main + tags → humain uniquement |
| RÈGLE-12 | Migrations = SQL brut `op.execute()` uniquement — zéro autogenerate |
| RÈGLE-09 | `winner` / `rank` / `recommendation` = INTERDITS hors comité humain |

---

```
DMS V4.1.0 — Mopti, Mali — 2026

M0   = dette visible, mesurée.
M0B  = schéma durci, FK, triggers.
M1   = moteur auth. Qui peut entrer.
M1B  = mémoire des actes. Ce qui s'est passé.
M2   = unification. Un seul système auth. src/auth.py supprimé.

La dualité est éliminée.
Le moteur V4.1.0 est seul.
Transmission faite. À toi, M2B.
```
