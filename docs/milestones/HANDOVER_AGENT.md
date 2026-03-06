# HANDOVER AGENT — DMS V4.1.0
**Date :** 2026-03-05
**Rédigé par :** Agent courant (Composer — session M6 Dictionary Build)
**Destinataire :** Agent successeur
**Branche active :** `main`
**Tag courant :** `v4.1.0-m6-dictionary` → commit `316854f`

---

## 1. CONTEXTE PROJET

**DMS = Decision Memory System**
Outil d'aide à la décision achats humanitaires pour Save the Children Mali.
Opérateur unique : Abdoulaye Ousmane (CTO/Founder), Mopti, Mali.
Stack : Python 3.11 · FastAPI · PostgreSQL 16 · Redis 7 · Railway · Alembic · psycopg v3 · pytest · ruff · black.

### Règles d'or (mises à jour 2026-03-05)

> **RÈGLE-ORG-04 mise à jour :** Le CTO a accordé à l'agent le droit de merger et poser des tags
> **sous conditions strictes** : les 7 gates binaires ci-dessous doivent être prouvées par outputs bruts.
> En dehors de ces gates, RÈGLE-ORG-04 reste : l'humain seul prononce le merge.

**Gates de merge autorisées (7/7 obligatoires) :**
```
1. alembic heads       → 1 seul résultat
2. alembic history     → down_revision correct (chaîne visible)
3. alembic upgrade head → 0 erreur
4. Cycle down/up        → head stable après aller-retour
5. pytest -q            → 0 failed / 0 error
6. ruff + black --check → verts
7. Fichiers hors périmètre → 0
```

**RÈGLE-ORG-10 :** L'agent ne merge vers main que si les 7 gates sont vérifiées ET que le CTO a explicitement autorisé le merge pour la session en cours.

---

## 2. ÉTAT DU REPO AU HANDOVER

### Git
```
Branche  : main
HEAD     : 316854f  feat(m6): dictionary procurement AOF - v4.1.0-m6-dictionary
Tag      : v4.1.0-m6-dictionary → 316854f
CI       : verte (817 passed · 36 skipped · 0 failed · 0 error)
Alembic  : m7_3_dict_nerve_center (head unique)
```

### Historique récent main
```
316854f  feat(m6): dictionary procurement AOF - v4.1.0-m6-dictionary
a326329  feat(m6): dictionary build - 1488 items - 1596 aliases - couche_b source de verite
2a8090e  Merge pull request #168 from feat/m5-patch-imc-ingest
1d835e5  fix(tests): alembic head attendu = m5_patch_imc_ingest_v410
ab4e865  style(imc): black format queries.py
```

### Tags Git (tous les sprints V4.1.0)
```
v4.1.0-m0-done
v4.1.0-m0b-done
v4.1.0-m1b-done
v4.1.0-m2-done
v4.1.0-m2b-done
v4.1.0-m2b-patch-done
v4.1.0-m3-done
v4.1.0-m4-done
v4.1.0-m4-patch-done
v4.1.0-m4-patch-a
v4.1.0-m4-patch-a-fix
v4.1.0-m4-patch-b-done
v4.1.0-patch-b-copilot
v4.1.0-m5-pre-hardening
v4.1.0-m5-fix          ← sprint M5-FIX (market_signals.vendor_id + alembic VARCHAR)
v4.1.0-m5-cleanup-a    ← sprint M5-CLEANUP-A (dettes pré-M5)
v4.1.0-m6-dictionary   ← sprint M6 Dictionary Build — TAG COURANT
```

---

## 3. ARCHITECTURE SYSTÈME

### Couches
```
COUCHE A — PROCUREMENT (exécution / calcul)
  ├── Case Management      : create / status / procedure_type
  ├── Document Upload      : sha256 + audit, queue async, 202 immédiat
  ├── Extraction Engine    : Classifier → LlamaParse → Azure Doc Intel
  │                          → Mistral OCR → python-docx → Tesseract (offline)
  │                          StructuredExtractor (instructor + LLM chain)
  ├── Scoring Engine       : criteria weights, eliminatory, SCI §5.2
  ├── Pipeline A           : preflight → extraction → scoring → summary
  ├── Committee            : members + seal, ACO + PV export · FSM events
  └── Submission Registry  : dépôts, append-only triggers DB

COUCHE B — MÉMOIRE MARCHÉ (contexte / enrichissement)
  ├── Dictionary           : canonical + aliases, collision_log, proposals
  ├── Mercuriale Ingest    : 2023/24/25/26, sha256 idempotent, zone × année
  ├── Market Signal        : agrégation 3 sources, formule v1.0
  └── Decision Feedback    : seal() → decision_history → dict enrichment auto

INFRASTRUCTURE
  PostgreSQL 16 · Redis 7 · Railway · FastAPI · Alembic
```

