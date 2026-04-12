# NOTE DE TRANSMISSION — M1B AUDIT HASH CHAIN

```
Date       : 2026-02-27
Milestone  : M1B — Audit Hash Chain
Branche    : feat/m1b-audit-hash-chain
Statut     : PR OUVERTE — en attente de validation humaine (DoD VERT)
Agent      : DMS V4.1.0
Successeur : Agent M2 UNIFY SYSTEM
```

---

## I. ÉTAT DU REPO À LA TRANSMISSION

| Élément | État |
|---|---|
| Branche active | `feat/m1b-audit-hash-chain` |
| Alembic head | `038_audit_hash_chain` |
| CI locale audit | 30/30 verts |
| Suite existante | 544 passés (non-régression confirmée localement) |
| ruff | 0 erreur |
| black | 0 erreur |
| PR GitHub | Ouverte — **merge** uniquement après DoD VERT humain + garde-fous CI/Alembic (`CLAUDE.md`) |
| Tag | `v4.1.0-m1b-done` — posé par l'humain (jalon) ; merge PR vers `main` = **agent** si mandat le prévoit |

---

## II. CE QUE M1B A LIVRÉ

### Migration `038_audit_hash_chain`

```
alembic/versions/038_audit_hash_chain.py
```

- Séquence `audit_log_chain_seq_seq` (BIGINT, START 1, NO CYCLE)
- Table `audit_log` : id UUID · chain_seq BIGINT · entity · entity_id · action
  · actor_id TEXT nullable · payload JSONB · payload_canonical TEXT · ip_address INET
  · timestamp TIMESTAMPTZ · prev_hash TEXT · event_hash TEXT
- 4 index : chain_seq · entity/entity_id · actor_id · timestamp DESC
- Extension pgcrypto (confirmée v1.3)
- Trigger `trg_audit_log_no_delete_update` (BEFORE DELETE OR UPDATE FOR EACH ROW)
- Trigger `trg_audit_log_no_truncate` (BEFORE TRUNCATE FOR EACH STATEMENT)
- Fonction `fn_reject_audit_mutation()` — message : "append-only — non autorisé et détectable"
- Fonction `fn_verify_audit_chain(p_from BIGINT, p_to BIGINT)` via pgcrypto SHA-256

### Code audit — `src/couche_a/audit/`

```
src/couche_a/audit/__init__.py
src/couche_a/audit/logger.py
```

**Exports publics :**
- `AuditAction` : CREATE · UPDATE · DELETE · ACCESS · LOGIN · LOGOUT · PERMISSION_DENIED
- `AuditLogEntry` : dataclass retournée par `write_event()`
- `write_event(entity, entity_id, action, db, actor_id, payload, ip_address)` → `AuditLogEntry`
- `verify_chain(db, from_seq, to_seq)` → `bool`

**Contrats immuables (ADR-M1B-001) — NE JAMAIS MODIFIER :**

```python
# Contrat 2 — payload_canonical
payload_canonical = json.dumps(payload, sort_keys=True, separators=(",",":"), ensure_ascii=False)
# ou "" si payload est None ou {}

# Contrat 3 — timestamp_canonical
ts_utc = ts.astimezone(UTC)
timestamp_canonical = ts_utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts_utc.microsecond:06d}Z"

# Contrat 4 — event_hash
raw = entity + entity_id + action + (actor_id or "") + payload_canonical
      + timestamp_canonical + str(chain_seq) + prev_hash
event_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

# Contrat 5 — prev_hash
prev_hash = "GENESIS"  # si première entrée
# sinon : SELECT event_hash FROM audit_log ORDER BY chain_seq DESC LIMIT 1

# Contrat 6 — mono-insert (IMMUABLE)
chain_seq = db.execute(text("SELECT nextval('audit_log_chain_seq_seq')")).scalar()
# calcul → INSERT unique → JAMAIS d'UPDATE post-insert sur event_hash
```

### Tests — `tests/audit/`

```
tests/audit/__init__.py
tests/audit/conftest.py          — db_session (rollback) · audit_entry_factory
tests/audit/test_audit_logger.py — 17 tests (écriture · hash · chaînage)
tests/audit/test_audit_chain.py  — 9 tests (vérification · altération · croisé Python↔DB)
tests/audit/test_audit_append_only.py — 4 tests (DELETE/UPDATE/TRUNCATE bloqués · INSERT autorisé)
```

**Test croisé Python ↔ DB vert** : `timestamp_canonical` identique entre
`strftime("%Y-%m-%dT%H:%M:%S.") + microseconds + "Z"` (Python) et
`to_char(timestamp AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')` (PostgreSQL).
STOP-M1B-9 non déclenché.

### Documentation

```
docs/adr/ADR-M1B-001_audit_hash_chain.md  — algorithme · contrats · alternatives · conséquences
TECHNICAL_DEBT.md                          — DETTE-M1-01 étendue (actor_id FK reportée)
```

---

## III. DETTES TECHNIQUES ACTIVES (héritées + M1B)

| ID | Description | Milestone cible |
|---|---|---|
| DETTE-M1-01 | `users.id` = INTEGER (legacy) · FK `actor_id → users` reportée | Post-beta dédié |
| DETTE-M1-02 | Double auth : `src/auth.py` legacy + `src/couche_a/auth/` V4.1.0 | M2 UNIFY SYSTEM |
| DETTE-M1-03 | `users.created_at` = TEXT (legacy) | Post-beta |
| DETTE-M1-04 | `users.role_id` INTEGER FK → roles (legacy) | M2 (DROP après bascule auth) |

