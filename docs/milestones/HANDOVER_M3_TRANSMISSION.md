# NOTE DE TRANSMISSION — M3 · GEO MASTER MALI

```
Date       : 2026-03-01
Milestone  : M3 — GEO MASTER MALI
Branche    : feat/m3-geo-master — MERGÉE via PR#141 → main
Statut     : DONE — tag v4.1.0-m3-done posé sur main (commit 075aac1)
Agent      : Claude Sonnet 4.6 (session 2026-03-01)
Successeur : Agent M4 (ou jalon intercalaire selon arbitrage CTO)
```

---

## I. ÉTAT DU REPO À LA TRANSMISSION

| Élément | État |
|---|---|
| Branche active | `main` (commit `075aac1`) |
| Alembic head | `040_geo_master_mali` — exactement 1 |
| CI locale post-merge | **640 passed · 36 skipped · 0 failed** |
| ruff | 0 erreur |
| black | 0 erreur |
| Tag | `v4.1.0-m3-done` — posé sur `main` + pushé origin |
| Branche feat/m3-geo-master | Mergée via PR#141 — supprimable |
| DB locale | Migration 040 appliquée · 7 tables geo créées |
| DB prod Railway | Non touchée — aucune migration posée en prod M3 |

---

## II. CE QUE M3 A LIVRÉ

### 2.1 Migration `040_geo_master_mali`

7 tables géographiques canoniques pour le Mali :

| Table | Rôle |
|---|---|
| `geo_countries` | Pays (Mali seedé, extensible) |
| `geo_regions` | 11 régions officielles Mali |
| `geo_cercles` | 8 cercles critiques Mopti seedés |
| `geo_communes` | 4 communes minimales de preuve |
| `geo_localites` | Table prête, non seedée M3 |
| `geo_zones_operationnelles` | Table prête, **non seedée M3** — agnostique |
| `geo_zone_commune_mapping` | Table prête, non seedée M3 |

Caractéristiques de la migration :
- Raw SQL uniquement (`op.execute()`) — zéro autogenerate
- `downgrade()` explicite et testable
- Colonne `organisation_code TEXT NOT NULL` — zéro DEFAULT organisationnel
- `UNIQUE(code, organisation_code)` sur zones
- Indexes sélectifs (sans doublon UNIQUE)
- Trigger `fn_set_updated_at()` sur 6 tables
- Tête alembic unique : `039 → 040`

### 2.2 Module `src/geo/`

| Fichier | Contenu |
|---|---|
| `__init__.py` | Module marker |
| `models.py` | Pydantic v2 — 7 modèles read-only |
| `repository.py` | Raw SQL read-only — 6 fonctions |
| `service.py` | Logique hiérarchique — validation déléguée au router |
| `router.py` | 6 endpoints `GET /geo/*` — lecture seule |
| `seed_mali.py` | Données Mali réelles bornées — idempotent |

### 2.3 Endpoints exposés (M3)

```
GET /geo/countries
GET /geo/countries/{iso2}/regions
GET /geo/regions/{region_id}/cercles
GET /geo/cercles/{cercle_id}/communes
GET /geo/communes/search?q=...       (422 si q < 2 chars)
GET /geo/zones
```

Hors périmètre M3 (reporté) :
```
GET /geo/zones/{zone_id}/communes    — pas d'API zombie
```

### 2.4 Tests `tests/geo/` — 66 tests

| Fichier | Tests | Couvre |
|---|---|---|
| `test_geo_migration.py` | 18 | Tables, alembic head, triggers, CHECK |
| `test_geo_hierarchy.py` | 8 | FK, traversée hiérarchique, unicité |
| `test_geo_seed_mali.py` | 30 | Seed pays/régions/cercles/communes, zones vides, idempotence |
| `test_geo_endpoints.py` | 10 | HTTP 200/404/422 sur tous les endpoints M3 |

### 2.5 Correctif intra-M3 (MANDAT CORRECTIF — appliqué)

Suite à la revue CTO, corrections appliquées **dans la même branche** avant merge :

