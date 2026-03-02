# ADR-M5-PRE-001 — Hardening Pré-M5 : Résolution Failles Architecture

## Statut
ACCEPTÉ

## Date
2026-03-02

## Auteur
Agent Claude Sonnet 4.6 — auto-évaluation pré-M5 · validé CTO

---

## Contexte

Audit technique réalisé à la clôture du sprint M4/PATCH-A/PATCH-B (v4.1.0).
9 failles identifiées, classées en 2 catégories :

**Bloquantes M5** (déploiement Railway risqué sans correction) :
- F7 : Chaîne Alembic sans numéros séquentiels — risque double head
- F8 : Table `vendors` legacy hors Alembic — risque crash RENAME (TD-004)

**Non bloquantes M5 mais critiques enterprise-grade** :
- F1 : `DATABASE_URL` évalué au chargement du module (couplage startup/runtime)
- F3 : `SELECT *` exposé en API (colonnes sensibles NIF/RIB/RCCM automatiquement exposées)
- F4 : Absence de connection pooling (saturation Railway à charge >10 req/s)
- F5 : `ImportError` avalés en silence dans `main.py` (12 blocs try/except)

**Mineures** :
- F2 : Race condition vendor_id — déjà documentée TD-001, mitigation M4 suffisante
- F6 : Service layer vendor vide — acceptable jusqu'à logique M5
- F9 : Codes `KLK`/`INT` non documentés dans `ALL_REGION_CODES`

---

## Décision

### PHASE 0 — PRÉ-M5 OBLIGATOIRE · avant premier commit M5

#### D0.1 · Alembic chain integrity (F7 · TD-009)

**Problème :** `m4_patch_a_vendor_structure_v410` et `m4_patch_a_fix` n'ont pas
de numéro séquentiel. La prochaine migration `044_` doit déclarer
`down_revision = "m4_patch_a_fix"` explicitement, sinon double head.

**Décision :**
- Ne PAS renommer les fichiers existants (migrations déployées en prod — règle absolue).
- Créer `alembic/versions/044_consolidate_vendors.py` avec
  `down_revision = "m4_patch_a_fix"` (nom exact du fichier).
- Documenter dans `docs/dev/migration-checklist.md` que la chaîne
  contient deux fichiers hors convention et que tout `04X_` doit vérifier
  `alembic heads` avant push.

**Critère de validation :**
```bash
alembic heads
# ATTENDU : 1 seul résultat = révision de 044
```

#### D0.2 · Migration 044_consolidate_vendors (F8 · TD-004)

**Problème :** Table `vendors` (4 colonnes, 10 lignes tests, hors Alembic) bloque
le renommage `vendor_identities → vendors`.

**Décision :**
1. Créer `alembic/versions/044_consolidate_vendors.py`
2. `down_revision = "m4_patch_a_fix"` (head actuel)
3. Contenu upgrade :
   ```sql
   -- Garde obligatoire
   SELECT COUNT(*) FROM market_signals WHERE vendor_id IS NOT NULL;
   -- Si > 0 → lever exception (ne jamais silencieusement DROP)

   DROP TABLE IF EXISTS vendors CASCADE;
   ALTER TABLE vendor_identities RENAME TO vendors;
   ALTER INDEX idx_vi_canonical_trgm         RENAME TO idx_vendors_canonical_trgm;
   ALTER INDEX vendor_identities_pkey        RENAME TO vendors_pkey;
   ALTER TABLE vendors RENAME CONSTRAINT
     vendor_identities_fingerprint_key       TO vendors_fingerprint_key;
   ALTER TABLE vendors RENAME CONSTRAINT
     vendor_identities_vendor_id_key         TO vendors_vendor_id_key;
   ALTER TABLE vendors RENAME CONSTRAINT
     vendor_identities_vcrn_key              TO vendors_vcrn_key;
   ALTER TABLE vendors RENAME CONSTRAINT
     uq_vi_canonical_name                    TO uq_vendors_canonical_name;
   ```
4. Contenu downgrade : `RENAME TO vendor_identities` (inverse complet).
5. Après migration : grep et remplacer tous les `vendor_identities` dans `src/`.
6. Tests : mettre à jour les références dans `tests/vendors/`.

**Critère de validation :**
```bash
alembic upgrade head
python -m ruff check src tests
python -m black --check src tests
pytest --tb=short -q
# ATTENDU : 0 failed · 0 erreurs ruff/black
```

