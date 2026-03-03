# NOTE DE TRANSMISSION — M5-PRE-HARDENING · SPRINT CLOS

```
Date de clôture : 2026-03-03
Sprint          : M5-PRE-HARDENING (sprint de stabilisation pré-M5)
Agent           : Claude Sonnet 4.6 (sessions 2026-03-03)
Branche         : feat/m5-pre-hardening → PR #152 → merged main
Tag             : v4.1.0-m5-pre-hardening
Successeur      : Agent M5 (Mercuriale Ingest)
Référence V4    : docs/freeze/DMS_V4.1.0_FREEZE.md (source de vérité unique)
```

---

## I. ÉTAT SYSTÈME À LA CLÔTURE

| Élément | Valeur |
|---|---|
| Branche de référence | `main` |
| Alembic head | `m5_pre_vendors_consolidation` · **1 seul head** |
| Tag Git | `v4.1.0-m5-pre-hardening` → commit `8ed7609` |
| Tests | **726 passed · 36 skipped · 0 failed** |
| ruff | **0 erreur** |
| black | **239 files unchanged** |
| `vendors` | Table canonique · 34 colonnes · ex `vendor_identities` |
| DB prod Railway | `m5_pre_vendors_consolidation` à appliquer au prochain deploy |
| `vendor_identities` | SUPPRIMÉE · renommée en `vendors` par la migration |
| `vendors` legacy | SUPPRIMÉE · 2 lignes seed nettoyées manuellement en prod |

### Tags posés sur main

| Tag | Commit | Contenu |
|---|---|---|
| `v4.1.0-m5-pre-hardening` | `8ed7609` | Consolidation vendors + hardening D1-D4 · PR #152 |

---

## II. CE QUE CE SPRINT A LIVRÉ

### Migration principale

**`alembic/versions/m5_pre_vendors_consolidation.py`**
- `down_revision = "m4_patch_a_fix"`
- `revision = "m5_pre_vendors_consolidation"`
- Consolide `vendor_identities → vendors` (RENAME) avec DROP de `vendors` legacy
- Drop explicite FK `market_signals_vendor_id_fkey` avant DROP TABLE (chirurgical)
- Gardes idempotentes : 3 niveaux (vendor_identities absente / vendors absente / données métier actives)
- Downgrade partiel honnête et documenté (vendors legacy non recréée, FK non restaurée)
- Cycle down/up validé localement · CI verte 726 passed

### Hardening D1–D4 (ADR-M5-PRE-001)

| Hardening | Fichier | Description |
|---|---|---|
| D1 | `src/db/core.py` | Lazy init `DATABASE_URL` via `_get_or_init_db_url()` + `_DB_URL_CACHE` |
| D2 | `src/vendors/repository.py` | `_PUBLIC_COLUMNS` remplace `SELECT *` · NIF/RIB/RCCM exclus de l'API |
| D3 | `src/api/main.py` | Fail-loud routers obligatoires · logger WARNING optionnels · `startup_check()` |
| D4 | `src/vendors/region_codes.py` | Codes `KLK` et `INT` documentés RÉSERVÉS |

### Corrections code

| Fichier | Nature |
|---|---|
| `src/vendors/repository.py` | Toutes les requêtes `vendor_identities → vendors` |
| `src/couche_b/resolvers.py` | `resolve_vendor` : retourne `vendor_id` (UUID) au lieu de `id` (int) |
| `tests/vendors/test_*.py` (6 fichiers) | Références `vendor_identities → vendors` + head Alembic |
| `tests/couche_b/test_resolvers.py` | Fixtures adaptées schéma 34 colonnes `vendors` |
| `tests/geo/test_geo_migration.py` | Head attendu mis à jour |
| `tests/test_m0b_db_hardening.py` | Head attendu mis à jour |

### Documentation

| Fichier | Mise à jour |
|---|---|
| `docs/dev/migration-checklist.md` | Section 8 : chaîne post-M4, FK supprimée, downgrade partiel |
| `TECHNICAL_DEBT.md` | TD-004 FERMÉE · TD-005 FERMÉE · TD-006 FERMÉE · TD-008 FERMÉE · TD-009 partial update |
| `docs/adr/ADR-M5-PRE-001_pre-m5-hardening.md` | ADR de référence (rédigé sprint précédent) |

---

## III. OPÉRATIONS PROD RAILWAY EFFECTUÉES

### Backup prod (avant merge)

- **Fichier :** `dms_prod_backup_20260303_090729.sql` (16.2 KB · racine projet)
- **Technique :** Python psycopg3 direct (pg_dump 15 incompatible avec PostgreSQL 17.7 Railway)
- **Contenu :** 48 lignes de données · schema + INSERT pour toutes les tables non-vides
- **Connexion :** URL Railway passée en runtime via env `PROD_URL` · **jamais hardcodée ni committée**

