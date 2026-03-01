# NOTE DE TRANSMISSION — PROD-HOTFIX-001 · ALEMBIC OVERLAP RAILWAY

```
Date       : 2026-03-01
Milestone  : PROD-HOTFIX-001 (intra-M3, post-tag)
Nature     : Hotfix production — crash loop Railway post-déploiement M3
Branche    : main — commits directs (pas de feature branch)
Statut     : RÉSOLU — prod verte — uvicorn running on 0.0.0.0:8080
Agent      : Claude Sonnet 4.6 (session 2026-03-01)
Successeur : Agent M4
```

---

## I. ÉTAT DU REPO À LA TRANSMISSION

| Élément | État |
|---|---|
| Branche active | `main` (commit `163b085`) |
| Alembic head | `040_geo_master_mali` — exactement 1 |
| DB prod `alembic_version` | `040_geo_master_mali` — 1 seule ligne ✅ |
| CI locale | **640 passed · 36 skipped · 0 failed** |
| ruff | 0 erreur |
| black | 0 erreur |
| Tag | `v4.1.0-m3-done` (inchangé — hotfix ne reçoit pas de tag) |
| Prod Railway | **VERTE** — `uvicorn` running — crash loop terminée |
| Tables geo_* prod | 8 présentes (7 M3 + `geo_master` orpheline legacy) |

---

## II. CHRONOLOGIE DU HOTFIX

### Symptôme initial

```
Erreur prod post-déploiement M3 :
"Requested revision 040_geo_master_mali overlaps
 with other requested revisions 039_created_at_timestamptz"
→ crash loop Railway · restart infini
```

### Cause racine reconstituée (chaîne complète)

```
ÉTAPE 1 — M2B (déploiement antérieur à M3)
  Migration 039_created_at_timestamptz appliquée en prod
  MAIS stockée avec slug court "039" dans alembic_version
  (au lieu de "039_created_at_timestamptz")
  → Cause : version Alembic ou config prod différente au moment du déploiement M2B

ÉTAPE 2 — M3 déployé (PR#141 mergé → main)
  alembic upgrade head résout "039" → "039_created_at_timestamptz" (partial match ✓)
  → applique migration 040 → 7 tables geo créées ✓
  → INSERT "040_geo_master_mali" dans alembic_version ✓
  → DELETE WHERE version_num = "039_created_at_timestamptz" ✗ ÉCHEC
    (la valeur réelle est "039", pas "039_created_at_timestamptz" → pas de match)
  → RÉSULTAT : alembic_version = {"039", "040_geo_master_mali"} — 2 lignes

ÉTAPE 3 — Crash loop "overlaps"
  Chaque restart : alembic upgrade head lit 2 révisions simultanées
  → 040 dépend de 039 → overlap logique → exception → crash → restart

ÉTAPE 4 — HOTFIX ACTE 1 : DELETE "039"
  DELETE FROM alembic_version WHERE version_num = '039'
  → alembic_version = {"040_geo_master_mali"} — 1 ligne ✓
  Mais Railway servait un container buildé AVANT M3 (cache Nixpacks / rollback auto)
  → container sans 040_geo_master_mali.py
  → nouvelle erreur : "Can't locate revision identified by '040_geo_master_mali'"

ÉTAPE 5 — HOTFIX ACTE 2 : Force rebuild
  Modification de 040_geo_master_mali.py :
    CREATE TABLE → CREATE TABLE IF NOT EXISTS (7 tables)
    CREATE INDEX → CREATE INDEX IF NOT EXISTS (6 indexes)
    CREATE TRIGGER → CREATE OR REPLACE TRIGGER (6 triggers)
  Push commit 163b085 → Railway déclenche nouveau build Nixpacks depuis zéro
  → container propre avec 040_geo_master_mali.py ✓
  → alembic upgrade head → "Already up to date" → uvicorn démarre ✓
```

---

## III. MODIFICATIONS APPORTÉES EN HOTFIX

### Seul fichier modifié : `alembic/versions/040_geo_master_mali.py`

| Changement | Avant | Après |
|---|---|---|
| CREATE TABLE (×7) | `CREATE TABLE` | `CREATE TABLE IF NOT EXISTS` |
| CREATE INDEX (×6) | `CREATE INDEX` | `CREATE INDEX IF NOT EXISTS` |
| CREATE TRIGGER (×6) | `CREATE TRIGGER` | `CREATE OR REPLACE TRIGGER` |
| Docstring | scope M3 seulement | + mention hotfix PROD-HOTFIX-001 |

**Aucun autre fichier modifié.** Périmètre respecté.

### Commits sur main post-tag v4.1.0-m3-done

| Commit | Nature |
|---|---|
| `55c29fa` | docs(m3): handover M3 |
| `163b085` | fix(deploy): migration 040 idempotente — hotfix Railway |

---

## IV. ÉTAT PROD CONFIRMÉ À LA CLÔTURE