---

### PHASE 1 — M5 SCOPE · pendant le sprint M5

#### D1.1 · Lazy init DATABASE_URL (F1 · TD-005)

**Problème :** `_DATABASE_URL = _get_database_url()` à la ligne 42 de `src/db/core.py`
s'exécute à l'import du module. Tout environnement sans `DATABASE_URL`
(build CI sans DB, tests unitaires purs) plante à l'import.

**Décision :**
- Remplacer le module-level `_DATABASE_URL = _get_database_url()` par
  une fonction `_get_or_init_db_url()` avec un cache local `_DB_URL_CACHE`.
- L'évaluation se fait au premier appel `get_connection()` ou `_get_raw_connection()`.
- `_sql_to_psycopg_style` et `_normalize_url` restent purs, sans effet de bord.

**Implémentation :**
```python
_DB_URL_CACHE: str | None = None

def _get_or_init_db_url() -> str:
    global _DB_URL_CACHE
    if _DB_URL_CACHE is None:
        _DB_URL_CACHE = _get_database_url()
    return _DB_URL_CACHE
```
Appeler `_get_or_init_db_url()` dans `_get_raw_connection()` à la place de `_DATABASE_URL`.

**Critère de validation :**
```python
# Test : l'import du module ne lève pas d'exception sans DATABASE_URL
import importlib, os
env_bak = os.environ.pop("DATABASE_URL", None)
import src.db.core  # ne doit pas crasher
os.environ["DATABASE_URL"] = env_bak or ""
```

#### D1.2 · SELECT * → colonnes explicites (F3 · TD-006)

**Problème :** `SELECT * FROM vendor_identities` dans `repository.py` expose
automatiquement toute nouvelle colonne via l'API `/vendors`, y compris
`nif`, `rib`, `rccm`, `verified_by`, `verification_source` — données
fournisseurs sensibles.

**Décision :**
- Définir une constante `_PUBLIC_COLUMNS` dans `repository.py` listant
  les colonnes safe pour exposition API.
- `list_vendors` et `get_vendor_by_id` utilisent cette constante.
- Colonnes exclues par défaut : `nif`, `rccm`, `rib`, `verified_by`,
  `verification_source`, `suspension_reason`.
- Un endpoint `/vendors/{id}/details` (scope admin, M6+) pourra exposer
  les colonnes complètes avec contrôle RBAC.

**Critère de validation :**
```python
# Test : réponse API ne contient pas les colonnes sensibles
assert "nif" not in response.json()[0]
assert "rib" not in response.json()[0]
```

#### D1.3 · Fail-loud au démarrage (F5 · TD-008)

**Problème :** `main.py` contient 12 blocs `try/except ImportError: pass`.
Un bug réel (circular import, `NameError`, dépendance manquante) est
silencieusement avalé. Un router peut disparaître en production sans alerte.

**Décision :**
- Les routers **obligatoires** (auth, cases, health) : import direct, sans try/except.
- Les routers **optionnels** (milestones futurs) : conserver le try/except **mais**
  logger en WARNING avec le nom du module et l'erreur.
- Ajouter un `startup_check()` appelé dans `@app.on_event("startup")` qui
  liste les routers actifs et logue leur statut.

**Critère de validation :**
```bash
# Simuler un ImportError volontaire dans un router
# ATTENDU : WARNING dans les logs, pas de silence total
```

---

### PHASE 2 — M6+ · décision CTO requise

#### D2.1 · Connection pooling (F4 · TD-007)

**Problème :** Chaque `get_connection()` ouvre et ferme une connexion psycopg raw.
Sous charge HTTP concurrente, Railway PostgreSQL atteint son `max_connections`
(Railway Starter = 25 par défaut).

**Décision :**
- Adopter `psycopg_pool.ConnectionPool` (synchrone, compatible ADR-0003).
- Pool size : `min_size=2, max_size=10` — ajustable selon Railway plan.
- Instance singleton initialisée au démarrage FastAPI (`@app.on_event("startup")`).
- `get_connection()` devient `pool.connection()` plutôt qu'une nouvelle connexion.
- **INTOUCHABLE** : l'interface `_ConnectionWrapper` reste identique — aucune
  modification aux callers.

**Prérequis :** `psycopg[pool]` dans `requirements.txt`.

**Critère de validation :**
```bash
# Test de charge : 50 req/s · 0 psycopg OperationalError "too many connections"
```