### Nettoyage prod préventif

- `DELETE FROM vendors` → 2 lignes seed supprimées (Marché Central + Boutique Kayes, issues de `005_add_couche_b.py`)
- `market_signals` était vide (0 lignes) → aucune donnée métier perdue
- Migration `m5_pre_vendors_consolidation` passera proprement en prod (vendors = 0 lignes)

---

## IV. PIÈGES RENCONTRÉS — À NE PAS RÉPÉTER

### PIÈGE-1 · Double mandat en cours de session (V1 → V2)

Le mandat initial (V1) a été annulé et remplacé par V2 en cours de session.
L'agent V1 avait déjà appliqué une migration `m5_patch_pre_vendors_consolidation_v410`
à la DB locale via les fixtures pytest, créant un état DB inattendu.

**Fix :** `git stash`, `alembic stamp` au head stable, reconstruire la migration depuis zéro.
**Règle à retenir :** PROBE-SQL-01 systématique avant TOUTE modification de migration.

### PIÈGE-2 · vendors legacy contient des données (005_add_couche_b.py)

`005_add_couche_b.py` seed 2 lignes dans `vendors` legacy au moment de sa migration.
Ces lignes bloquent toute garde `COUNT(vendors) > 0` si le guard est naïf.

**Symptôme CI :** `vendors legacy contient 2 ligne(s) — DROP refusé`
**Fix final :** Garde croisée avec `market_signals` — DROP autorisé si 0 références actives.
**En prod :** nettoyage manuel requis avant premier deploy de la migration.

### PIÈGE-3 · pg_dump version mismatch Railway

Railway PostgreSQL = version 17.7. pg_dump local = version 15.
`pg_dump` 15 refuse de dumper un serveur 17 (`annulation à cause de la différence des versions`).

**Fix :** Backup Python via psycopg3 (script temporaire, URL runtime uniquement).

### PIÈGE-4 · Downgrade partiel non réversible

La migration `m5_pre_vendors_consolidation` downgrade ne recrée pas `vendors` legacy.
Après `alembic downgrade -1`, un `alembic upgrade head` déclenche RAISE EXCEPTION
"vendors legacy introuvable — état inattendu".

**Ce n'est pas un bug.** C'est documenté dans le downgrade.
Pour rollback complet : restaurer depuis backup Railway.
Ne jamais tester downgrade/upgrade en boucle sur la DB prod.

### PIÈGE-5 · FK market_signals_vendor_id_fkey jamais visible en local post-consolidation

La FK existe dans l'état "pre-consolidation" uniquement (créée par `005_add_couche_b.py`).
Après la migration, la FK est supprimée. En local post-consolidation, probe FK → 0 résultats.

**Solution :** Lire le code source de `005_add_couche_b.py` pour connaître le nom.
Convention PostgreSQL `{table}_{colonne}_fkey` confirme `market_signals_vendor_id_fkey`.

### PIÈGE-6 · Cycle downgrade + restore DB laisse contraintes dans l'état vi_

Le downgrade renomme les contraintes (`vendors_* → vendor_identities_*`/`uq_vi_*`)
mais pas la table si l'état est hybride. Si `alembic stamp` est utilisé pour forcer
l'état Alembic sans exécuter les DDL de la migration, les contraintes restent incohérentes.

**Symptôme :** `test_pa4_canonical_name_unique_constraint` · `test_pa7_couche_b_indexes_exist` → FAILED
**Fix :** Script `_fix_constraints_rename.py` pour réappliquer les renames manuellement.

### PIÈGE-7 · PowerShell ne supporte pas && et les guillemets inline

Windows PowerShell ne supporte pas `&&` ni les quotes imbriquées pour Python `-c`.
**Fix systématique :** Toujours passer par un fichier `.py` script pour les opérations multi-lignes.

---

## V. FAILLES ARCHITECTURE VUES DANS LE SYSTÈME

### F1 · DB prod vierge de données métier après M5-PRE

La DB prod Railway était entièrement vide de données métier à la clôture :
- `vendor_identities` : 0 lignes (ETL wave 1/2 = local uniquement)
- `cases` : 0 lignes
- `market_signals` : 0 lignes
- Seules données : 1 user admin + tables geo/scoring seed

**Conséquence :** M5 Mercuriale doit inclure l'import des données vers prod ou
documenter explicitement que prod reste staging jusqu'à M14/M15.

### F2 · market_signals.vendor_id = INTEGER orphelin post-consolidation

Après `m5_pre_vendors_consolidation`, `market_signals.vendor_id` est une colonne `INTEGER`
sans contrainte FK (la FK a été supprimée, et le nouveau `vendors.vendor_id` est UUID).
Il n'y a aucune contrainte d'intégrité entre `market_signals` et le référentiel vendeur.

