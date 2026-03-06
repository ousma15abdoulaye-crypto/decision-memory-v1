# Migration Checklist (Alembic + PostgreSQL)

**Avant CHAQUE nouvelle migration:**

## 📋 1. Développement

- [ ] Migration créée: `alembic revision -m "description clear"`
- [ ] `revision` ID unique généré automatiquement
- [ ] `down_revision` pointe vers migration précédente (vérifier `alembic history`)
- [ ] Syntaxe SQL PostgreSQL stricte (PAS MySQL/SQLite)
  - [ ] Booleans: `TRUE`/`FALSE` (PAS `1`/`0`)
    - ✅ `server_default=sa.text('TRUE')` 
    - ❌ `server_default='1'`
  - [ ] Types PostgreSQL natifs:
    - ✅ `sa.UUID()` (PAS `VARCHAR(36)`)
    - ✅ `sa.JSONB()` (PAS `JSON` simple)
    - ✅ `sa.TIMESTAMP(timezone=True)` (PAS `DATETIME`)
    - ✅ `sa.Text()` (PAS `LONGTEXT`)
  - [ ] Constraints PostgreSQL:
    - ✅ `CHECK (column IN ('value1', 'value2'))`
    - ✅ `FOREIGN KEY` pointent vers tables existantes
- [ ] Foreign keys créées APRÈS les tables référencées
- [ ] Indexes noms uniques projet-wide (ex: `idx_cases_ref` pas juste `idx_ref`)
- [ ] `downgrade()` implémenté (ordre inverse de `upgrade()`)

---

## 🧪 2. Tests Locaux (OBLIGATOIRE)

### 2.1 Setup PostgreSQL Local

**⚠️ CRITIQUE:** Toujours tester sur PostgreSQL réel, jamais SQLite!

```bash
# Option 1: Docker (recommandé)
docker run -d --name dms-postgres-test \
  -e POSTGRES_USER=dms \
  -e POSTGRES_PASSWORD=dms_test \
  -e POSTGRES_DB=dms_test \
  -p 5432:5432 \
  postgres:16

export DATABASE_URL="postgresql://dms:dms_test@localhost:5432/dms_test"

# Option 2: PostgreSQL local
createdb dms_test
export DATABASE_URL="postgresql://localhost/dms_test"
```

### 2.2 Tests Migration

- [ ] **Clean migration (base → head):**
  ```bash
  alembic downgrade base
  alembic upgrade head
  echo $?  # Doit retourner 0
  ```

- [ ] **Vérification schéma:**
  ```bash
  psql $DATABASE_URL -c "\dt"  # Lister tables
  psql $DATABASE_URL -c "\d <table>"  # Structure table modifiée
  ```

- [ ] **Test downgrade:**
  ```bash
  alembic downgrade -1
  # Vérifier que table/colonne supprimée correctement
  psql $DATABASE_URL -c "\d <table>"
  ```

- [ ] **Test re-upgrade (idempotence):**
  ```bash
  alembic upgrade head
  echo $?  # Doit retourner 0 sans erreur
  ```

- [ ] **Vérifier données seed (si applicable):**
  ```bash
  psql $DATABASE_URL -c "SELECT * FROM <table> LIMIT 5;"
  ```

### 2.3 Tests Unitaires

- [ ] **Tests migrations existants:**
  ```bash
  pytest tests/migrations/test_chain.py -v
  ```

- [ ] **Ajouter test spécifique nouvelle migration** (optionnel mais recommandé)

---

## 📝 3. Documentation

- [ ] **Docstring migration:**
  ```python
  """Add procurement extended features.
  
  Tables créées:
  - procurement_references: Références uniques DAO/RFQ/RFP
  - procurement_categories: Catégories achats (6 types)
  
  Tables modifiées:
  - cases: Ajout colonnes ref_id, category_id, estimated_value
  
  Révision: 003_add_procurement_extensions
  Revises: 002_add_couche_a
  """
  ```

- [ ] **Commentaires inline SQL complexe:**
  ```python
  # Contrainte: procedure_type doit être une valeur valide du Manuel SCI
  op.execute("""
      ALTER TABLE cases ADD CONSTRAINT check_procedure_type 
      CHECK (procedure_type IN ('devis_unique', 'devis_simple', ...))
  """)
  ```

- [ ] **Update `docs/architecture/database-schema.md`** (si changements majeurs)

- [ ] **Update CHANGELOG.md:**
  ```markdown
  ## [Unreleased]
  ### Added
  - Migration 003: Procurement extended (références, catégories, seuils)
  ```

---

## 🔍 4. Review Code

- [ ] **Linter Python:**
  ```bash
  python -m py_compile alembic/versions/<migration_file>.py
  ```

- [ ] **Vérifier chaîne révisions:**
  ```bash
  alembic history
  # Doit afficher: ... → <down_revision> → <nouvelle_migration> → ...
  ```

- [ ] **Pas de fichiers hors `alembic/versions/`:**
  ```bash
  find . -name "*<migration_prefix>*" -type f | grep -v "alembic/versions"
  # Ne doit rien retourner
  ```

