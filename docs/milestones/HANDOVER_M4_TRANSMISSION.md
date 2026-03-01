# NOTE DE TRANSMISSION — M4 · VENDOR IMPORTER MALI + PATCH

```
Date       : 2026-03-01 / 2026-03-02
Milestone  : M4 — VENDOR IMPORTER MALI + PATCH M4
Branches   : feat/m4-vendor-importer (PR#142) · feat/m4-patch (PR#143)
Statut     : EN ATTENTE MERGE CTO — PR#142 puis PR#143
             Tags à poser par CTO : v4.1.0-m4-done · v4.1.0-m4-patch-done
Agent      : Claude Sonnet 4.6 (session 2026-03-01/02)
Successeur : Agent M5 (après merge + tag CTO)
```

---

## I. ÉTAT DU REPO À LA TRANSMISSION

| Élément | État |
|---|---|
| Branche active | `feat/m4-patch` (commit `262991f`) |
| Branche M4 base | `feat/m4-vendor-importer` (commit `aaad4a9`) |
| Alembic head local | `043_vendor_activity_badge` — exactement 1 head |
| CI locale M4 + patch | **702 passed · 36 skipped · 0 failed** |
| ruff | 0 erreur |
| black | 0 erreur |
| PR#142 | `feat/m4-vendor-importer` → `main` — **EN ATTENTE MERGE CTO** |
| PR#143 | `feat/m4-patch` → `feat/m4-vendor-importer` — **EN ATTENTE MERGE CTO** |
| DB locale | Migrations 041 + 042 + 043 appliquées · 0 vendors (nettoyés par tests) |
| DB prod Railway | 102 vendors EXCEL_M4 présents · `041` appliqué en prod |
| Tags | À poser par CTO après merge — jamais par l'agent |

---

## II. CE QUE M4 A LIVRÉ

### 2.1 Migration `041_vendor_identities`

Table principale des fournisseurs :

| Colonne | Type | Contrainte |
|---|---|---|
| `id` | UUID | PK · `gen_random_uuid()` |
| `vendor_id` | TEXT | UNIQUE · `CHECK LIKE 'DMS-VND-%'` (renforcé en 042) |
| `fingerprint` | TEXT | UNIQUE · SHA256 anti-doublon |
| `name_raw` | TEXT | NOT NULL |
| `name_normalized` | TEXT | NOT NULL |
| `zone_raw` / `zone_normalized` | TEXT | calculé par `normalizer.py` — pas GENERATED COLUMN |
| `region_code` | TEXT | NOT NULL · CHECK canonique (10 régions) |
| `email` / `phone` | TEXT | nullable · normalisés applicativement |
| `email_verified` | BOOLEAN | NOT NULL DEFAULT FALSE |
| `is_active` | BOOLEAN | NOT NULL DEFAULT TRUE |
| `source` | TEXT | NOT NULL DEFAULT 'MANUAL' |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL · trigger `fn_set_updated_at()` |

Caractéristiques :
- Raw SQL uniquement — zéro autogenerate
- `IF NOT EXISTS` / `OR REPLACE` — idempotence prod
- Garde défensive `fn_set_updated_at()` en tête d'upgrade
- Extension `unaccent` installée (retirée en 042 — normalisation Python)

### 2.2 Migration `042_vendor_fixes` (Patch M4)

Correctifs techniques post-merge Copilot AI :

| Fix | Action |
|---|---|
| FIX-1 | CHECK `vendor_id` : `LIKE 'DMS-VND-%'` → regex `^DMS-VND-[A-Z]{3}-[0-9]{4}-[A-Z]$` |
| FIX-2 | Trigger `trg_vendor_updated_at` rebuild sans `OR REPLACE` (PG12+ compatible) |
| FIX-3 | Extension `unaccent` retirée — normalisation Python uniquement (ADR-0003) |

### 2.3 Migration `043_vendor_activity_badge` (Patch M4)

Badge activité fournisseur — décision CTO :

| Colonne | Type | Contrainte |
|---|---|---|
| `activity_status` | TEXT | NOT NULL DEFAULT 'UNVERIFIED' · CHECK canonique (4 valeurs) |
| `last_verified_at` | TIMESTAMPTZ | nullable |
| `verified_by` | TEXT | nullable |
| `verification_source` | TEXT | nullable · CHECK canonique (5 valeurs) |