**Risque :** Si des market_signals sont créées en M5+, elles peuvent référencer des
vendor_id entiers qui ne correspondent à rien dans `vendors` (UUID-based).

**Action recommandée M5 :** Décider si `market_signals.vendor_id` doit être migré
de `INTEGER` vers `TEXT`/`UUID` pour s'aligner avec `vendors.vendor_id`.

### F3 · Chaîne Alembic hors convention numérique (3 migrations)

Trois migrations ne suivent pas `NNN_nom.py` :
`m4_patch_a_vendor_structure_v410` → `m4_patch_a_fix` → `m5_pre_vendors_consolidation`

La prochaine migration M5 doit absolument déclarer :
```python
down_revision = "m5_pre_vendors_consolidation"
```
Oublier ce nom exact → double head → crash deploy Railway.

### F4 · 005_add_couche_b.py seed data dans vendors legacy

`005_add_couche_b.py` insère des données test dans `vendors` (Marché Central, Boutique Kayes).
Ces données "fantômes" bloquent toute migration qui cherche une table vide.
Le pattern `INSERT ... ON CONFLICT DO NOTHING` dans les migrations crée de la dette invisible.

**À surveiller M5+ :** toute migration touchant `units`, `geo_master`, `items` a le même pattern.

### F5 · market_signals.vendor_id type mismatch (INTEGER vs UUID)

Type mismatch structurel : `market_signals.vendor_id INTEGER` vs `vendors.vendor_id TEXT/UUID`.
Ces deux tables ne peuvent pas avoir de FK entre elles sans migration de type.
La FK originale `market_signals_vendor_id_fkey` pointait vers `vendors.id INTEGER` (ancien schéma).
Ce n'est plus cohérent avec le schéma cible V4.1.0.

---

## VI. CHAIN ALEMBIC À LA CLÔTURE

```
001_initial_schema
002_add_couche_a
...
005_add_couche_b
...
039_created_at_timestamptz
040_geo_master_mali
041_vendor_identities
042_vendor_fixes
043_vendor_activity_badge
m4_patch_a_vendor_structure_v410
m4_patch_a_fix
m5_pre_vendors_consolidation   ← HEAD (v4.1.0-m5-pre-hardening)
```

**Prochain down_revision obligatoire pour M5 :**
```python
down_revision = "m5_pre_vendors_consolidation"
```

---

## VII. PROCHAINES ÉTAPES — PLAN M5 (Mercuriale Ingest)

D'après `docs/freeze/DMS_V4.1.0_FREEZE.md` (RÈGLE-ORG-02 : lire avant de commencer) :

### Objectif M5

> Ingestion brute des 4 mercuriales officielles Mali (2023/2024/2025/2026)
> Actif disponible : ~2 000 articles mercuriels
> Head attendu freeze : `040_mercuriale_ingest` (nom conventionnel à adapter à la chaîne réelle)

### Séquence attendue RÈGLE-02

```
DB → tests DB → services → endpoints → CI verte
```

### PROBE-SQL-01 M5 obligatoire (RÈGLE-08)

Avant tout commit M5, sonder l'état réel de la DB prod et des tables Couche B :

```sql
-- État table vendors post-m5_pre
SELECT COUNT(*) FROM vendors;
SELECT column_name FROM information_schema.columns
WHERE table_name='vendors' ORDER BY ordinal_position;

-- Tables Couche B existantes
SELECT table_name FROM information_schema.tables
WHERE table_schema='public' AND table_name LIKE '%mercuri%';

-- market_signals.vendor_id type réel
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name='market_signals' AND column_name='vendor_id';

-- Alembic heads (1 seul obligatoire)
SELECT version_num FROM alembic_version;
```

### Points critiques M5

1. **Migration naming** : `down_revision = "m5_pre_vendors_consolidation"` (obligatoire)
2. **market_signals.vendor_id** : décider migration type INTEGER → UUID/TEXT avant M5
3. **Import mercuriale** : local uniquement ou vers prod ? → décision CTO
4. **Table `mercuriale_raw_queue`** : déjà dans le schéma via migrations antérieures à vérifier
5. **RÈGLE-29** : M5 = ingestion brute → M6 = construction canonique (séquence non inversible)
6. **RÈGLE-05** : tables mercuriale = append-only si contiennent données décisionnelles

### Dettes actives à surveiller en M5