#### D2.2 · vendor_id atomique (F2 · TD-001)

Voir TD-001 existant dans `TECHNICAL_DEBT.md`.
Décision : Option B — table `vendor_sequences(region_code PK, current_seq INT)`
avec `SELECT FOR UPDATE` avant INSERT.
Périmètre : M5+ si import concurrent ou écriture API activée.

---

### PHASE 3 — HOUSEKEEPING · au fil de l'eau

#### D3.1 · Service layer vendor (F6)

Conserver `service.py` vide jusqu'à M5. En M5, y déplacer :
- validation métier (ex: vérifier qu'un `region_code` est cohérent avec la zone)
- orchestration multi-repository (ex: enrichissement geo depuis `geo_regions`)

#### D3.2 · Codes KLK/INT (F9)

`KLK` (Kidal) et `INT` (International) sont des codes-région futurs
réservés, non encore mappés dans `ZONE_TO_REGION`.
Action : ajouter commentaire dans `region_codes.py` pour chaque code
indiquant son statut "RÉSERVÉ — aucune zone mappée en M4".

---

## Périmètre des fichiers touchés par phase

```
PHASE 0 :
  alembic/versions/044_consolidate_vendors.py    CRÉER
  src/vendors/repository.py                      vendor_identities → vendors
  src/vendors/router.py                          vendor_identities → vendors (docstrings)
  src/vendors/service.py                         idem
  tests/vendors/                                 références table renommée
  docs/dev/migration-checklist.md                note chaîne hors convention

PHASE 1 :
  src/db/core.py                                 lazy init DATABASE_URL
  src/vendors/repository.py                      SELECT * → _PUBLIC_COLUMNS
  src/api/main.py                                fail-loud + startup_check()

PHASE 2 :
  src/db/core.py                                 ConnectionPool
  requirements.txt                               psycopg[pool]
  src/vendors/repository.py                      vendor_sequences SELECT FOR UPDATE

PHASE 3 :
  src/vendors/region_codes.py                    commentaires KLK/INT
```

---

## Exclusions définitives

```
- Ne PAS modifier alembic/041, 042, 043, m4_patch_a_vendor_structure_v410, m4_patch_a_fix
- Ne PAS introduire SQLAlchemy (ADR-0003)
- Ne PAS créer de GENERATED COLUMN PostgreSQL
- Ne PAS changer l'interface _ConnectionWrapper (callers inchangés)
- Ne PAS ajouter de codes région sans validation CTO
```

---

## Plan de rollback

**PHASE 0 — migration 044 :**
```bash
alembic downgrade -1
# Inverse : RENAME vendors → vendor_identities · restaure vendors legacy
# Requiert que vendors legacy n'ait pas été accidentellement modifiée
```

**PHASE 1 — lazy init :**
Non destructif — rollback = revert git du fichier `core.py`.

**PHASE 2 — connection pool :**
Non destructif — rollback = revert `core.py` + retrait `psycopg[pool]`.

---

## Registre des dettes associées

| Ref      | Statut dans TECHNICAL_DEBT.md | Phase résolution |
|----------|-------------------------------|-----------------|
| TD-001   | ACTIVE · existant             | Phase 2 (D2.2)  |
| TD-004   | ACTIVE · bloquant M5          | Phase 0 (D0.2)  |
| TD-005   | ACTIF · planifié              | Phase 1 (D1.1)  |
| TD-006   | ACTIF · planifié              | Phase 1 (D1.2)  |
| TD-007   | ACTIF · planifié              | Phase 2 (D2.1)  |
| TD-008   | ACTIF · planifié              | Phase 1 (D1.3)  |
| TD-009   | ACTIF · bloquant M5           | Phase 0 (D0.1)  |

---

## Conséquences

- Système stable pour M5+ avec `vendor_identities` → `vendors` renommé
- Chaîne Alembic propre · `alembic heads` retourne toujours 1 résultat
- Aucune fuite de données sensibles NIF/RIB/RCCM via API publique
- Démarrage explicite : un router manquant est visible dans les logs
- Connection pool évite la saturation Railway à charge réelle
- vendor_id non atomique reste mitigation-suffisante jusqu'à import concurrent

---

## Auteur
CTO DMS V4.1.0 — 2026-03-02
Agent : Claude Sonnet 4.6 — sprint M4/PATCH clôturé