Valeurs `activity_status` : `VERIFIED_ACTIVE` · `UNVERIFIED` · `INACTIVE` · `GHOST_SUSPECTED`

Valeurs `verification_source` : `SCI_FIELD_VISIT` · `PHONE_CONFIRMATION` · `DOCUMENT_REVIEW` · `LEGACY_IMPORT` · `MANUAL_ENTRY`

**DÉCISION CTO inscrite en migration** : les 102 vendors `EXCEL_M4` sont marqués `VERIFIED_ACTIVE` (listes SCI de visites terrain réelles).

### 2.4 Module `src/vendors/`

| Fichier | Contenu |
|---|---|
| `__init__.py` | Module marker |
| `models.py` | Pydantic v2 · `VendorOut` read-only |
| `normalizer.py` | Source de vérité normalisation — `normalize_text/zone/name/email/phone` |
| `region_codes.py` | `ZONE_TO_REGION` · `ALL_REGION_CODES` · `build_vendor_id()` · checksum maison |
| `repository.py` | psycopg pur — `insert_vendor` (ON CONFLICT) · `get_next_sequence` (regex) · `get_vendor_by_id` · `list_vendors` |
| `service.py` | Thin wrapper repository |
| `router.py` | `GET /vendors` (filtre region + activity_status) · `GET /vendors/{id}` |

### 2.5 DMS_VENDOR_ID — Format et génération

```
Format  : DMS-VND-{REGION}-{SEQ:04d}-{CHK}
Exemple : DMS-VND-BKO-0001-K

Génération :
  1. get_next_sequence(conn, region_code)  → MAX(seq)+1 par région (TD-001)
  2. build_vendor_id(region_code, seq)     → format + checksum maison SHA256
  3. INSERT ... ON CONFLICT (fingerprint) DO NOTHING

RÈGLE ABSOLUE : jamais généré dans un DataFrame ETL.
Généré dans repository.insert_vendor() · en transaction · toujours.
```

### 2.6 Fingerprint anti-doublon

```python
# Source : src/vendors/repository.py · generate_fingerprint()
canonical = f"{name_normalized}|ML|{region_code}"
fingerprint = sha256(canonical.encode()).hexdigest()[:16]

# Même nom normalisé + même région → même fingerprint → ON CONFLICT → skipped
# Même nom + région différente → fingerprints distincts → deux vendors distincts
```

### 2.7 Script ETL `scripts/etl_vendors_m4.py`

| Paramètre | Valeur |
|---|---|
| Fichiers source | `Supplier DATA BAMAKO.xlsx` (header=2) · `Supplier DATA Mopti et autres zones nords.xlsx` (header=0) |
| Seuil WARN | 5% → warning · import continue |
| Seuil STOP | 15% → STOP-M4-G · SystemExit |
| Badge | `VERIFIED_ACTIVE` · `SCI_FIELD_TEAM_MALI` · `SCI_FIELD_VISIT` |

**Note BAMAKO** : le fichier Bamako a 2 lignes méta en tête. `pd.read_excel(..., header=2)` obligatoire.

Résultat import réel (2026-03-01) :
```
Total lu : 103 · Importés : 102 · Doublons : 1 · Rejetés : 0 · Taux rejet : 0.0%
BKO: 50 · MPT: 46 · TBK: 5 · GAO: 1
```

### 2.8 Endpoints exposés (M4)

```
GET /vendors                          → liste paginée · filtre region + activity_status
GET /vendors?region=BKO               → uniquement BKO
GET /vendors?activity_status=VERIFIED_ACTIVE → uniquement verts
GET /vendors?activity_status=INVALID  → 422 (validation canonique)
GET /vendors/{vendor_id}              → détail · 404 si inexistant
```

Hors périmètre M4 (jamais implémentés) :
```
POST/PUT/PATCH/DELETE /vendors        → lecture seule uniquement
vendor_zone_coverage                  → M5
vendor_external_refs                  → M5+
```

