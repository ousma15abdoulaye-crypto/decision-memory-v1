# HANDOVER AGENT — DMS V4.1.0
**Date :** 2026-02-27
**Rédigé par :** Agent précédent (Claude Sonnet 4.6)
**Destinataire :** Agent successeur
**Branche active :** `main`
**Tag courant :** `v4.1.0-m0b-done` → commit `7a28df5`

---

## 1. CONTEXTE PROJET

**DMS = Decision Memory System**
Outil d'aide à la décision achats humanitaires pour Save the Children Mali.
Opérateur unique : Abdoulaye Ousmane (CTO/Founder), Mopti, Mali.
Stack : Python 3.11 · FastAPI · PostgreSQL 16 · Redis 7 · Railway · Alembic · psycopg v3 · pytest · ruff · black.

**Règle d'or RÈGLE-ORG-04 :** L'agent ne valide jamais un DoD seul. L'humain seul prononce le merge.
**Règle d'or RÈGLE-ORG-10 :** L'agent ne merge jamais vers `main`. Jamais.

---

## 2. ÉTAT DU REPO AU HANDOVER

### Git
```
Branche  : main
HEAD     : 7a28df5  fix: black formatting (3 fichiers)
Tag      : v4.1.0-m0b-done → 7a28df5
CI       : verte (491 passed · 35 skipped · 0 failed · 0 errors)
Alembic  : 036_db_hardening (head unique)
```

### Historique récent
```
7a28df5  fix: black formatting test_migration, test_m0b_db_hardening, test_pipeline_a_e2e_mode
db8a435  fix: ruff F401 suppression imports inutilises uuid et PipelineResult
d0571af  DoD M0B: rapport de validation docs/milestones/DOD_M0B_RAPPORT.md
d51a049  Merge feat/m0b-db-hardening: M0B DB Hardening (migration 036, ...)
38ebf67  DoD M0B: flakiness _restore_schema multi-worker documente dans TECHNICAL_DEBT
a805e01  M0B DB Hardening: migration 036, tests FK sha256, fix test_upgrade_downgrade
74190ab  Merge pull request #128 feat/m0-fix-ci
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
  ├── Committee            : members + seal, ACO + PV export
  └── Submission Registry  : dépôts, append-only triggers DB

COUCHE B — MÉMOIRE MARCHÉ (contexte / enrichissement)
  ├── Dictionary           : canonical + aliases, collision_log, proposals
  ├── Mercuriale Ingest    : 2023/24/25/26, sha256 idempotent, zone × année
  ├── Market Signal        : agrégation 3 sources, formule v1.0
  └── Decision Feedback    : seal() → decision_history → dict enrichment auto

INFRASTRUCTURE
  PostgreSQL 16 · Redis 7 · Railway · FastAPI · Alembic
```

### Arborescence src/ (76 fichiers)
```
src/
├── api/               FastAPI routers (cases, documents, analysis, health...)
├── couche_a/
│   ├── pipeline/      service.py · models.py · router.py
│   ├── extraction.py  ← STUB actif (time.sleep + return statique) — réservé M10A
│   ├── scoring/       engine.py · models.py · api.py
│   ├── criteria/      service.py · router.py
│   ├── committee/     service.py · snapshot.py · models.py · router.py
│   ├── price_check/   engine.py · schemas.py
│   └── analysis_summary/  engine/ (builder, service, models)
├── couche_b/
│   ├── mercuriale/    parser.py · schemas.py
│   ├── normalisation/ engine.py · schemas.py
│   └── resolvers.py
├── db/                core.py · connection.py
├── core/              config.py · models.py · dependencies.py
└── extraction/        engine.py
```

