# NOTE DE TRANSMISSION — M2B HARDENING DB + MIGRATIONS

```
Date       : 2026-02-26
Milestone  : M2B — Hardening DB + Migrations
Branche    : feat/m2b-hardening-db-migrations (mergée sur main)
Statut     : DONE — tag v4.1.0-m2b-done posé sur main
Agent      : DMS V4.1.0
Successeur : Agent M3 (données réelles — géographie Mali · fournisseurs)
```

---

## I. ÉTAT DU REPO À LA TRANSMISSION

| Élément | État |
|---|---|
| Branche active | `main` |
| Alembic head | `039` (`039_hardening_created_at_timestamptz`) — exactement 1 |
| CI locale | **574 passed · 36 skipped · 0 failed** |
| ruff | 0 erreur |
| black | 0 erreur |
| Tag | `v4.1.0-m2b-done` — posé sur `main` |
| DB locale | `users.created_at = TIMESTAMPTZ` · FK NOT VALID local (doctrine ADR-0012) |
| DB prod Railway | `users.created_at = TIMESTAMPTZ` · `convalidated = True` · 1 user · 0 cases |

---

## II. CE QUE M2B A LIVRÉ

### Objectif accompli

Durcissement chirurgical du socle DB avant ouverture de M3.
Quatre dettes techniques soldées. Deux décisions documentées avec motif explicite.
Zéro violation de doctrine. Zéro fichier hors périmètre. Prod propre.

---

### Fichiers créés

| Fichier | Rôle |
|---|---|
| `docs/adr/ADR-M2B-001_hardening_db_scope.md` | ADR complète : probe, décisions CTO, STOP-M2B-3 résolution |
| `alembic/versions/039_hardening_created_at_timestamptz.py` | Migration `users.created_at TEXT → TIMESTAMPTZ` |
| `scripts/runbook_m2b_local.sql` | Runbook SQL local : orphelins, VALIDATE CONSTRAINT |
| `scripts/probe_m2b.py` | PROBE lecture seule multi-environnement |
| `scripts/_acte6_prod.py` | Runbook prod : verify 039, orphan_count, VALIDATE CONSTRAINT |
| `scripts/_acte6_option_a.py` | DELETE séquence case → user · IDs validés CTO |

### Fichiers modifiés

| Fichier | Changement |
|---|---|
| `TECHNICAL_DEBT.md` | 6 entrées reclassées (voir §VI) |
| `tests/couche_a/test_endpoints.py` | Skip reason `"Endpoint non encore implémenté (Milestone 2B / M5)"` → `"Endpoint non encore implémenté — prévu M5"` |
| `tests/test_m0b_db_hardening.py` | `test_alembic_head_is_current` → head attendu `039` (était `038_audit_hash_chain`) |

---

### Migration 039 — détail complet

```python
revision      = "039"
down_revision = "038_audit_hash_chain"

def upgrade() -> None:
    op.execute("""
        ALTER TABLE users
          ALTER COLUMN created_at TYPE TIMESTAMPTZ
          USING created_at::timestamp AT TIME ZONE 'UTC';
    """)

def downgrade() -> None:
    op.execute("""
        ALTER TABLE users
          ALTER COLUMN created_at TYPE TEXT
          USING to_char(
            created_at AT TIME ZONE 'UTC',
            'YYYY-MM-DD"T"HH24:MI:SS.US'
          );
    """)
```

**Note downgrade :** Les valeurs originalement en format date-only (`'2026-02-21'`) seront
restituées comme `'2026-02-21T00:00:00.000000'` — précision non récupérable après upgrade.
Décision CTO documentée dans ADR-M2B-001.

---

## III. SÉQUENCE D'EXÉCUTION M2B — RÉCAPITULATIF