- [ ] **Review SQL par senior dev** (si migration complexe)

---

## 🚀 5. CI/CD

- [ ] **Push branche feature:**
  ```bash
  git add alembic/versions/<migration_file>.py
  git commit -m "feat(migration): add <description>"
  git push origin <feature-branch>
  ```

- [ ] **CI verte avant merge:**
  - PostgreSQL service healthy ✓
  - `alembic upgrade head` success ✓
  - Tests pytest passent ✓
  - Aucune erreur SQL ✓

- [ ] **Review migration par senior dev/DBA**

- [ ] **Squash commits atomiques** (1 migration = 1 commit clean)

---

## 🏭 6. Production (Post-Merge)

### 6.1 Pré-Déploiement

- [ ] **Backup base AVANT migration:**
  ```bash
  pg_dump -h <host> -U <user> <db> > backup_pre_migration_$(date +%Y%m%d).sql
  ```

- [ ] **Maintenance window planifiée** (si downtime attendu)

- [ ] **Rollback plan documenté:**
  ```bash
  # Si migration échoue:
  alembic downgrade -1
  # Restaurer backup si nécessaire
  ```

### 6.2 Exécution Production

- [ ] **Dry-run staging:**
  ```bash
  # Sur base staging identique prod
  alembic upgrade head
  # Vérifier résultat, perf, données
  ```

- [ ] **Migration production:**
  ```bash
  alembic upgrade head
  ```

- [ ] **Vérifications post-migration:**
  ```bash
  psql $DATABASE_URL -c "\dt"  # Tables créées OK
  psql $DATABASE_URL -c "\d <table>"  # Structure OK
  psql $DATABASE_URL -c "SELECT COUNT(*) FROM <table>;"  # Données OK
  ```

### 6.3 Monitoring Post-Migration

- [ ] **Logs application (24h):**
  - Aucune erreur SQL
  - Performances normales
  - Aucune régression fonctionnelle

- [ ] **Metrics base de données:**
  - Query time OK
  - Index utilisés correctement
  - Pas de table locks prolongés

- [ ] **Rollback si problème critique** (et analyse post-mortem)

---

## 🔧 7. Outils Helper

### Script Validation Migration

**Créer:** `scripts/validate_migration.sh`
```bash
#!/bin/bash
# Valide migration avant commit

MIGRATION_FILE=$1

if [ -z "$MIGRATION_FILE" ]; then
    echo "Usage: $0 <migration_file.py>"
    exit 1
fi

echo "🔍 Validation migration: $MIGRATION_FILE"

# 1. Syntaxe Python
echo "1. Syntaxe Python..."
python -m py_compile "$MIGRATION_FILE" || exit 1

# 2. Détection erreurs communes PostgreSQL
echo "2. Vérification syntaxe PostgreSQL..."
if grep -E "server_default=['\"](0|1)['\"]" "$MIGRATION_FILE"; then
    echo "❌ ERREUR: Utiliser sa.text('TRUE')/sa.text('FALSE') pour server_default"
    exit 1
fi

if grep -E ",\s*[01]\s*," "$MIGRATION_FILE" | grep -q "Boolean"; then
    echo "❌ ERREUR: Utiliser TRUE/FALSE dans INSERT, pas 0/1"
    exit 1
fi

# 3. Chaîne révisions
echo "3. Chaîne révisions..."
alembic history | tail -5

echo "✅ Validation OK"
```

### Hook Pre-Commit

**Créer:** `.git/hooks/pre-commit`
```bash
#!/bin/bash
for file in $(git diff --cached --name-only | grep "alembic/versions/.*\.py"); do
    ./scripts/validate_migration.sh "$file" || exit 1
done
```

---

## 📚 Ressources

- **PostgreSQL Types:** https://www.postgresql.org/docs/16/datatype.html
- **Alembic Tutorial:** https://alembic.sqlalchemy.org/en/latest/tutorial.html
- **SQLAlchemy Types:** https://docs.sqlalchemy.org/en/20/core/types.html
- **DMS Constitution V2.1:** `docs/constitution_v2.1.md` (§1.4 Database PostgreSQL 16)

---

## ⚠️ Erreurs Fréquentes à Éviter

| Erreur | ❌ Incorrect | ✅ Correct |
|--------|-------------|-----------|
| **Boolean default** | `server_default='1'` | `server_default=sa.text('TRUE')` |
| **Boolean INSERT** | `VALUES (..., 1, ...)` | `VALUES (..., TRUE, ...)` |
| **UUID type** | `sa.String(36)` | `sa.UUID()` |
| **JSON type** | `sa.JSON()` | `sa.JSONB()` (plus performant) |
| **Timestamp** | `sa.DateTime()` | `sa.TIMESTAMP(timezone=True)` |
| **Text long** | `sa.String(10000)` | `sa.Text()` |
| **FK avant table** | `CREATE FK puis CREATE TABLE` | `CREATE TABLE puis CREATE FK` |
| **Index nom générique** | `idx_ref` | `idx_cases_ref` (unique projet) |