### Schéma DB (54 tables + 1 vue) — état 036_db_hardening
Tables principales :
```
cases · offers · lots · items · documents · extractions · extraction_corrections
extraction_jobs · extraction_errors · analyses · analysis_summaries
pipeline_runs · pipeline_step_runs · score_runs · scoring_configs
criteria · dao_criteria · decision_snapshots · committee_* (5 tables)
dictionary · dict_* (4 tables) · annotation_registry
artifacts · audits · users · roles · permissions
market_signals · market_data · mercuriale_raw_queue (via views)
submission_scores · supplier_scores · supplier_eliminations
```

Vue : `structured_data_effective` (join extractions + extraction_corrections)

---

## 4. MIGRATIONS ALEMBIC (36 migrations)

| # | Fichier | Contenu clé |
|---|---------|-------------|
| 002 | add_couche_a | cases, offers, lots, items, documents, extractions, analyses, audits |
| 013 | add_m_extraction_engine_documents_columns | mime_type, storage_uri, extraction_status, extraction_method sur documents |
| 014 | ensure_extraction_tables | document_id, raw_text, structured_data sur extractions |
| 015 | m_extraction_corrections | extraction_corrections + structured_data_effective view |
| 032 | create_pipeline_runs | pipeline_runs (append-only) |
| 033 | create_pipeline_step_runs | pipeline_step_runs (append-only) |
| 034 | add_force_recompute_pipeline_runs | force_recompute sur pipeline_runs |
| 035 | create_analysis_summaries | analysis_summaries (append-only) |
| **036** | **db_hardening** | FK NOT VALID, committee_delegations, dict_collision_log, annotation_registry, sha256, triggers append-only, fn_sre_*, 8 index |

**ATTENTION migration 036 :**
- `fk_pipeline_runs_case_id` créée `NOT VALID` (données orphelines existantes)
- `documents.sha256` ajouté nullable (backfill non fait)
- Tables créées : `committee_delegations`, `dict_collision_log`, `annotation_registry`
- Tables référencées dans TECHNICAL_DEBT mais **absentes en DB** :
  `audit_log`, `score_history`, `elimination_log`, `decision_history`,
  `submission_registries`, `submission_registry_events`, `mercurials`

---

## 5. TESTS — ÉTAT ACTUEL

**CI : 491 passed · 35 skipped · 0 failed**

### Fichiers tests clés
```
tests/
├── test_m0b_db_hardening.py           Tests migration 036 (FK, sha256, tables, triggers)
├── couche_a/
│   └── test_migration.py              ← FICHIER CRITIQUE (voir section 7)
├── db_integrity/
│   └── test_pipeline_append_only_triggers.py
├── pipeline/
│   ├── test_pipeline_a_e2e_mode.py
│   └── test_pipeline_a_partial_statuses.py
└── analysis_summary/ · criteria/ · committee/ · ...
```

### Fixtures conftest racine
- `db_conn` : connexion autocommit=True — pour tests triggers/FK
- `db_transaction` : curseur avec rollback automatique — pour tests isolés
- `db_engine` : SQLAlchemy engine (session-scoped)
- `case_factory` : crée un `cases` réel en DB — **obligatoire** pour tous inserts dans `pipeline_runs` (FK active)

### Tests SKIPPED (35)
- `test_sla_classe_b_has_queue` — SLA-B extraction (M10A)
- `test_sla_classe_a_60s` — performance (désactivé)
- Tests `offers` preflight — table présente mais tests configurés SKIP
- `market_signal` — hors scope M0

---

## 6. DETTE TECHNIQUE DOCUMENTÉE (TECHNICAL_DEBT.md)

### A. Stub actif — NE PAS TOUCHER avant M10A
```python
# src/couche_a/extraction.py:416
# extract_offer_content() → time.sleep(2) + return {"status": "completed"}
# Corps complet stub — SLA-B non implémenté
```

### B. FK NOT VALID — à valider après nettoyage orphelins
```sql
-- Audit orphelins d'abord :
SELECT pr.id, pr.case_id FROM pipeline_runs pr
LEFT JOIN cases c ON c.id = pr.case_id WHERE c.id IS NULL;

-- Puis valider :
ALTER TABLE pipeline_runs VALIDATE CONSTRAINT fk_pipeline_runs_case_id;
```