| ACTE | Action | Résultat |
|---|---|---|
| ACTE 1 | ADR-M2B-001 rédigée + validée humainement | Committée |
| ACTE 2 | Bloc A non destructif : skip reason · downgrade cycle · test head 039 | ✅ |
| ACTE 3 | Runbook local orphelins → STOP-M2B-3 déclenché (trigger append-only) | NOT VALID assumé local |
| ACTE 4 | Migration 039 créée · contenu validé CTO · `to_char` downgrade corrigé | Committée |
| ACTE 5 | Cycle `downgrade -1` → `upgrade head` → pytest → 574+ passed | DETTE-ALEMBIC-01 SOLDÉE |
| ACTE 6 | Runbook prod Railway : 039 upgradé · VALIDATE CONSTRAINT · DELETE smoke | 4 dettes soldées |

---

## IV. STOP-M2B-3 — DÉCISION DOCUMENTÉE

**Contexte :** La DB locale contient 166 `pipeline_runs` avec `case_id` orphelins (fixtures
écrites avant existence de la FK fk_pipeline_runs_case_id, contexte M0B). Le trigger
`trg_pipeline_runs_append_only` (ADR-0012) BEFORE DELETE empêche toute purge.

**Décision CTO :** La doctrine ADR-0012 prime. Le trigger n'est pas désactivé.

```
DB locale    : NOT VALID assumé et documenté.
DB prod      : orphan_count = 0 prouvé → VALIDATE CONSTRAINT exécuté.
DETTE-M0B-01 : SOLDÉE sur prod · NOT VALID local assumé.
DETTE-FIXTURE-01 : OUVERTE — refactor fixtures à planifier M3+.
```

---

## V. ACTE 6 — PROD RAILWAY · OUTPUTS RÉELS

### Migration 039 prod

```
alembic_version prod : 039
users.created_at     : timestamp with time zone
```

### VALIDATE CONSTRAINT

```
orphan_count prod    : 0
convalidated         : True
```

### DELETE smoke

```
ETAPE 1  case_title='Smoke M2' · owner_username=smoke_0b6609bc  ✅
ETAPE 2  total_cases avant = 1                                   ✅
ETAPE 3  DELETE cases : 1 ligne                                  ✅
ETAPE 4  total_cases après = 0                                   ✅
ETAPE 5  DELETE users id=10 : 1 ligne                            ✅
ETAPE 6  remaining id=10 = 0                                     ✅
ETAPE 7a smoke/debug restants : 0 rows                           ✅
ETAPE 7b total_users = 1 (admin uniquement)                      ✅
ETAPE 7c total_cases = 0                                         ✅
ETAPE 8  FK NOT VALID = 0 rows                                   ✅
```

---

## VI. DETTES TECHNIQUES — ÉTAT FINAL M2B

| ID | Description | Statut avant M2B | Statut après M2B |
|---|---|---|---|
| DETTE-M1-01 | `users.id` INTEGER vs UUID freeze | Inchangé | Inchangé — post-beta |
| DETTE-M1-02 | Double auth `src/auth.py` | **SOLDÉE** M2 | SOLDÉE |
| DETTE-M1-03 | `users.created_at` TEXT | Active | **SOLDÉE** — migration 039 |
| DETTE-M1-04 | `users.role_id` INTEGER FK | PARTIELLEMENT SOLDÉE M2 | **ACTIVE** — DROP bloqué (7 usages runtime) |
| DETTE-M0B-01 | FK NOT VALID `pipeline_runs.case_id` | Active | **SOLDÉE prod** — NOT VALID local assumé ADR-0012 |
| DETTE-M2-01 | Hash admin seed | Active | **FERMÉE** — admin/admin123 fonctionne en prod (username=`admin` pas `admin@dms.local`) |
| DETTE-M2-02 | `conditional_limit` no-op | Active | Active — M3+ |
| DETTE-M2-03 | 36 tests skipped non audités | Active | 4 suspects audités et documentés — reste 32+ à auditer M3 |
| DETTE-M2-04 | 9 comptes smoke en prod | Active | **SOLDÉE** — DELETE id=10 + case associée IDs explicites |
| DETTE-ALEMBIC-01 | Downgrades 037+038 défaillants | Active | **SOLDÉE** — cycle complet vert |
| DETTE-FIXTURE-01 | Fixtures `pipeline_runs` non conformes | Inexistante | **OUVERTE** P2 — post-M2B, planifier M3+ |