| Ref | Statut | Impact M5 |
|---|---|---|
| TD-001 | ACTIVE | `vendor_id` MAX+1 non atomique — import séquentiel seulement |
| TD-002 | ACTIVE | Index GIN trigram manquant — `match_vendor_by_name()` M11 |
| TD-003 | ACTIVE | `zones_covered` et `category_ids` vides — peuplement M5/M6 |
| TD-007 | ACTIVE | Connection pooling absent — Railway 25 cnx max |
| DETTE-M1-04 | ACTIVE | `users.role_id` INTEGER legacy — conditions DROP non réunies |
| DETTE-M2-02 | ACTIVE | Rate limiting per-route no-op |

---

## VIII. RÈGLES INVIOLABLES (RAPPEL POUR AGENT M5)

| Règle | Énoncé |
|---|---|
| RÈGLE-01 | 1 milestone = 1 branche = 1 PR = 1 merge = 1 tag Git |
| RÈGLE-03 | CI rouge = STOP TOTAL |
| RÈGLE-08 | PROBE-SQL-01 avant toute migration touchant une table existante |
| RÈGLE-12 | Migrations = SQL brut `op.execute()` — ZÉRO autogenerate |
| RÈGLE-17 | Toute migration = 1 test minimum prouvant l'invariant visé |
| RÈGLE-ORG-02 | Lire `docs/freeze/DMS_V4.1.0_FREEZE.md` EN ENTIER avant de commencer |
| RÈGLE-ORG-04 | DoD = checklist validée par l'humain avant merge. Jamais par l'agent seul. |
| RÈGLE-ORG-10 | **L'agent ne merge JAMAIS vers main** |
| RÈGLE-ORG-11 | Chemin ADR = `docs/adr/` (singulier · invariant) |

---

## IX. SCRIPTS UTILITAIRES (scripts/)

| Script | Usage | Statut |
|---|---|---|
| `_force_036.py` | Restauration urgence DB → état 036 | STABLE |
| `_probe_vendors_state.py` | Probe contraintes/indexes vendors | AJOUTÉ M5-PRE |
| `_fix_constraints_rename.py` | Réappliquer renames vi_→vendors_ si état hybride | AJOUTÉ M5-PRE |
| `_probe_fk_vendors.py` | Probe FK vers vendors/vendor_identities | AJOUTÉ M5-PRE |
| `_restore_m5pre.py` / `_restore_m5pre2.py` | Restauration DB post-downgrade | AJOUTÉ M5-PRE |

---

## X. DOCUMENTS DE RÉFÉRENCE

| Fichier | Rôle |
|---|---|
| `docs/freeze/DMS_V4.1.0_FREEZE.md` | **Source de vérité unique** — 29 règles · architecture · schéma cible |
| `TECHNICAL_DEBT.md` | Inventaire dettes actives — mis à jour 2026-03-03 |
| `docs/adr/ADR-M5-PRE-001_pre-m5-hardening.md` | ADR failles F1-F9 · plan Phases 0-3 |
| `docs/dev/migration-checklist.md` | Checklist migrations · section 8 = chaîne post-M4 |
| `dms_prod_backup_20260303_090729.sql` | Backup prod avant merge M5-PRE (16.2 KB) |

---

## XI. DEBRIEF TECHNIQUE — TECHNIQUE UTILISÉE POUR LE BACKUP PROD

**Problème :** Railway PostgreSQL = v17.7. pg_dump local (PostgreSQL 15) refuse de dumper.
**Solution :** Script Python temporaire + psycopg3 direct.
- Connexion via URL Railway passée exclusivement en variable d'environnement (`PROD_URL`)
- URL jamais écrite dans un fichier · jamais committée · script supprimé après usage
- Dump SQL avec INSERT pour chaque table non-vide
- Script effacé immédiatement après usage (`scripts/_backup_railway_tmp.py` → deleted)
- Fichier backup conservé localement uniquement (non committé)

**Pattern à réutiliser pour M5+ :** même approche pour tout accès prod direct.

---

## XII. MÉTRIQUES DE CLÔTURE

| Métrique | Valeur |
|---|---|
| Tests | 726 passed · 36 skipped · 0 failed |
| Couverture dettes fermées ce sprint | 5 (TD-004 · TD-005 · TD-006 · TD-008 · TD-009 partial) |
| Migration créée | `m5_pre_vendors_consolidation` |
| Fichiers modifiés | 17 (alembic · src · tests · docs) |
| Commits M5-PRE | 4 (`bb3aa09` · `ec45e8d` · `501f5ed` · `e2d8ce9`) |
| PR GitHub | #152 mergée · tag `v4.1.0-m5-pre-hardening` posé |
| DB prod Railway | Sauvegardée · vendors seed nettoyée · prête pour migration |

---

*Agent : Claude Sonnet 4.6 · DMS V4.1.0 · Mopti, Mali · 2026-03-03*
*Réf. V4 : docs/freeze/DMS_V4.1.0_FREEZE.md · RÈGLE-ORG-02*