```bash
# alembic_version prod (vérifié via psycopg)
SELECT version_num FROM alembic_version;
→ 040_geo_master_mali   (1 seule ligne)

# Tables geo présentes en prod
→ geo_cercles, geo_communes, geo_countries, geo_localites,
  geo_master (orpheline legacy — voir §V),
  geo_regions, geo_zone_commune_mapping, geo_zones_operationnelles
  (8 tables)

# Logs Railway (dernier démarrage propre)
[start.sh] Running alembic upgrade head...
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

---

## V. POINTS D'ATTENTION POUR L'AGENT SUCCESSEUR (M4)

### 5.1 Table `geo_master` orpheline en prod

```
La table geo_master existe en prod (confirmé probe HOTFIX).
Elle N'EST PAS dans la migration 040_geo_master_mali.py.
Elle N'EST PAS dans les tests.
Elle est probablement une relique d'un test ou proto antérieur à M3.

Règle : NE PAS la modifier · NE PAS la dropper sans décision CTO explicite.
Si M4 touche le schéma geo, noter sa présence dans le probe initial.
```

### 5.2 Slug court "039" — legacy prod

```
La migration 039_created_at_timestamptz a été stockée avec slug "039"
dans alembic_version lors de son déploiement prod (M2B).
Ce slug court a été SUPPRIMÉ par le hotfix (DELETE).
alembic_version pointe maintenant sur "040_geo_master_mali" — correct.

MAIS : si jamais une future opération de downgrade est envisagée
(downgrade -1 depuis prod), Alembic essaiera de réinstaller "039_created_at_timestamptz"
dans alembic_version. Le downgrade devrait fonctionner normalement
car c'est la migration file qui écrit dans alembic_version, pas un opérateur humain.
→ À tester en local AVANT tout downgrade prod.
```

### 5.3 Migration 040 est maintenant idempotente

```
CREATE TABLE IF NOT EXISTS → rejouer la migration 040 ne crashe pas.
CREATE INDEX IF NOT EXISTS → idem.
CREATE OR REPLACE TRIGGER  → idem.

C'est un comportement VOULU post-hotfix.
Ne pas "corriger" en retirant le IF NOT EXISTS.
```

### 5.4 Alembic_version et slugs courts — règle à poser pour M4+

```
Tout futur déploiement Railway doit vérifier AVANT push :
  alembic heads → doit retourner 1 seule ligne avec slug complet

Si slug court détecté dans alembic_version prod :
  UPDATE alembic_version SET version_num = '<slug_complet>'
  WHERE version_num = '<slug_court>'
  → avant toute nouvelle migration
```

---

## VI. DETTE TECHNIQUE CRÉÉE PAR LE HOTFIX

Aucune nouvelle dette technique créée. Le hotfix est chirurgical et ciblé.

La `DETTE-ARCH-01` (hardcodes organisationnels legacy) reste active — non touchée par ce hotfix.

---

## VII. INSTRUCTIONS POUR L'AGENT SUCCESSEUR (M4)

```
1. Lire HANDOVER_M3_TRANSMISSION.md + ce fichier en entier.
2. Probe initial obligatoire :
     alembic heads                  → doit retourner exactement 040_geo_master_mali
     pytest --tb=short -q           → doit retourner 640 passed · 0 failed
     SELECT version_num FROM alembic_version (prod, si accès disponible)
                                    → doit retourner 040_geo_master_mali
3. Vérifier la table geo_master en prod — documenter sa présence dans le probe M4.
4. NE PAS toucher alembic/versions/040_geo_master_mali.py sans mandat explicite.
5. NE PAS dropper geo_master sans décision CTO.
6. La prod est verte — ne rien faire qui pourrait déclencher un restart Railway
   sauf push délibéré d'un commit M4 validé.
7. Attendre le mandat M4 du CTO avant toute action.
```

---

## VIII. DoD HOTFIX-001 — RÉSULTATS FINAUX

| # | Invariant | Résultat |
|---|---|---|
| 1 | Cause identifiée (CAS C + CAUSE D) | ✅ |
| 2 | `alembic heads` local = 1 head | ✅ |
| 3 | Chaîne historique linéaire `040 → 039 → ...` | ✅ |
| 4 | Cycle downgrade/upgrade local propre | ✅ |
| 5 | `pytest` = 640 passed · 0 failed | ✅ |
| 6 | Uniquement `040_geo_master_mali.py` modifié | ✅ |
| 7 | Logs Railway : absence de FAILED et ERROR | ✅ |
| 8 | Logs Railway : démarrage propre confirmé | ✅ |
| 9 | Application Railway running · crash loop terminée | ✅ |
| 10 | Aucun fichier hors périmètre modifié | ✅ |

**DoD : 10/10 vert.**

---

```
HANDOVER PROD-HOTFIX-001
v4.1.0-m3-done + hotfix · 2026-03-01
La prod est stable. La dette est documentée. M4 peut ouvrir.

DMS V4.1.0 · Mopti, Mali · Discipline. Vision. Ambition.
```