### 2.9 Tests `tests/vendors/` — 62 tests

| Fichier | Tests | Couvre |
|---|---|---|
| `test_vendor_migration.py` | 7 | Table, head alembic, CHECK, UNIQUE, trigger, colonnes |
| `test_vendor_etl.py` | 28 | normalize_*, ZONE_TO_REGION, taux rejet, ETLReport |
| `test_vendor_seed.py` | 4 | Dry-run · import réel · IDs uniques · distribution régions |
| `test_vendor_endpoints.py` | 5 | GET /vendors · filtres · 404 · pagination |
| `test_vendor_dedup.py` | 4 | Fingerprint · ON CONFLICT · casse · régions distinctes |
| `test_vendor_patch.py` | 14 | P1-P12 patch · regex · badge · activity_status · TD-001 |

---

## III. TECHNICAL_DEBT.MD — MISES À JOUR M4

### Ajouté en M4-patch

**`TD-001`** — `vendor_id MAX()+1` non atomique :
- `get_next_sequence()` utilise `MAX()+1` — non atomique
- Risque : collision UNIQUE si import concurrent (deux process, même région)
- Mitigation M4 : import séquentiel · un opérateur · un process
- Solution M5+ : advisory lock `pg_try_advisory_xact_lock(hashtext(region_code))` OU table `vendor_sequences(region_code, current_seq)` avec `FOR UPDATE`
- Propriétaire : CTO · à résoudre avant tout import concurrent

### Non modifié en M4

- `NOTE-ARCH-M3-001` (schéma geo normalisé)
- `DETTE-ARCH-01` (hardcodes organisationnels legacy)
- `DETTE-M1-04` (auth_helpers.py — `utcnow()` résiduel)
- `DETTE-UTC-01`, `DETTE-FIXTURE-01` (SOLDÉES M2B-PATCH)

---

## IV. RÈGLES ET PATTERNS ACTIFS

### Règles M4 — à respecter absolument

```
RÈGLE-M4-01 : vendor_id généré dans repository.insert_vendor() · jamais dans ETL DataFrame
RÈGLE-M4-02 : zone_normalized calculé par normalizer.py · jamais GENERATED COLUMN SQL
RÈGLE-M4-03 : pas de séquences SQL PostgreSQL · séquence applicative MAX()+1 (TD-001)
RÈGLE-M4-04 : ON CONFLICT (fingerprint) DO NOTHING · pas de SELECT+INSERT séparé
RÈGLE-M4-05 : activity_status et verification_source = valeurs canoniques contraintes
               pas de TEXT libre sur champ filtrable
RÈGLE-M4-06 : filtre activity_status validé côté router (422) · service suppose valeur propre
```

### Règles projet (toujours actives)

```
RÈGLE-ORG-04  : Pas de merge sans DoD vert
RÈGLE-ORG-07  : Fichier hors périmètre modifié = revert + STOP
RÈGLE-ORG-10  : Pas de migration autogenerate
RÈGLE-12      : Migrations historiques = faits non réécritibles
ADR-0003      : Pas de SQLAlchemy ORM — psycopg pur
```

### Pattern vendor insert (M4 — référence)

```python
# ON CONFLICT (fingerprint) DO NOTHING — pattern établi en M4
INSERT INTO vendor_identities (vendor_id, fingerprint, ...)
VALUES (:vid, :fp, ...)
ON CONFLICT (fingerprint) DO NOTHING

# Vérifier si insertion réussie ou doublon :
SELECT vendor_id FROM vendor_identities WHERE fingerprint = :fp LIMIT 1
# row["vendor_id"] == vendor_id → insertion OK
# row["vendor_id"] != vendor_id → doublon existant
```

### Pattern psycopg (ADR-0003 — obligatoire)

```python
# CORRECT — psycopg pur
from src.db import get_connection, db_fetchall

with get_connection() as conn:
    conn.execute("SELECT * FROM vendor_identities WHERE vendor_id = %(vid)s", {"vid": vid})
    row = conn.fetchone()  # dict ou None

# INTERDIT — pas de SQLAlchemy Session dans ce projet
from sqlalchemy.orm import Session  # INTERDIT
from src.database import get_db      # INTERDIT — src.database n'existe pas
```