---

## VII. SÉQUENCE MILESTONES

```
M0   ✅ v4.1.0-m0-done    — CI verte · repo truth sync
M0B  ✅ v4.1.0-m0b-done   — Migration 036 DB hardening · FK NOT VALID · triggers
M1   ✅ v4.1.0-m1-done    — JWT · RBAC · middleware · rate limiting · headers
M1B  ✅ v4.1.0-m1b-done   — audit_log · chain_seq · SHA-256 · fn_verify_audit_chain
M2   ✅ v4.1.0-m2-done    — Unification auth · src/auth.py supprimé · smoke Railway vert
M2B  ✅ v4.1.0-m2b-done   — Hardening DB · 4 dettes soldées · prod propre
M3   ⬜ PROCHAIN           — Base cesse d'être vide — géographie + fournisseurs réels
M9 → M21 ⬜ OUVERTS
```

---

## VIII. INSTRUCTIONS POUR L'AGENT SUCCESSEUR (M3)

### Lire en priorité

```
docs/freeze/DMS_V4.1.0_FREEZE.md               — loi absolue
docs/milestones/HANDOVER_M2B_TRANSMISSION.md    — ce document
docs/milestones/HANDOVER_M2_TRANSMISSION.md     — contexte auth
docs/adr/ADR-M2B-001_hardening_db_scope.md     — décisions DB M2B
TECHNICAL_DEBT.md                               — dettes actives
```

### Dettes à gérer impérativement avant M3 ou en M3

**1. DETTE-M1-04 — DROP COLUMN `users.role_id`** (priorité P1)

```bash
# Vérifier les usages restants avant toute migration
grep -rn "role_id" src/
```

Résultats attendus (usages légitimes documentés) :
- `src/api/auth_helpers.py` — `create_user(role_id=2)` · 6 occurrences
- `src/auth_router.py` — `create_user(role_id=2)` · 1 occurrence

Séquence obligatoire avant DROP :
1. Retirer `role_id=2` de `create_user()` dans `auth_helpers.py`
2. Retirer le paramètre de `auth_router.py`
3. Migration Alembic 040 : `ALTER TABLE users DROP COLUMN IF EXISTS role_id`
4. Évaluer si `DROP TABLE roles CASCADE` est sûr (vérifier usages FK)

**2. DETTE-FIXTURE-01 — Fixtures pipeline_runs non conformes** (priorité P2)

```python
# Les fixtures créent des pipeline_runs avec des case_id qui n'existent pas dans cases.
# Refactorer pour créer les cases correspondants avant les pipeline_runs.
# Ou utiliser des case_id existants depuis les fixtures cases.
# Fichiers concernés : tests/ contenant des fixtures pipeline_runs
```

**3. DETTE-M2-02 — conditional_limit no-op** (priorité P3)

```python
# src/ratelimit.py — conditional_limit doit passer func à slowapi
# Vérifier slowapi version : pip show slowapi
# Tester si slowapi gère async nativement sur la version installée
```

**4. Audit 36 skipped complet** (priorité P3)

```bash
pytest -rs tests/ 2>&1 | grep "SKIPPED"
# Classifier : légitimes / obsolètes / masquent une régression
# 4 suspects déjà audités en M2B (voir ADR-M2B-001)
```

### Règles absolues à respecter

```
- DETTE-M1-04 : Ne pas DROP role_id sans migration Alembic (zéro ALTER direct)
- Retirer create_user(role_id=2) AVANT de dropper la colonne DB
- tests/auth/ et tests/audit/ : Ne pas modifier (M1 et M1B fermés)
- src/couche_a/auth/*  : Ne pas modifier (M1 fermé)
- src/couche_a/audit/* : Ne pas modifier (M1B fermé)
- Migrations : SQL brut op.execute() uniquement — zéro autogenerate
- Next migration ID : 040_ (039 = M2B)
- DELETE prod : IDs explicites validés humainement uniquement — jamais par pattern
- PROBE avant toute action DB
```

---

## IX. ARCHITECTURE DB — ÉTAT FINAL M2B