---

## ✅ Checklist Résumée

**Avant commit:**
- [ ] Tests locaux PostgreSQL ✓
- [ ] Syntaxe PostgreSQL stricte ✓
- [ ] Chaîne révisions OK ✓
- [ ] Downgrade implémenté ✓
- [ ] Documentation ✓

**Avant merge:**
- [ ] CI verte ✓
- [ ] Review senior dev ✓
- [ ] CHANGELOG updated ✓

**Avant production:**
- [ ] Backup base ✓
- [ ] Dry-run staging ✓
- [ ] Rollback plan ✓

---

---

## ⚠️ 8. Spécificités Chaîne Post-M4 (OBLIGATOIRE — lire avant 04X+)

### Règles absolues post-M4

```text
1. alembic heads → 1 seul résultat avant de commencer
2. down_revision = copié depuis output alembic heads · jamais supposé
3. IDs 044 et 045 réservés freeze V4.1.0 · M11 et M14 uniquement
4. Migrations patch post-freeze = noms explicites (m5_pre_* · m4_patch_*)
5. Noms contraintes/index = issus du probe SQL · jamais inventés
6. Après chaque migration : alembic heads → vérifier 1 seul résultat
```

### Chaîne Alembic post-M4 — état 2026-03-03

```
041_vendor_identities
  → 042_vendor_fixes
  → 043_vendor_activity_badge
  → m4_patch_a_vendor_structure_v410   ← hors séquence · DÉPLOYÉ PROD
  → m4_patch_a_fix                     ← hors séquence · DÉPLOYÉ PROD
  → m5_pre_vendors_consolidation
  → m6_dictionary_build
  → m7_2_taxonomy_reset
  → m7_3_dict_nerve_center             ← HEAD · M7.3 DICT NERVE CENTER
```

### Migrations hors convention numérique (INTOUCHABLES)

```text
m4_patch_a_vendor_structure_v410 · down_revision = 043_vendor_activity_badge
m4_patch_a_fix                   · down_revision = m4_patch_a_vendor_structure_v410
m5_pre_vendors_consolidation     · down_revision = m4_patch_a_fix
```

Ces fichiers sont **intouchables** (renommage interdit — migrations déployées).

### État consolidation vendors — 2026-03-03 · VERDICT A appliqué

```text
alembic heads         → m7_3_dict_nerve_center (1 seul head ✓)
vendors               → ex vendor_identities · 34 colonnes · 0 lignes local · 661 prod
vendor_identities     → SUPPRIMÉE (consolidation appliquée)
vendors legacy        → SUPPRIMÉE (était vide · TD-004 FERMÉE)
market_signals.vendor_id → FK existante vers vendors(id) supprimée explicitement
  créée par    : 005_add_couche_b.py (market_signals_vendor_id_fkey)
  supprimée par: m5_pre_vendors_consolidation (upgrade · ALTER TABLE market_signals DROP CONSTRAINT)
  non restaurée: m5_pre_vendors_consolidation (downgrade · partiel · documenté)
  rollback complet : backup Railway requis
```

### Prochain slot migration valide

```text
Révision      : m6_[description] (ou nom explicite)
down_revision : m5_fix_market_signals_vendor_type
Condition     : exécuter alembic heads immédiatement avant de coder le fichier
```

---

## 9. Doctrine seed data — RÈGLE ABSOLUE POST-M5-PRE

### Problème identifié (Sprint M5-PRE · Piège-02)

`005_add_couche_b.py` a inséré des données via `INSERT` dans la migration.
Conséquence : les fixtures pytest appliquent ce seed à chaque `alembic upgrade`.
La DB locale diverge silencieusement de prod.
Les gardes `COUNT > 0` explosent en CI.

Symptôme observé :
```text
psycopg.errors.RaiseException: vendors legacy contient 2 ligne(s) — DROP refusé
```

### Règle

```text
INTERDIT dans alembic/versions/*.py :
  INSERT INTO ... VALUES ...
  UPDATE ...
  DELETE ...

AUTORISÉ dans alembic/versions/*.py :
  DDL uniquement : CREATE · ALTER · DROP · INDEX · TRIGGER

OBLIGATOIRE pour les seed data :
  scripts/seed_*.py dédiés · exécution manuelle documentée
  Jamais automatique dans les migrations
```

### Vérification avant merge

```bash
grep -n "INSERT INTO\|UPDATE \|DELETE FROM" \
  alembic/versions/<nouvelle_migration>.py
# Résultat attendu : 0 occurrence
# Les blocs DO $$ de garde (RAISE EXCEPTION/NOTICE) sont exemptés
```

---

**Dernière mise à jour:** 2026-03-03
**Auteur:** Agent DMS · VERDICT A CTO (Abdoulaye Ousmane)
**Version:** 1.3 (Post-M5-FIX · vendor_id UUID · doctrine seed data)