---

## V. PIÈGES CONNUS ET RÉSOLUTIONS

| Piège | Contexte | Solution |
|---|---|---|
| Bamako `header=2` | Le xlsx a 2 lignes méta avant les vrais en-têtes | `pd.read_excel(f, header=2, dtype=str)` |
| PowerShell UTF-8 | `→` et `✓` → `UnicodeEncodeError cp1252` | `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')` |
| PowerShell heredoc | `cat <<'EOF'` non supporté | Écrire message dans fichier `.txt` + `git commit -F` |
| SQLAlchemy absent | Mandat indique `Session` mais ADR-0003 interdit ORM | Adapter tout en psycopg `get_connection()` |
| `src.database` absent | Mandat CTO mentionne ce module — n'existe pas | Utiliser `from src.db import get_connection` |
| `%s` vs `%(name)s` | psycopg v3 accepte les deux — préférer `%(name)s` pour la lisibilité | `conn.execute("... WHERE id = %(id)s", {"id": vid})` |
| `_ConnectionWrapper` | `fetchone()` retourne un `dict` (row_factory=dict_row) | `row["column_name"]` — pas `row[0]` |
| `generate_fingerprint` importé inutilement | ruff F401 | Supprimer l'import ou utiliser la fonction |
| Tests couche_a `_restore_schema` | Stamp alembic à la HEAD courante | Mettre à jour à chaque nouvelle migration head |

---

## VI. CONTEXTE DE REPRISE POUR L'AGENT SUCCESSEUR (M5)

### Actions CTO requises avant ouverture M5

```
1. Merger PR#142 (feat/m4-vendor-importer → main)
2. Merger PR#143 (feat/m4-patch → feat/m4-vendor-importer, ou rebaser sur main après #142)
3. Poser tag v4.1.0-m4-done sur main
4. Poser tag v4.1.0-m4-patch-done sur main
5. Confirmer que Railway a bien appliqué les migrations 042 + 043 en prod
6. Vérifier que les 102 vendors prod ont bien activity_status = VERIFIED_ACTIVE
```

### État attendu après merge CTO

```
Branche  : main
Tags     : v4.1.0-m4-done · v4.1.0-m4-patch-done
Alembic  : 043_vendor_activity_badge (1 head)
CI       : 702 passed · 0 failed
Prod     : 102 vendors VERIFIED_ACTIVE · 043 appliqué
```

### Vérifications rapides pour l'agent successeur

```powershell
# Baseline obligatoire
alembic heads
# ATTENDU : 043_vendor_activity_badge (1 head)

python -m pytest --tb=short -q | Select-Object -Last 3
# ATTENDU : 702 passed · 0 failed

# Vendors prod
python _validate_m4.py  # (si recreé — voir pattern dans HANDOVER)
# ATTENDU : BKO:50 · MPT:46 · TBK:5 · GAO:1
```

### Ce qui est stable et ne doit pas être touché

```
src/geo/                    → M3 · stable · read-only
alembic/versions/040        → migration geo · stable
alembic/versions/041        → INTOUCHABLE en prod (CTO instruction)
alembic/versions/042        → correctif tech · stable
alembic/versions/043        → badge activité · stable
src/vendors/normalizer.py   → source de vérité normalisation — ne pas dupliquer en SQL
src/vendors/region_codes.py → source de vérité ZONE_TO_REGION — compléter si nouvelles zones
```

### Ce qui reste ouvert pour M5+

```
vendor_zone_coverage         → couverture géographique par vendor (M5)
vendor_external_refs         → références externes (M5+)
TD-001 : MAX()+1 atomicité   → advisory lock ou table vendor_sequences
DETTE-ARCH-01                → hardcodes SCI dans code applicatif (avant M9)
GET /geo/zones/{id}/communes → endpoint geo reporté (quand zones chargées)
```

---

## VII. DoD M4 — RÉSULTATS FINAUX

### M4 de base (17/17)

