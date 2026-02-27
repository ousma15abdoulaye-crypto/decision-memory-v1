# NOTE DE TRANSMISSION — DMS V4.1.0
## Milestones M0 · M0B · M1 Security Baseline

**Date :** 2026-02-27
**Rédigé par :** Agent Claude Sonnet 4.6 (session complète)
**Destinataire :** Agent successeur + CTO Abdoulaye Ousmane
**Branche active :** `feat/m1-security-baseline`
**Prérequis merge :** DoD M1 validé par l'humain (RÈGLE-ORG-04 / RÈGLE-ORG-10)

---

## PARTIE I — VISION V4.1.0

### Principe directeur

> L'outil n'est jamais vide après M3.
> La donnée réelle entre tôt. Le moteur se calibre sur le réel.
> La décision reste humaine. L'agent exécute. L'humain valide.

### Jalons stratégiques (freeze DMS V4.1.0)

| Milestone | Objectif | État |
|---|---|---|
| **M0** | Dette visible, mesurée, TECHNICAL_DEBT.md | ✅ **DONE** |
| **M0B** | DB Hardening — migration 036, FK, triggers | ✅ **DONE** |
| **M1** | Security Baseline — JWT, RBAC, middleware | ⏳ **EN ATTENTE DOD HUMAIN** |
| M1B | Audit log + event_hash + fn_verify_audit_chain | 🔲 À OUVRIR |
| M2 | UNIFY SYSTEM — bascule auth legacy → V4.1.0 | 🔲 À PLANIFIER |
| M3 | Base cesse d'être vide — géographie + fournisseurs réels | 🔲 |
| M9 | Couche B = moat vivant — mercuriale + survey + signal | 🔲 |
| M10A | Stubs morts — extraction réelle LLM | 🔲 |
| M11 | Corpus annoté — precision ≥ 0.70 | 🔲 |
| M15 | 100 dossiers terrain avec métriques | 🔲 |
| M21 | Déployé sans fiction — Claude activé automatiquement | 🔲 |

---

## PARTIE II — TRAVAUX ACCOMPLIS (cette session)

### M0 — FIX CI & REPO TRUTH SYNC

**Objectif :** CI verte, inventaire dette technique, documentation.

**Livrables :**
- `docs/ci/ci_diagnosis.txt` — diagnostic CI local Windows
- `TECHNICAL_DEBT.md` — inventaire complet (stubs, FK manquantes, tables absentes)
- CI : 479 passed → **0 failed** · Alembic head : `035_create_analysis_summaries`

---

### M0B — DB HARDENING

**Objectif :** Durcir le schéma DB, FK, triggers append-only.

**Migration créée :** `alembic/versions/036_db_hardening.py`

| Élément | Détail |
|---|---|
| FK `fk_pipeline_runs_case_id` | Créée `NOT VALID` (données orphelines existantes) |
| `committee_delegations` | Créée (member_id corrigé TEXT) |
| `dict_collision_log` | Créée (canonical_id TEXT) |
| `annotation_registry` | Créée (document_id TEXT) |
| `extraction_jobs` | `next_retry_at`, `fallback_used`, `retry_count`, `max_retries`, `queued_at` |
| `documents.sha256` | Ajouté nullable (backfill requis — DETTE-M0B) |
| `UNIQUE (case_id, sha256)` | `uq_documents_case_sha256` |
| Triggers append-only | `fn_reject_mutation()` + triggers sur 4 tables |
| Fonctions SRE | `fn_sre_*` (3 fonctions) |
| 8 index critiques | Créés |

**Tests créés :** `tests/test_m0b_db_hardening.py` — 20+ tests

**Correctifs critiques :**
- `tests/couche_a/test_migration.py` : `_restore_schema()` dans `try/finally` — corrige la corruption de schéma par `002.downgrade()`
- 11 tests FK corrigés → `case_factory()` (tests pipeline + e2e + partial_statuses)
- `test_fk_rejects_ghost_case_id` → `pytest.raises(ForeignKeyViolation)`

**CI finale M0B :** 491 passed · 35 skipped · **0 failed**
**Tag :** `v4.1.0-m0b-done` → `7a28df5`

---

### M1 — SECURITY BASELINE

**Objectif :** Moteur auth V4.1.0 isolé — JWT, RBAC, middleware. Zéro touch legacy.