```
tables actives :
  users           — id INTEGER · role TEXT · created_at TIMESTAMPTZ ✅
  cases           — id UUID · owner_id FK users.id · VALIDATED ✅
  pipeline_runs   — append-only (ADR-0012) · FK case_id NOT VALID local
  token_blacklist — jti blacklist JWT
  audit_log       — chain_seq · SHA-256 (M1B fermé)
  pipeline_stages — (M0B)
  documents       — (M0B)

alembic head : 039_hardening_created_at_timestamptz

colonnes legacy :
  users.role_id   — INTEGER FK → roles · 7 usages runtime · DROP bloqué (DETTE-M1-04)
  roles table     — encore référencée via role_id
```

---

## X. COMMANDES DE VÉRIFICATION RAPIDE

```bash
# État migrations
alembic heads
# → 039 (head) — DOIT rester 039 jusqu'à M3 migration suivante

# CI complète
pytest --tb=short -q
# → 574 passed · 36 skipped · 0 failed

# Qualité statique
ruff check src/ tests/
black --check src/ tests/

# Vérifier usages role_id
grep -rn "role_id" src/
# → auth_helpers.py (6) + auth_router.py (1)

# État DB prod
psql $DATABASE_URL -c "
  SELECT column_name, data_type FROM information_schema.columns
  WHERE table_name = 'users' AND column_name = 'created_at';"
# → timestamp with time zone

# FK NOT VALID restantes
psql $DATABASE_URL -c "
  SELECT conname, convalidated, conrelid::regclass
  FROM pg_constraint WHERE contype = 'f' AND convalidated = false;"
# → prod : 0 rows · local : pipeline_runs NOT VALID (assumé ADR-0012)
```

---

## XI. PIÈGES CONNUS (NE PAS RÉPÉTER)

| Piège | Cause | Fix |
|---|---|---|
| `VALIDATE CONSTRAINT` local impossible | trigger `trg_pipeline_runs_append_only` (ADR-0012) empêche DELETE orphelins | NOT VALID assumé local — validé uniquement en prod si `orphan_count = 0` |
| Migration downgrade TEXT perd le `T` | `AT TIME ZONE 'UTC'` → format PostgreSQL standard sans `T` | Utiliser `to_char(..., 'YYYY-MM-DD"T"HH24:MI:SS.US')` |
| `alembic heads` affiche 2 têtes | Fusion de branches mal gérée | Vérifier `down_revision` chaîne correcte avant commit |
| `test_alembic_head_is_current` rouge après migration | head hardcodé dans le test | Mettre à jour le test avec le nouvel ID de head |
| DELETE prod par pattern ILIKE | Risque de supprimer des utilisateurs légitimes | Toujours DELETE sur IDs explicites validés humainement |
| PowerShell `&&` invalide | PS ne supporte pas `&&` | Séparer les commandes ou utiliser Git Bash |
| Scripts Python inline en PowerShell | `UnicodeEncodeError` · `SyntaxError` heredoc | Créer des fichiers `.py` séparés · `$env:PYTHONIOENCODING="utf-8"` |
| `psycopg` v3 vs v2 API | `.fetchone()` retourne `dict` ou `tuple` selon `row_factory` | Utiliser `dict_row` de `psycopg.rows` |

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
| ADR-0012 | `pipeline_runs` append-only — UPDATE/DELETE interdits |
| ADR-M2-001 | Tokens V4.1.0 incompatibles legacy — reconnexion obligatoire |
| ADR-M2B-001 | STOP-M2B-3 — doctrine ADR-0012 prime — NOT VALID local assumé |

---

```
DMS V4.1.0 — Mopti, Mali — 2026

M0   = dette visible, mesurée.
M0B  = schéma durci, FK, triggers.
M1   = moteur auth. Qui peut entrer.
M1B  = mémoire des actes. Ce qui s'est passé.
M2   = unification. Un seul système auth. src/auth.py supprimé.
M2B  = socle durci. Quatre dettes soldées. Prod propre.

La base de données est prête pour recevoir des données réelles.
Transmission faite. À toi, M3.
```