| # | Invariant | Résultat |
|---|---|---|
| 1 | Migration `041` · SQL brut · zéro autogenerate | ✅ |
| 2 | `alembic heads` = 1 head `041_vendor_identities` | ✅ |
| 3 | Cycle downgrade/upgrade propre | ✅ |
| 4 | Garde défensive `fn_set_updated_at()` dans migration | ✅ |
| 5 | Table `vendor_identities` créée · contraintes actives | ✅ |
| 6 | Pas de `vendor_zone_coverage` · pas de `vendor_external_refs` | ✅ |
| 7 | Pas de séquences SQL PostgreSQL créées | ✅ |
| 8 | Probe B0.3 posté · header Bamako=2 validé | ✅ |
| 9 | Probe B0.5 posté · zones toutes mappées (0.0% rejet) | ✅ |
| 10 | `vendor_id` généré dans `repository.insert_vendor()` · pas dans ETL | ✅ |
| 11 | `zone_normalized` calculé par `normalizer.py` · pas GENERATED COLUMN | ✅ |
| 12 | Vendors GAO → `region_code = GAO` · jamais MPT | ✅ |
| 13 | Vendors NIAFUNKE → `region_code = TBK` · jamais MPT | ✅ |
| 14 | Taux rejet tracé · seuils 5%/15% actifs | ✅ |
| 15 | `GET /vendors` et `GET /vendors/{id}` → 200 | ✅ |
| 16 | `pytest` = 0 failed | ✅ |
| 17 | Aucun fichier hors périmètre modifié · aucun xlsx committé | ✅ |

### Patch M4 (12/12)

| # | Invariant | Résultat |
|---|---|---|
| P1 | CHECK regex `^DMS-VND-[A-Z]{3}-[0-9]{4}-[A-Z]$` actif | ✅ |
| P2 | 4 colonnes activité présentes | ✅ |
| P3 | Vendors EXCEL_M4 → `VERIFIED_ACTIVE` (en prod via 043) | ✅ |
| P4 | `ON CONFLICT DO NOTHING` — doublon retourne None | ✅ |
| P5 | `get_next_sequence` utilise regex `~` | ✅ |
| P6 | `skipped_no_region` absent de `ETLReport` | ✅ |
| P7 | `?activity_status=INVALID` → 422 | ✅ |
| P8 | Filtre `VERIFIED_ACTIVE` cohérent · valeurs canoniques seulement | ✅ |
| P9 | `TD-001` documentée dans `TECHNICAL_DEBT.md` | ✅ |
| P10 | `alembic heads` = `043_vendor_activity_badge` | ✅ |
| P11 | Trigger rebuilt proprement sans OR REPLACE | ✅ |
| P12 | `chk_activity_status` bloque les valeurs invalides | ✅ |

---

## VIII. INSTRUCTIONS POUR L'AGENT SUCCESSEUR (M5)

```
1. Lire ce fichier en entier avant toute action.
2. Lire TECHNICAL_DEBT.md — TD-001, DETTE-ARCH-01, NOTE-ARCH-M3-001.
3. Confirmer avec CTO que PR#142 et PR#143 sont mergées et tags posés.
4. Vérifier : alembic heads → 043_vendor_activity_badge (1 head).
5. Vérifier : pytest → 702 passed · 0 failed.
6. Créer la branche M5 depuis main (après merge des deux PRs).
7. NE PAS modifier src/vendors/ sans mandat explicite.
8. NE PAS modifier alembic/041 (intouchable en prod).
9. NE PAS utiliser SQLAlchemy — psycopg pur (ADR-0003).
10. Si M5 touche les zones fournisseurs :
    — vendor_zone_coverage = table à créer (migration 044 ou suivante)
    — liée à vendor_identities.vendor_id et geo_zones_operationnelles.id
    — charger les zones organisationnelles dans geo_zones_operationnelles
      AVANT de créer vendor_zone_coverage
11. TD-001 : si import concurrent prévu en M5 → implémenter advisory lock AVANT.
12. L'agent ne merge jamais. L'agent ne pose jamais les tags.
```

---

```
HANDOVER M4 — VENDOR IMPORTER MALI + PATCH
PR#142 + PR#143 — En attente merge CTO
702 tests · 0 failed · 102 vendors prod
DMS V4.1.0 · Mopti, Mali · Discipline. Vision. Ambition.
```