#### Migration `037_security_baseline`

```sql
-- users (additif uniquement — legacy préservé)
ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'viewer';
UPDATE users SET role = 'viewer' WHERE role IS NULL;
ALTER TABLE users ALTER COLUMN role SET NOT NULL;
ALTER TABLE users ADD CONSTRAINT chk_users_role
  CHECK (role IN ('admin','manager','buyer','viewer','auditor'));
ALTER TABLE users ADD COLUMN IF NOT EXISTS organization TEXT;

-- token_blacklist (table opérationnelle — NON append-only)
CREATE TABLE IF NOT EXISTS token_blacklist (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  token_jti TEXT NOT NULL UNIQUE,
  revoked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_jti ON token_blacklist(token_jti);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_expires ON token_blacklist(expires_at);
CREATE OR REPLACE FUNCTION fn_cleanup_expired_tokens() RETURNS INTEGER ...
```

#### Nouveaux fichiers `src/couche_a/auth/`

| Fichier | Rôle |
|---|---|
| `__init__.py` | Module marker |
| `jwt_handler.py` | `create_access_token()` · `create_refresh_token()` · `verify_token()` · `revoke_token()` · `rotate_refresh_token()` |
| `rbac.py` | 5 rôles · matrice permissions · `is_allowed()` |
| `dependencies.py` | `get_current_user()` · `require_role()` · `require_any_role()` · `UserClaims` dataclass |
| `middleware.py` | `SecurityHeadersMiddleware` · `RedisRateLimitMiddleware` (fallback no-op Redis) |

#### Intégration `src/api/main.py`

Ajout non-destructif des deux middlewares via `try/except ImportError`.
`src/auth.py` legacy **non modifié**.

#### Tests `tests/auth/` — 53 tests verts

