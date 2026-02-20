# Rapport ÉTAPE 2 — Tests DB-level M-EXTRACTION-ENGINE

**Date :** 2026-02-19  
**Milestone :** M-EXTRACTION-ENGINE  
**Étape :** 2/8 — Tests DB-level

---

## 🔴 INSTRUCTION 1 — BLOQUÉE

**Action :** `alembic upgrade head`

**Résultat :** ❌ **ÉCHEC**

**Erreur complète :**
```
RuntimeError: DATABASE_URL is required for Alembic migrations. 
DMS is online-only (Constitution V2.1).
```

**Cause :** Variable d'environnement `DATABASE_URL` non définie.

**Action requise :** Configurer `DATABASE_URL` avant de continuer.

**Statut :** ⛔ **STOP** — Ne pas passer à l'instruction suivante tant que DATABASE_URL n'est pas configurée.

---

## ✅ INSTRUCTIONS PRÉPARÉES (sans DB)

### INSTRUCTION 5 — Fixture db_transaction

**Statut :** ✅ **CRÉÉE**

**Fichier modifié :** `tests/conftest.py`

**Fixture ajoutée :**
```python
@pytest.fixture
def db_transaction():
    """Fixture pour tests DB-level avec rollback automatique."""
    conn = psycopg2.connect(
        dsn=os.environ["DATABASE_URL"],
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    conn.autocommit = False
    cur = conn.cursor()
    yield cur
    conn.rollback()
    cur.close()
    conn.close()
```

---

### INSTRUCTION 7 — Fichier de tests DB-level

**Statut :** ✅ **CRÉÉ**

**Fichier créé :** `tests/db_integrity/test_extraction_jobs_fsm.py`

**Contenu :**
- 5 classes de tests
- 21 tests au total
- Helpers locaux : `_insert_job()`, `_insert_processing_job()`
- Tests transitions valides (6 tests)
- Tests transitions invalides (5 tests)
- Tests horodatage automatique (4 tests)
- Tests contraintes CHECK (4 tests)
- Tests doctrine §9 (4 tests)

**Structure conforme aux instructions :**
- Classes non renommées
- Fonctions non renommées
- Structure exacte comme demandée

---

## ⏳ INSTRUCTIONS EN ATTENTE (nécessitent DB)

Les instructions suivantes nécessitent une connexion DB active :

- **INSTRUCTION 2** : `alembic current` — Nécessite DB
- **INSTRUCTION 3** : Vérifier tables en DB — Nécessite DB
- **INSTRUCTION 4** : Vérifier trigger en DB — Nécessite DB
- **INSTRUCTION 6** : Vérifier/quand document en DB — Nécessite DB
- **INSTRUCTION 8** : Exécuter tests — Nécessite DB
- **INSTRUCTION 9** : Commit et push — Nécessite tests verts

---

## 📋 FICHIERS CRÉÉS/MODIFIÉS

| Fichier | Statut | Action |
|---------|--------|--------|
| `alembic/versions/012_m_extraction_engine.py` | ✅ Créé | Migration M-EXTRACTION-ENGINE |
| `tests/conftest.py` | ✅ Modifié | Fixture `db_transaction` ajoutée |
| `tests/db_integrity/test_extraction_jobs_fsm.py` | ✅ Créé | 21 tests DB-level |

---

## 🔍 VÉRIFICATIONS PRÉLIMINAIRES

### Migration 012

**Vérifications syntaxe :**
- ✅ Syntaxe Python valide (`python -m py_compile` OK)
- ✅ Format nommage conforme : `012_m_extraction_engine.py` (ADR-0003 §3.2)
- ✅ Down revision correcte : `011_add_missing_schema`
- ✅ Type `document_id` corrigé : `TEXT` (cohérence avec `documents.id`)

**Contenu migration :**
- ✅ Table `extraction_jobs` définie
- ✅ Table `extraction_errors` définie
- ✅ Trigger `enforce_extraction_job_fsm()` défini
- ✅ Index créés
- ✅ Fonction `downgrade()` complète

### Tests DB-level

**Structure :**
- ✅ 5 classes de tests créées
- ✅ 21 tests au total
- ✅ Helpers locaux créés
- ✅ Fixture `db_transaction` référencée

**Couverture :**
- ✅ Transitions valides (6 tests)
- ✅ Transitions invalides (5 tests)
- ✅ Horodatage automatique (4 tests)
- ✅ Contraintes CHECK (4 tests)
- ✅ Doctrine §9 (4 tests)

---

## 🎯 PROCHAINES ACTIONS REQUISES

### Action immédiate — Configurer DATABASE_URL

**Option 1 — Variable d'environnement système :**
```powershell
$env:DATABASE_URL = "postgresql+psycopg://postgres:testpass@localhost:5432/dmstest"
```

**Option 2 — Fichier .env :**
```bash
DATABASE_URL=postgresql+psycopg://postgres:testpass@localhost:5432/dmstest
```

**Option 3 — PostgreSQL local requis :**
- Installer PostgreSQL si absent
- Créer base de test `dmstest`
- Configurer accès avec credentials ci-dessus

### Après configuration DATABASE_URL

1. Relancer **INSTRUCTION 1** : `alembic upgrade head`
2. Continuer séquentiellement avec INSTRUCTIONS 2-9
3. Vérifier que tous les tests passent (21/21)

---

## 📊 RAPPORT DE FIN D'ÉTAPE (PARTIEL)

```
ÉTAPE 2 — Tests DB-level
─────────────────────────
alembic current    : ⏳ EN ATTENTE (DATABASE_URL requis)
Tables créées      : ⏳ EN ATTENTE (migration non appliquée)
  extraction_jobs  : ⏳
  extraction_errors: ⏳
Trigger créé       : ⏳ EN ATTENTE
  enforce_extraction_job_fsm_trigger : ⏳
Tests créés        : ✅ 21 tests créés
Tests exécutés     : ⏳ 0 / 21 (DB requise)
Tests verts        : ⏳ 0 / 21
Tests rouges       : ⏳ N/A
Commit             : ❌ NON (tests non exécutés)
Push               : ❌ NON

PRÊT POUR ÉTAPE 3 : ❌ NON

BLOCAGE IDENTIFIÉ : DATABASE_URL non configurée
```

---

## ⚠️ BLOCAGE PRINCIPAL

**Problème :** Variable d'environnement `DATABASE_URL` non définie.

**Impact :** Impossible d'exécuter :
- Migration Alembic
- Vérifications DB
- Tests DB-level

**Solution :** Configurer `DATABASE_URL` avant de continuer.

**Fichiers préparés :**
- ✅ Migration 012 créée et vérifiée
- ✅ Tests DB-level créés (21 tests)
- ✅ Fixture `db_transaction` ajoutée

**Une fois DATABASE_URL configurée :**
- Relancer INSTRUCTION 1
- Exécuter séquentiellement INSTRUCTIONS 2-9
- Vérifier 21/21 tests verts avant ÉTAPE 3

---

*© 2026 — Decision Memory System — Rapport ÉTAPE 2 M-EXTRACTION-ENGINE*