| Correction | Action |
|---|---|
| `organisation → organisation_code` | Schéma + tests + seed |
| `DEFAULT 'SCI'` supprimé | Migration épurée |
| `UNIQUE(code, organisation_code)` ajouté | Migration |
| `SCI_ZONES_OPERATIONNELLES` supprimé | Seed épuré |
| Endpoint `zones/{id}/communes` retiré | Router + tests |
| Validation `q` unifiée côté router | Service allégé |
| Index redondant `idx_geo_communes_code_instat` supprimé | Migration |
| `NOTE-ARCH-M3-001` + `DETTE-ARCH-01` | `TECHNICAL_DEBT.md` |

---

## III. TECHNICAL_DEBT.MD — MISES À JOUR M3

### Ajouté en M3

**`NOTE-ARCH-M3-001`** — décision schéma normalisé 7 tables (agnostique, documentée).

**`DETTE-ARCH-01`** — hardcodes organisationnels legacy détectés hors périmètre M3 :

| Fichier | Nature |
|---|---|
| `alembic/versions/003_add_procurement_extensions.py` | `cat_it_sci`, `Manuel SCI` |
| `src/templates/pv_template.py` | Référence `Manuel SCI SC-PR-02` |
| `src/couche_a/routers.py` | Référence organisationnelle |
| `src/templates/cba_template.py` | Référence organisationnelle |
| `src/evaluation/profiles.py` | Hardcode profil évaluation |

Règle : migrations historiques non réécritibles. Fichiers applicatifs à corriger avant M9.
Recommandation CTO : traiter dans `DETTE-ARCH-01-M7` (milestone intercalaire M6/M7 ou intégré M7).

### Non modifié en M3

- `DETTE-M1-04` (auth_helpers.py — `utcnow()` résiduel)
- `DETTE-M2-02`, `DETTE-M2-03`
- `DETTE-FIXTURE-01`, `DETTE-UTC-01` (SOLDÉES M2B-PATCH)

---

## IV. RÈGLES ET PATTERNS ACTIFS

### Règles d'architecture geo

```
RÈGLE-GEO-01 : geo_zones_operationnelles est agnostique.
                Zéro DEFAULT organisationnel en base.
                Les organisations sont des données, pas du code.

RÈGLE-GEO-02 : Pas d'API zombie.
                On ne publie pas un endpoint qui ne peut pas prouver sa valeur.
                GET /geo/zones/{id}/communes = hors M3.

RÈGLE-GEO-03 : La validation côté router, pas côté service.
                Le service suppose une entrée déjà valide.
```

### Règles projet (inchangées)

```
RÈGLE-ORG-04  : Pas de merge sans DoD vert
RÈGLE-ORG-07  : Fichier hors périmètre modifié = revert + STOP
RÈGLE-ORG-10  : Pas de migration autogenerate
RÈGLE-12      : Migrations historiques = faits non réécritibles
```

### Pattern seed idempotent (M3)

```python
# Pattern établi en M3 — à réutiliser pour tout seed futur
INSERT INTO ... VALUES (...)
ON CONFLICT (...) DO NOTHING
RETURNING id

# Si row None (conflit → déjà existant) :
SELECT id FROM ... WHERE ...
```

---

## V. CONTEXTE DE REPRISE POUR L'AGENT SUCCESSEUR

### État courant

```
Branche          : main
Tag              : v4.1.0-m3-done
Alembic head     : 040_geo_master_mali (unique)
CI               : 640 passed · 0 failed
Prochaine tâche  : M4 (mandat à fournir par CTO)
```

### Ce qui existe et est stable

```
src/geo/          → module complet, read-only, agnostique
alembic/040       → migration stable, downgrade testé
tests/geo/        → 66 tests, couverture complète M3
```

### Ce qui est délibérément vide en M3 (à compléter en jalon futur)

```
geo_zones_operationnelles   → table prête, données organisationnelles hors M3
geo_zone_commune_mapping    → table prête, mappings hors M3
geo_localites               → table prête, données localités hors M3
GET /geo/zones/{id}/communes → endpoint à implémenter quand zones chargées
```

### Pièges connus