### Arborescence src/ — changements M5-CLEANUP-A
```
src/
├── db/
│   └── __init__.py        ← TD-005 FERMÉE : appel eager supprimé · lazy init
├── api/
│   └── analysis.py        ← extract_dao_criteria_structured → HTTP 501 · TD-011
├── couche_a/
│   ├── scoring/
│   │   └── api.py         ← POST /calculate → HTTP 501 · pipeline FSM uniquement
│   └── committee/
│       ├── service.py     ← recommendation_set → review_opened
│       └── models.py      ← COMMITTEE_EVENT_TYPES : recommendation_set → review_opened
└── ...
```

### Schéma DB — état `m7_3_dict_nerve_center`
```
Chaîne Alembic complète (du plus récent au plus ancien) :
  m7_3_dict_nerve_center  ← HEAD
  m5_patch_imc_ingest_v410
  m5_geo_patch_koutiala
  040_mercuriale_ingest
  m5_geo_fix_master
  m5_cleanup_a_committee_event_type_check
  m5_fix_market_signals_vendor_type
  m5_pre_vendors_consolidation
  m4_patch_a_fix
  ... (migrations 036 et antérieures)
```

CHECK constraint `committee_events_event_type_check` :
```
Valeurs valides : committee_created · member_added · member_removed
                  meeting_opened · vote_recorded · review_opened
                  seal_requested · seal_completed · seal_rejected
                  snapshot_emitted · committee_cancelled
ATTENTION : "recommendation_set" SUPPRIMÉ (migration M5-CLEANUP-A)
```

### Dictionnaire procurement (M6)
```
couche_b.procurement_dict_items    → 1488 items (51 seed + 1437 mercuriale/IMC)
couche_b.procurement_dict_aliases  → 1596 aliases
couche_b.dict_proposals            → 1439 pending (file validation M7)
public.dict_items / dict_aliases    → vues miroir couche_b
Source de vérité : couche_b · matcher 3 niveaux (EXACT → NORMALIZED → TRIGRAM)
```

### Détails entreprise-grade (réf. HANDOVER_M4_TRANSMISSION)

Le système est **solide pour une beta terrain mono-opérateur**. La discipline psycopg (ADR-0003), la chaîne de migrations, le fingerprint SHA256, la résilience circuit-breaker/retry, et le TECHNICAL_DEBT.md sont au niveau.

**Concurrence** — Scope assumé mono-opérateur (M21 multi-pays). Dette documentée (TD-001, TD-007), pas un défaut pour V4.1.0.

**Fail-loud** — Audit grep 2026-03-05 : `src/couche_b` et `scripts/` — tous les `except Exception` identifiés loggent ou reportent (logger.warning/error, report.errors). Les `pass` dans parsers (imc/parser, mercuriale/parser) concernent `ValueError` sur lignes malformées (skip acceptable). Cas limites : `build_dictionary.py` log_collision/log_proposal (l.310, l.359) — logger.error sans re-raise ; l'erreur est tracée mais le flux continue. Aucun cas de swallow total identifié.

Détails complets : `docs/milestones/HANDOVER_M4_TRANSMISSION.md` (lignes 357–395).

---

## 4. MIGRATIONS ALEMBIC — ÉTAT ACTUEL

### Nouvelles migrations M5/M6 (à connaître)

| Révision | Sprint | Contenu |
|----------|--------|---------|
| `m5_pre_hardening` | M5-PRE | Consolidation vendors legacy · DROP TABLE vendors legacy |
| `m5_pre_vendors_consolidation` | M5-PRE | Schéma vendors nouvelle génération |
| `m5_fix_market_signals_vendor_type` | M5-FIX | `market_signals.vendor_id` INTEGER → UUID · alembic_version VARCHAR(32→64) |
| `m5_cleanup_a_committee_event_type_check` | M5-CLEANUP-A | CHECK constraint `committee_events.event_type` : `recommendation_set → review_opened` |
| `m5_geo_fix_master` | M5-PATCH | 16 zones mercuriales Mali 2023 |
| `040_mercuriale_ingest` | M5 | Tables mercuriale_sources, mercurials |
| `m5_patch_imc_ingest_v410` | M5-PATCH | IMC ingest 2024/25/26 |
| `m5_geo_patch_koutiala` | M5-PATCH | Zone géographique Koutiala |
| `m7_3_dict_nerve_center` | M7.3 | Dict nerve center · audit_log aligné · taxonomie L1/L2/L3 · 1488 items · 1596 aliases |