| Fichier | Tests | Couverture |
|---|---|---|
| `conftest.py` | Fixtures | user_admin/viewer/buyer/auditor · valid/expired/blacklisted token |
| `test_jwt_handler.py` | 12 | claims · TTL · expiration · signature · blacklist · rotation · SECRET_KEY absent |
| `test_rbac.py` | 21 | matrice complète par rôle · rôle inconnu · require_role 200/403 |
| `test_token_blacklist.py` | 5 | révocation · cleanup TTL · UNIQUE constraint |
| `test_rate_limiting.py` | 5 | fallback no-op · 429 mock · TTL mock horloge |
| `test_security_headers.py` | 9 | 6 headers toutes routes · Cache-Control /auth/* |

#### ADRs créés

- `docs/adr/ADR-M1-001_jwt_strategy.md` — HS256 · 30min/7j · jti · rotation · cohabitation legacy · stratégie M2
- `docs/adr/ADR-M1-002_rbac_matrix.md` — 5 rôles · matrice · SOD M16B · audit_log M1B

**CI finale M1 :** 544 passed · 35 skipped · **0 failed**
**ruff :** 0 erreur · **black :** 0 erreur
**Alembic head :** `037_security_baseline`

---

## PARTIE III — ÉTAT DU REPO AU HANDOVER

### Git

```
Branche  : feat/m1-security-baseline
HEAD     : f955347 (M1 Security Baseline)
Remote   : origin/feat/m1-security-baseline = f955347
main     : 56eb8ce (handover M0B→M1)
Tag M0B  : v4.1.0-m0b-done → 7a28df5
Tag M1   : À POSER après DoD VERT humain
```

### Alembic

```
head     : 037_security_baseline
chaîne   : 001 → ... → 035 → 036 → 037
```

### Schéma DB (54 tables + 1 vue + 1 table auth)

Nouvelles en M1 : `token_blacklist`
Colonnes ajoutées : `users.role TEXT NOT NULL DEFAULT 'viewer'` · `users.organization TEXT`

---

## PARTIE IV — DETTES ACTIVES (TECHNICAL_DEBT.md)

### Dettes M0B

| ID | Dette | Action | Milestone |
|---|---|---|---|
| — | FK `fk_pipeline_runs_case_id` NOT VALID | VALIDATE après nettoyage orphelins | M2+ |
| — | `documents.sha256` nullable | Backfill + SET NOT NULL | M2+ |
| — | Types PK non conformes (id TEXT vs UUID) | Migration dédiée | Post-beta |

### Dettes M1

| ID | Dette | Action | Milestone |
|---|---|---|---|
| DETTE-M1-01 | `users.id` = INTEGER (vs UUID freeze) | Migration dédiée post-beta | Post-beta |
| DETTE-M1-02 | Double auth legacy vs V4.1.0 | Basculement complet | **M2 UNIFY SYSTEM** |
| DETTE-M1-03 | `users.created_at` = TEXT (vs TIMESTAMPTZ) | ALTER TYPE + backfill | Post-beta |
| DETTE-M1-04 | `users.role_id` INTEGER (vs `role TEXT CHECK`) | DROP COLUMN lors M2 | M2 |

### Dettes techniques

| Dette | Action | Milestone |
|---|---|---|
| Stub `src/couche_a/extraction.py:416` (`time.sleep(2)`) | Implémentation réelle LLM | **M10A** |
| SOD comité dans `require_role()` | Logique métier comité | **M16B** |
| `audit_log` / hash chain | Module traçabilité | **M1B** |
| `_restore_schema` flakiness CI multi-worker | Refactoriser en 1 transaction | Avant `pytest-xdist` |
| `app_user` DB role + REVOKE | Créer rôle + permissions | **M1** ou M2 |

---

## PARTIE V — PIÈGES CONNUS (NE PAS RÉPÉTER)

| Piège | Cause | Fix |
|---|---|---|
| `sha256` disparaît après pytest full | `test_migration.py::downgrade()` CASCADE | `_restore_schema()` dans `try/finally` |
| FK violation `pipeline_runs` insert | `case_id` ghost sans `case_factory()` | Toujours utiliser `case_factory()` |
| PowerShell `&&` invalide | Syntaxe PowerShell | Séparer les commandes |
| Quotes Python inline PowerShell | Guillemets imbriqués | Passer par fichier `.py` |
| ruff/black non vérifiés avant push | Oubli CI | Toujours lancer avant commit |
| **Merge vers main sans autorisation** | Mauvaise lecture mandat | RÈGLE-ORG-10 : **JAMAIS** sans feu vert humain |
| `ADD COLUMN IF NOT EXISTS` avec NOT NULL | PostgreSQL ignore silencieusement si colonne existe | Utiliser multi-step : ADD → UPDATE → SET NOT NULL |

---

## PARTIE VI — RÈGLES INVIOLABLES (RAPPEL AGENT)

| Règle | Énoncé |
|---|---|
| RÈGLE-ORG-04 | DoD = checklist validée par l'humain. **Jamais par l'agent.** |
| RÈGLE-ORG-07 | Fichier hors périmètre modifié → revert immédiat |
| RÈGLE-ORG-08 | Chaque mandat commence par PROBE (état réel avant modification) |
| **RÈGLE-ORG-10** | **L'agent ne merge JAMAIS vers main. L'humain seul merge.** |
| RÈGLE-03 | CI rouge = STOP TOTAL |
| RÈGLE-05 | Append-only sur toute table décisionnelle / audit / traçabilité |
| RÈGLE-08 | PROBE-SQL-01 avant toute migration touchant une table existante |
| RÈGLE-09 | `winner` / `rank` / `recommendation` = INTERDITS hors comité humain |
| RÈGLE-10 | `status=complete` = réservé M15 exclusivement |
| RÈGLE-12 | Migrations = `op.execute()` SQL brut. ZÉRO autogenerate. |

---

## PARTIE VII — PROCHAINES ÉTAPES PRIORITAIRES

### Action immédiate — DoD M1 (humain)

Checklist à valider :

```
[ ] pytest → 544 passed · 0 failed · 0 errors
[ ] tests/auth/ complets et verts (53 tests)
[ ] alembic heads → exactement 1 : 037_security_baseline
[ ] Migration 037 = SQL brut op.execute() · zéro autogenerate
[ ] Migration 037 ne touche PAS audit_log
[ ] ADR-M1-001_jwt_strategy.md committé dans docs/adr/
[ ] ADR-M1-002_rbac_matrix.md committé dans docs/adr/
[ ] JWT : access 30min · refresh 7j · jti blacklist opérationnel
[ ] RBAC : 5 rôles · matrice complète
[ ] SOD comité absente de require_role() · documentée TECHNICAL_DEBT M16B
[ ] token_blacklist doctrine opérationnelle (non append-only)
[ ] rate limiting : Redis · fallback no-op · test mock horloge
[ ] headers sécurité : 6 headers toutes réponses
[ ] passlib non utilisé dans src/couche_a/auth/
[ ] grep "audit_log|event_hash|prev_hash" src/couche_a/auth/ → 0
[ ] grep "winner|rank|recommendation" src/ → 0
[ ] zéro appel API réel dans tests/
[ ] TECHNICAL_DEBT.md mis à jour · DETTE-M1-01 à M1-04 documentées
[ ] ruff → 0 erreur · black → 0 erreur
[ ] zéro fichier hors périmètre modifié
```

**Après DoD VERT humain :**
```
git tag -a v4.1.0-m1-done <HEAD> -m "M1 Security Baseline complete"
git push origin v4.1.0-m1-done
# Merge → humain uniquement (RÈGLE-ORG-10)
```

### M1B — Audit Log & Hash Chain (prochain mandat)

**Head début :** `037_security_baseline`
**Head fin :** `037_audit_hash_chain` (ou `038_audit_hash_chain`)

Points clés :
- Table `audit_log` (append-only, trigger DB)
- `event_hash` = SHA256(prev_hash + event data)
- `prev_hash` chainé
- `fn_verify_audit_chain()` — vérification cryptographique
- Tests chaîne cryptographique

### M2 — UNIFY SYSTEM (après M1B)

**Objectif :** Basculer l'auth legacy sur le nouveau moteur V4.1.0.

Points clés :
- Raccorder `src/couche_a/auth/` aux endpoints `/auth/token`, `/auth/me`, `/auth/register`
- Migrer les 5 tests legacy `tests/test_rbac.py`
- Supprimer `src/auth.py` après validation complète
- `DROP COLUMN role_id` sur `users` (DETTE-M1-04)
- **Condition bloquante :** décision humaine explicite avant bascule

---

## PARTIE VIII — FICHIERS CLÉS À LIRE EN PRIORITÉ

| Fichier | Rôle |
|---|---|
| `docs/freeze/DMS_V4.1.0_FREEZE.md` | **Source de vérité unique** — 29 règles, architecture, schéma cible |
| `TECHNICAL_DEBT.md` | Inventaire dettes actives (M0 + M0B + M1) |
| `docs/adr/ADR-M1-001_jwt_strategy.md` | Stratégie JWT + cohabitation legacy + M2 |
| `docs/adr/ADR-M1-002_rbac_matrix.md` | Matrice RBAC 5 rôles |
| `docs/milestones/DOD_M0B_RAPPORT.md` | Rapport validation M0B |
| `docs/milestones/HANDOVER_AGENT.md` | Handover M0B → M1 (détail schéma + pièges) |
| `alembic/versions/036_db_hardening.py` | Migration M0B |
| `alembic/versions/037_security_baseline.py` | Migration M1 |
| `src/couche_a/auth/` | Nouveau moteur auth V4.1.0 |
| `src/auth.py` | Auth legacy — **NE PAS MODIFIER avant M2** |

---

## PARTIE IX — SCRIPTS UTILITAIRES

| Script | Usage |
|---|---|
| `scripts/_force_036.py` | Restauration urgence DB → état 036 |
| `scripts/_dod_m0b_probe.py` | Sonde DoD M0B (6 vérifications DB) |
| `scripts/_probe_m1.py` | Sonde PROBE M1 (tables auth, colonnes) |
| `scripts/_probe_m1_post.py` | Sonde post-migration 037 |
| `scripts/_probe_m1_role.py` | Vérifie role NOT NULL + CHECK + token_blacklist |

---

## CONCLUSION

| Milestone | CI | Tag | Statut |
|---|---|---|---|
| M0 | 479 ✅ | `v4.1.0-m0-done` | ✅ MERGÉ main |
| M0B | 491 ✅ | `v4.1.0-m0b-done` | ✅ MERGÉ main |
| **M1** | **544 ✅** | À poser après DoD | ⏳ EN ATTENTE VALIDATION HUMAINE |

**DMS V4.1.0 — Mopti, Mali**
*Discipline. Vision. Ambition.*
*M1 = moteur auth. M1B = mémoire des actes. M2 = unification.*