**Garde-fou actif RÈGLE-ORG-11** : aucun nouveau code n'importe `src/auth.py`.
Règle Cursor : `.cursor/rules/no-legacy-auth-import.mdc`.

---

## IV. SÉQUENCE MILESTONES

```
M0  ✅ v4.1.0-m0-done   — CI verte · repo truth sync
M0B ✅ v4.1.0-m0b-done  — Migration 036 DB hardening · FK NOT VALID · triggers
M1  ✅ v4.1.0-m1-done   — JWT · RBAC · middleware · rate limiting · headers
M1B ⏳ v4.1.0-m1b-done  — audit_log · chain_seq · SHA-256 · fn_verify_audit_chain
                           PR ouverte — tag après DoD VERT humain
M2  ⬜ PROCHAIN          — Unification auth legacy vs V4.1.0 · bascule src/auth.py
M3 → M21 ⬜ OUVERTS
```

---

## V. INSTRUCTIONS POUR L'AGENT SUCCESSEUR (M2)

### Lire en priorité

```
docs/freeze/DMS_V4.1.0_FREEZE.md          — loi absolue
docs/milestones/HANDOVER_M1B_TRANSMISSION.md  — ce document
TECHNICAL_DEBT.md                          — dettes actives
docs/adr/ADR-M1-001_jwt_strategy.md       — stratégie bascule auth
alembic/versions/                          — état migrations
```

### Prérequis avant de démarrer M2

```
[ ] Tag v4.1.0-m1b-done posé par l'humain
[ ] Smoke Railway staging vert
[ ] Confirmation humaine explicite : "Ouvre M2"
```

### Périmètre M2 — Unification auth

```
OBJECTIF : basculer tous les endpoints /auth/* vers src/couche_a/auth/
           et désactiver src/auth.py (legacy)

RÈGLES :
  - Inventaire complet des imports src/auth.py AVANT toute modification
  - Chaque endpoint legacy = 1 test de non-régression AVANT modification
  - Migration Alembic si changement schéma users (PK UUID, created_at TIMESTAMPTZ)
  - RÈGLE-ORG-10 : merge PR `main` = **agent** après garde-fous (`CLAUDE.md`)
  - RÈGLE-ORG-11 : aucun nouveau code n'importe src/auth.py

DETTE à résoudre en M2 :
  DETTE-M1-02 — Double auth
  DETTE-M1-04 — users.role_id DROP COLUMN

DETTE reportée post-M2 (nécessite backfill) :
  DETTE-M1-01 — users.id INTEGER → UUID
  DETTE-M1-03 — users.created_at TEXT → TIMESTAMPTZ
```

### Points d'attention architecture

1. **`audit_log` est append-only** — tout appel métier qui modifie des données
   doit appeler `write_event()` dans la même transaction. Jamais d'opération
   métier sans trace audit.

2. **Contrats ADR-M1B-001 immuables** — l'ordre des champs et la canonicalisation
   ne peuvent plus changer sans rupture rétroactive de toute la chaîne.

3. **`fn_verify_audit_chain()`** — la vérification sur des millions de lignes
   doit utiliser `p_from`/`p_to` pour limiter la plage (O(n)).

4. **Redis rate limiting** — fallback no-op si Redis absent (RÈGLE-04).
   Ne jamais bloquer l'app sur Redis down.

5. **SECRET_KEY** — doit être dans l'ENV au démarrage.
   Absence → `ValueError` levée par `jwt_handler._secret_key()`.

---

## VI. COMMANDES DE VÉRIFICATION RAPIDE

```bash
# État migrations
alembic heads
# → 038_audit_hash_chain (head)

# Tables créées par M1B
psql $DATABASE_URL -c "
SELECT table_name FROM information_schema.tables
WHERE table_name IN ('audit_log', 'token_blacklist')
ORDER BY table_name;"

# Triggers audit_log
psql $DATABASE_URL -c "
SELECT tgname, tgenabled FROM pg_trigger t
JOIN pg_class c ON t.tgrelid = c.oid
WHERE c.relname = 'audit_log';"

# Tests audit uniquement (rapide)
pytest tests/auth/ tests/audit/ -v --tb=short -q

# Qualité statique
ruff check src/ tests/
black --check src/ tests/
```

---

## VII. RÈGLES ORGANISATIONNELLES ACTIVES

| Règle | Description |
|---|---|
| RÈGLE-ORG-04 | DoD validé par l'humain uniquement |
| RÈGLE-ORG-07 | Fichier hors périmètre → revert immédiat |
| RÈGLE-ORG-08 | PROBE avant toute action DB |
| RÈGLE-ORG-10 | Merge PR → `main` : **agent** (`CLAUDE.md`) ; tags jalons → souvent humain |
| RÈGLE-ORG-11 | Aucun nouveau import de `src/auth.py` |
| RÈGLE-12 | Migrations = SQL brut `op.execute()` uniquement |

---

```
DMS V4.1.0 — Mopti, Mali — 2026

M1  = moteur auth. Qui peut entrer.
M1B = mémoire des actes. Ce qui s'est passé.
M2  = unification. Un seul système.

La chaîne ne ment pas.
Transmission faite. À toi, M2.
```