| Piège | Contexte | Solution |
|---|---|---|
| `psycopg` v3 vs v2 | `db_fetchone` n'existe pas | `conn.execute(sql, params); cur.fetchone()` |
| `ScopeMismatch` pytest | `geo_seed` session-scoped doit utiliser `db_conn_geo` | Fixture dédiée `db_conn_geo` en `scope="session"` dans `conftest.py` |
| `DuplicateTable` après restore | `_restore_schema` réinitialise à 036, mais 040 est appliqué | Stamp à `040_geo_master_mali` après restore |
| PowerShell heredoc | `cat <<'EOF'` non supporté | Écrire dans fichier `.txt` + `git commit -F` |
| `rg` non disponible | `rg` pas dans PATH Windows | Utiliser outil Grep intégré Cursor |

### Commandes de vérification rapide

```powershell
# Alembic
alembic heads

# CI
python -m pytest tests/geo/ --tb=short -q
python -m pytest --tb=short -q | Select-Object -Last 5

# Linting
ruff check src/geo/ tests/geo/
black --check src/geo/ tests/geo/

# Grep agnosticisme
# (utiliser outil Grep Cursor — rg non disponible sous PowerShell)
# Chercher : SCI, DEFAULT 'SCI', organisation_code, idx_geo_communes_code_instat
```

---

## VI. DoD M3 — RÉSULTATS FINAUX

| # | Invariant | Résultat |
|---|---|---|
| 1 | Migration `040_geo_master_mali` — 7 tables + indexes + triggers | ✅ |
| 2 | Seed Mali réel borné — pays, régions, cercles Mopti, communes min | ✅ |
| 3 | Module `src/geo/` — models, repository, service, router | ✅ |
| 4 | 66 tests geo — migration, hiérarchie, seed, endpoints | ✅ |
| 5 | Router `/geo` branché dans `src/api/main.py` | ✅ |
| 6 | `organisation_code` — zéro DEFAULT organisationnel | ✅ |
| 7 | `geo_zones_operationnelles` agnostique, non seedée | ✅ |
| 8 | Endpoint communes-par-zone hors périmètre (pas d'API zombie) | ✅ |
| 9 | Validation `q` unifiée côté FastAPI (422 uniquement) | ✅ |
| 10 | Index redondant supprimé | ✅ |
| 11 | `NOTE-ARCH-M3-001` + `DETTE-ARCH-01` dans `TECHNICAL_DEBT.md` | ✅ |
| 12 | `pytest` 640 passed · 0 failed | ✅ |
| 13 | `ruff` 0 erreur | ✅ |
| 14 | `black --check` 0 erreur | ✅ |
| 15 | Aucun fichier hors périmètre modifié | ✅ |
| 16 | PR#141 mergée · tag `v4.1.0-m3-done` posé | ✅ |

**DoD M3 : 16/16 vert.**

---

## VII. INSTRUCTIONS POUR L'AGENT SUCCESSEUR (M4)

```
1. Lire ce fichier en entier avant toute action.
2. Lire TECHNICAL_DEBT.md — section DETTE-ARCH-01, NOTE-ARCH-M3-001.
3. Vérifier : alembic heads → doit retourner exactement 040_geo_master_mali.
4. Vérifier : pytest --tb=short -q → doit retourner 640 passed · 0 failed.
5. Créer la branche depuis main (tag v4.1.0-m3-done).
6. NE PAS modifier src/geo/ sans mandat explicite.
7. NE PAS réécrire les migrations 003/004 (RÈGLE-12).
8. Si le mandat M4 touche les zones opérationnelles :
   — les données organisationnelles se chargent via import/flux métier
   — jamais via seed de fondation
   — la table geo_zones_operationnelles est prête, col organisation_code TEXT NOT NULL
9. DETTE-ARCH-01 : planifier avant M9, recommandation CTO = DETTE-ARCH-01-M7.
```

---

```
HANDOVER M3 — GEO MASTER MALI
v4.1.0-m3-done · 2026-03-01
Géographie. Rigueur. Neutralité.
DMS V4.1.0 · Mopti, Mali · Discipline. Vision. Ambition.
```