### C. sha256 nullable — backfill requis (M1+)
```sql
UPDATE documents
SET sha256 = encode(digest(storage_uri, 'sha256'), 'hex')
WHERE sha256 IS NULL;
-- Puis : ALTER TABLE documents ALTER COLUMN sha256 SET NOT NULL;
```

### D. Types PK non conformes (post-beta uniquement)
| Table | PK réelle | PK freeze | Action |
|---|---|---|---|
| documents | id TEXT | UUID | Migration dédiée post-beta |
| procurement_references | id TEXT | UUID | Migration dédiée post-beta |
| committee_members | member_id | id | Renommer post-beta |

### E. Flakiness potentielle CI multi-worker
`tests/couche_a/test_migration.py::_restore_schema` — deux transactions séparées.
**Pas de risque en CI séquentielle actuelle.** Risque si `pytest-xdist -n auto` activé.

### F. Dettes d'environnement
| Item | Local | Cible |
|---|---|---|
| Python | 3.11.0 | 3.11.9 (runtime.txt) |
| app_user DB | absent | rôle à créer (M1) |

---

## 7. PIÈGE CONNU — test_migration.py (CRITIQUE)

`tests/couche_a/test_migration.py::test_upgrade_downgrade` appelle directement
`migration_002.downgrade(engine)` qui **drop avec CASCADE** :
`documents`, `extractions`, `offers`, `analyses`, `lots`, `items`, `audits`.

Cela **corrompt le schéma DB** pour les tests suivants si `_restore_schema` échoue.

**Protection actuelle :** bloc `try/finally` avec `_restore_schema()` qui :
1. Appelle `migration_002.upgrade(engine)` — recrée les tables IF NOT EXISTS
2. Stamp `alembic_version = 036_db_hardening`
3. Réapplique toutes les colonnes critiques (sha256, document_id, etc.)
4. Recrée la vue `structured_data_effective`
5. Recrée index et contrainte unique 036

**Si ce test échoue isolément → la DB peut être dans un état corrompu.**
Commande de récupération d'urgence : `python scripts/_force_036.py`

---

## 8. RÈGLES SYSTÈME (INVIOLABLES)

| Règle | Énoncé |
|---|---|
| RÈGLE-01 | 1 milestone = 1 branche = 1 PR = 1 merge = 1 tag Git |
| RÈGLE-03 | CI rouge = STOP TOTAL |
| RÈGLE-05 | Append-only sur toute table décisionnelle / audit / traçabilité |
| RÈGLE-06 | DONE ou ABSENT. Rien entre les deux. |
| RÈGLE-08 | PROBE-SQL-01 avant toute migration touchant une table existante |
| RÈGLE-09 | `winner` / `rank` / `recommendation` = INTERDITS hors comité humain |
| RÈGLE-10 | `status=complete` = réservé M15 exclusivement |
| RÈGLE-12 | Migrations = `op.execute()` SQL brut. ZÉRO autogenerate. |
| RÈGLE-17 | Toute migration = 1 test minimum prouvant l'invariant visé |
| RÈGLE-ORG-04 | DoD = checklist validée par l'humain avant merge. Jamais par l'agent. |
| RÈGLE-ORG-07 | Fichier hors périmètre modifié = revert immédiat |
| RÈGLE-ORG-08 | Chaque mandat commence par PROBE (état réel avant modification) |
| RÈGLE-ORG-10 | **L'agent ne merge JAMAIS vers main** |

---

## 9. PROCHAINES ÉTAPES — PLAN M1 (Security Baseline)

> Le plan détaillé M1 n'a pas encore été posé par l'humain.
> Ces points sont inférés du freeze DMS V4.1.0 et des dettes M0B.