### Point critique migration M5-FIX
- `alembic_version.version_num` étendu à `VARCHAR(64)` — **idempotent** · toujours applicable
- FK `market_signals → vendors` : **non enforced localement** · appliquée en prod via `scripts/apply_fk_prod.py`

### Point critique migration M5-CLEANUP-A
- CHECK constraint `committee_events_event_type_check` recréée avec `review_opened` à la place de `recommendation_set`
- Migration **idempotente** : skip propre si `review_opened` déjà présent, skip propre si contrainte absente

---

## 5. TESTS — ÉTAT ACTUEL

**CI : 817 passed · 36 skipped · 0 failed · 0 error**

### Fichiers tests modifiés en M5-CLEANUP-A / M6
```
tests/invariants/test_inv_04_online_only.py   ← lazy init · reset _DB_URL_CACHE
tests/test_m0b_db_hardening.py                ← head assertion → m7_3_dict_nerve_center
tests/vendors/test_vendor_migration.py        ← idem
tests/vendors/test_vendor_patch.py            ← idem
tests/vendors/test_vendor_patch_a.py          ← idem
tests/geo/test_geo_migration.py               ← idem
tests/couche_b/test_dict_minimum_coverage.py  ← M6 : coverage dict_items/aliases
```

### Invariant important — test_inv_04
`test_inv_04_database_url_required` vérifie que `get_connection()` (pas l'import) lève `RuntimeError` si `DATABASE_URL` absent.
Le test reset explicitement `_core._DB_URL_CACHE = None` pour l'isolation.
**Ne pas modifier ce pattern.**

### Skipped (36 — inchangés)
- SLA-B extraction (M10A)
- Performance (`test_sla_classe_a_60s`)
- `market_signal` hors scope M0
- Tests `offers` preflight configurés SKIP

---

## 6. DETTE TECHNIQUE — ÉTAT ACTUEL (TECHNICAL_DEBT.md)

### Fermées ce sprint
| TD | Fermée | Sprint |
|----|--------|--------|
| TD-004 | Table vendors legacy hors alembic | M5-PRE |
| TD-005 | Lazy init DATABASE_URL (`__init__.py` + `core.py`) | M5-CLEANUP-A |
| TD-006 | SELECT * vendors API | M5-PRE |
| TD-008 | ImportError silencieux main.py | M5-PRE |
| TD-010 | `market_signals.vendor_id` INTEGER→UUID | M5-FIX |

### Ouvertes (à traiter)
| TD | Sévérité | Échéance | Description |
|----|----------|----------|-------------|
| TD-001 | Haute | M5+ | `get_next_sequence()` non atomique |
| TD-002 | Modérée | M11 | Index GIN trigram vendor_match_rate |
| TD-003 | Modérée | M5/M6 | `zones_covered`, `category_ids` vides |
| TD-007 | Modérée | M5+ | Connection pooling absent |
| TD-009 | Modérée | M5+ | Chaîne Alembic hors convention numérique |
| TD-011 | **Haute** | **M10B** | `extract_dao_criteria_structured` stub → HTTP 501 posé · implémentation M10B |
| TD-012 | Modérée | Continu | `SELECT *` persistant hors vendors |
| TD-013 | **Haute** | **M10A** | SLA-B LlamaParse + Mistral OCR non connectés |
| TD-014 | Faible | RUNBOOK | Migration 017 supprimée · script fix manuel |
| TD-015 | Modérée | M5+ | FK market_signals append-only incompatible localement |
| TD-016 | Faible | M5+ | chk_vendor_id_format limité 4 chiffres (9999 vendors/région) |

### Stubs actifs — NE PAS TOUCHER
```python
# src/couche_a/extraction.py:416
# extract_offer_content() → time.sleep(2) + return {"status": "completed"}
# Réservé M10A — NE PAS SUPPRIMER

# src/api/analysis.py — extract_dao_criteria_structured → HTTP 501
# Réservé M10B Gateway Calibration

# src/couche_a/scoring/api.py — POST /calculate → HTTP 501
# Scoring via pipeline FSM uniquement · endpoint direct désactivé
# Disponible M9
```

---

## 7. PIÈGES RENCONTRÉS — À NE PAS RÉPÉTER

| # | Piège | Cause | Fix |
|---|-------|-------|-----|
| PIÈGE-1 | sha256 disparaît après pytest | `test_migration.py::downgrade()` DROP CASCADE | `_restore_schema()` try/finally |
| PIÈGE-4 | alembic_version régresse cycle down/up | DB désynchronisée avant downgrade | Vérifier `alembic current` ET état DB avant tout downgrade |
| PIÈGE-8 | FOR KEY SHARE bloque FK market_signals | Protection append-only incompatible | FK hors migration → `apply_fk_prod.py` prod uniquement |
| PIÈGE-9 | Séquence vendor_id BKO sature à 10000 | Contrainte `[0-9]{4}` + runs répétés | `scripts/_reset_vendor_seq.py` |
| PIÈGE-10 | alembic stamp ne survit pas à pytest | Désynchronisation mid-transaction | Garde 0 idempotence dans `upgrade()` |
| PIÈGE-11 | PowerShell heredoc `<<'EOF'` invalide | PowerShell ne supporte pas heredoc | `git commit -F fichier.txt` |
| PIÈGE-12 | `--timeout` pytest non reconnu | pytest-timeout absent | Ne jamais utiliser `--timeout` |
| PIÈGE-13 | Shell spawn abort longues commandes | Windows PowerShell > 300s | Fichier Python + `subprocess.run([sys.executable, ...])` |
| PIÈGE-14 | `&&` invalide PowerShell | PowerShell n'accepte pas `&&` | Utiliser `;` ou commandes séparées |
| PIÈGE-15 | alembic_version VARCHAR(32) tronque | Défaut Alembic toutes versions y compris 1.13.x | `ALTER COLUMN version_num TYPE VARCHAR(64)` en tête de `upgrade()` |
| PIÈGE-16 | CHECK constraint DB invisible au probe applicatif | Divergence silencieuse code ↔ schéma DB | Toujours sonder `pg_constraint` avant renommage d'event_type |

### PIÈGE-16 — détail critique
`committee_events_event_type_check` imposait `recommendation_set` en DB alors que le code Python avait été mis à jour vers `review_opened`. L'erreur n'apparaissait qu'à l'INSERT (psycopg `CheckViolation`), pas à l'import ni au linting.
**Règle :** avant tout renommage d'une valeur dans un champ contraint en DB, toujours exécuter :
```sql
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'nom_table'::regclass AND contype = 'c';
```

---

## 8. RÈGLES SYSTÈME (INVIOLABLES)

| Règle | Énoncé |
|-------|--------|
| RÈGLE-01 | 1 milestone = 1 branche = 1 PR = 1 merge = 1 tag Git |
| RÈGLE-03 | CI rouge = STOP TOTAL |
| RÈGLE-05 | Append-only sur toute table décisionnelle / audit / traçabilité |
| RÈGLE-06 | DONE ou ABSENT. Rien entre les deux. |
| RÈGLE-08 | PROBE-SQL-01 avant toute migration touchant une table existante |
| RÈGLE-09 | `winner` / `rank` / `recommendation` = INTERDITS hors comité humain |
| RÈGLE-10 | `status=complete` = réservé M15 exclusivement |
| RÈGLE-12 | Migrations = `op.execute()` SQL brut. ZÉRO autogenerate. |
| RÈGLE-17 | Toute migration = 1 test minimum prouvant l'invariant visé |
| RÈGLE-FK | Toute FK vers/depuis `market_signals` → vérifier privilege `FOR KEY SHARE` |
| RÈGLE-WIN | PowerShell : `&&` invalide · heredoc invalide · spawn peut avorter · HTTP/1.1 requis pour push |
| RÈGLE-ORG-02 | Lire `docs/freeze/DMS_V4.1.0_FREEZE.md` EN ENTIER avant de commencer |
| RÈGLE-ORG-07 | Fichier hors périmètre modifié = revert immédiat |
| RÈGLE-ORG-08 | Chaque mandat commence par PROBE (état réel avant modification) |
| RÈGLE-ORG-10 | L'agent ne merge que si 7 gates vertes ET autorisation CTO explicite pour la session |

### Workaround réseau Windows (NOUVEAU — 2026-03-04)
`git push` via HTTP/2 échoue aléatoirement avec `curl 52 Recv failure: Connection was reset`.
**Fix permanent :**
```bash
git config http.version HTTP/1.1
```
Cette config est déjà appliquée dans le repo local. À ré-appliquer si le repo est reclôné.

---

## 9. PROBE-SQL-01 — À EXÉCUTER AVANT TOUT SPRINT M5+

```sql
-- Alembic head (doit être 1 seul)
SELECT version_num FROM alembic_version;
-- Attendu : m7_3_dict_nerve_center

-- market_signals.vendor_id (doit être UUID après M5-FIX)
SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_name = 'market_signals' AND column_name = 'vendor_id';

-- CHECK constraint committee_events (doit contenir review_opened)
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'committee_events'::regclass AND contype = 'c'
ORDER BY conname;

-- alembic_version longueur colonne (doit être 64 après M5-FIX)
SELECT character_maximum_length
FROM information_schema.columns
WHERE table_name = 'alembic_version' AND column_name = 'version_num';

-- FK market_signals (absente localement, présente en prod)
SELECT constraint_name FROM pg_constraint c
JOIN pg_class t ON t.oid = c.conrelid
WHERE c.conname = 'market_signals_vendor_id_fkey'
  AND t.relname = 'market_signals';
```

---

## 10. PROCHAIN SPRINT — M7 DICTIONARY VALIDATION

**Débloqué après merge de M6 (fait).**

### Contexte
M5 Mercuriale Ingest et M6 Dictionary Build sont terminés. M7 = validation des fichiers `dict_proposals` (1439 pending) → intégration dans `procurement_dict_items` / `procurement_dict_aliases`.

### Préconditions
- `alembic heads` = `m7_3_dict_nerve_center` ✅
- `pytest` = 817 passed ✅
- Dictionnaire : 1488 items, 1596 aliases, couche_b source de vérité ✅

### Dettes ouvertes bloquantes pour M10A/M10B
| TD | Sprint cible |
|----|-------------|
| TD-011 | M10B — implémentation `extract_dao_criteria_structured` |
| TD-013 | M10A — SLA-B LlamaParse + Mistral OCR |

---

## 11. SCRIPTS UTILITAIRES (scripts/)

| Script | Usage | Statut |
|--------|-------|--------|
| `_force_036.py` | Restauration urgence DB → état 036 | STABLE |
| `apply_fk_prod.py` | FK `market_signals → vendors` ON DELETE RESTRICT (prod uniquement) | STABLE · ONE-SHOT PROD |
| `build_dictionary.py` | Build procurement dict depuis couche_b (M6) | STABLE |
| `run_tests_final.py` | pytest via subprocess Python (bypass spawn Windows) | STABLE |
| `_reset_vendor_seq.py` | Nettoie vendors TEST_* · remet séquence BKO < 10000 | LOCAL ONLY |
| `_probe_state_now.py` | Probe état DB (tables · types · FK · alembic) | DEBUG |
| `fix_alembic_version_017_to_018.py` | Fix manuel migration 017 supprimée (TD-014) | PENDING · À DOCUMENTER RUNBOOK |

---

## 12. DOCUMENTS DE RÉFÉRENCE

| Fichier | Rôle |
|---------|------|
| `docs/freeze/DMS_V4.1.0_FREEZE.md` | **Source de vérité unique** — 29 règles, architecture, schéma cible |
| `TECHNICAL_DEBT.md` | Inventaire dettes actives et fermées |
| `docs/milestones/HANDOVER_M4_TRANSMISSION.md` | Verdict enterprise-grade · failles F1–F9 · plan d'attaque |
| `docs/milestones/HANDOVER_M5FIX_TRANSMISSION.md` | Handover sprint M5-FIX (PIÈGE-8 à PIÈGE-15) |
| `docs/milestones/HANDOVER_M5PRE_TRANSMISSION.md` | Handover sprint M5-PRE |
| `docs/adrs/` | ADRs décisions architecturales |

---

*Agent : Composer · DMS V4.1.0 · Mopti, Mali · 2026-03-05*
*Sprints couverts cette session : M6 Dictionary Build (1488 items · 1596 aliases · couche_b source de vérité)*