### Acte 1 obligatoire — PROBE-SQL-01
Avant tout code M1, sonder l'état réel :
```sql
-- Orphelins pipeline_runs
SELECT COUNT(*) FROM pipeline_runs pr
LEFT JOIN cases c ON c.id = pr.case_id WHERE c.id IS NULL;

-- Rôle app_user
SELECT rolname FROM pg_roles WHERE rolname = 'app_user';

-- REVOKE sur tables append-only
SELECT grantee, table_name, privilege_type
FROM information_schema.role_table_grants
WHERE table_name IN ('pipeline_runs','analysis_summaries','audits')
  AND privilege_type IN ('UPDATE','DELETE');
```

### Points M1 attendus (d'après freeze V4.1.0 + TECHNICAL_DEBT)
1. **Créer rôle `app_user`** + REVOKE UPDATE/DELETE sur tables append-only
2. **VALIDATE CONSTRAINT fk_pipeline_runs_case_id** (après nettoyage orphelins)
3. **Backfill `documents.sha256`** + ALTER COLUMN SET NOT NULL
4. **Audit migrations 001–035** : downgrade() sécurisé ou supprimé
   → Question ouverte : M0C dédié ou intégré M1 ?
5. **RBAC** : endpoints non protégés (périmètre à définir)
6. **Rate limiting / upload security** : `src/upload_security.py` existant → tester

### Question stratégique en suspens
> Audit downgrade() 001–035 (sécurisation `test_migration.py`) :
> **M1 ou M0C dédié ?**
> À trancher par l'humain avant ouverture M1.

---

## 10. SCRIPTS UTILITAIRES (scripts/)

| Script | Usage |
|---|---|
| `_force_036.py` | Restauration urgence DB → état 036 |
| `_dod_m0b_probe.py` | Sonde complète DoD M0B (6 vérifications DB) |
| `_dod_probe_234.py` | Sondes rapides colonnes/FK/tables |
| `_check_extractions.py` | Vérifie colonnes table extractions |
| `_probe_cases_cols.py` | Colonnes table cases |
| `_apply_sha256.py` | Applique colonne sha256 manuellement (urgence) |
| `_apply_uq_sha256.py` | Applique contrainte unique (urgence) |

---

## 11. DOCUMENTS DE RÉFÉRENCE

| Fichier | Rôle |
|---|---|
| `docs/freeze/DMS_V4.1.0_FREEZE.md` | **Source de vérité unique** — 29 règles, architecture, schéma cible |
| `TECHNICAL_DEBT.md` | Inventaire dettes actives (M0 + M0B) |
| `docs/milestones/DOD_M0B_RAPPORT.md` | Rapport validation DoD M0B |
| `docs/ci/ci_diagnosis.txt` | Diagnostic CI M0 (contexte Windows local) |
| `docs/adrs/` | ADRs décisions architecturales |

---

## 12. ERREURS / PIÈGES RENCONTRÉS — À NE PAS RÉPÉTER

| Piège | Cause | Fix |
|---|---|---|
| `sha256` disparaît après pytest full | `test_migration.py::downgrade()` drop tables CASCADE | `_restore_schema()` dans try/finally |
| FK violation sur `pipeline_runs` insert | `fk_pipeline_runs_case_id` active + case_id ghost | Utiliser `case_factory()` dans tous les tests qui insèrent dans `pipeline_runs` |
| `ForeignKeyViolation` à `alembic upgrade head` | Orphelins dans `pipeline_runs` | FK créée `NOT VALID` |
| PowerShell `&&` invalide | PowerShell n'accepte pas `&&` en ligne | Séparer les commandes ou utiliser scripts `.py` |
| Quotes Python inline PowerShell | Guillemets imbriqués | Toujours passer par un fichier `.py` script |
| Black/ruff non vérifiés avant commit | Oubli | Toujours lancer `ruff check` + `black --check` avant push |
| Merge vers main sans autorisation | Mauvaise lecture mandat | **RÈGLE-ORG-10 : jamais de merge sans feu vert humain explicite** |
