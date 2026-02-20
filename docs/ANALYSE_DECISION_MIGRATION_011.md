# Analyse — Point de Décision Migration 011

**Date :** 2026-02-19  
**Contexte :** ADR-0004 §6.2 — Nommage migration 011  
**Migration concernée :** `alembic/versions/011_add_missing_schema.py`

---

## 📋 État actuel

### Migration 011

**Fichier :** `alembic/versions/011_add_missing_schema.py`  
**Revision ID :** `011_add_missing_schema`  
**Down revision :** `010_enforce_append_only_audit`  
**Statut :** ✅ Mergée sur `main` (commit `0ebfb6c`, PR #84)  
**Milestone associé :** M-SCHEMA-CORE (selon docstring ligne 7)

### Convention ADR-0003 §3.2

**Format attendu :** `NNN_<id_milestone_snake>.py`  
**Exemples :**
- `001_m_docs_core.py`
- `002_m_extraction_corrections.py`
- `005_seed_dict_procurement_sahel.py`

**Nom actuel :** `011_add_missing_schema.py`  
**Nom conforme :** `011_m_schema_core.py`

---

## 🔍 Analyse des options

### OPTION A — Renommer migration 011

**Action :**
```bash
git mv alembic/versions/011_add_missing_schema.py \
       alembic/versions/011_m_schema_core.py
```

**Modifications requises :**
1. Renommer fichier : `011_add_missing_schema.py` → `011_m_schema_core.py`
2. Modifier `revision = '011_add_missing_schema'` → `revision = '011_m_schema_core'`
3. Vérifier références dans codebase (grep `011_add_missing_schema`)
4. Vérifier chaîne Alembic : `alembic history`
5. Tester migrations : `alembic upgrade head` puis `alembic downgrade base`

**Avantages :**
- ✅ Conformité stricte ADR-0003 §3.2
- ✅ Cohérence avec autres migrations futures
- ✅ Traçabilité claire milestone → migration
- ✅ Respect principe "un milestone = une migration"

**Risques :**
- ⚠️ Migration déjà mergée sur `main` (commit `0ebfb6c`)
- ⚠️ Si migration appliquée en production → `alembic_version` contient `011_add_missing_schema`
- ⚠️ Renommer `revision` casse la chaîne si migration déjà appliquée
- ⚠️ Nécessite vérification environnement production/staging

**Impact :**
- **Si migration NON appliquée** : Renommage sans risque
- **Si migration APPLIQUÉE** : Renommage casse chaîne Alembic

---

### OPTION B — Accepter écart par exception documentée

**Action :**
- Documenter exception dans ADR-0004 §6.2
- Ajouter note dans migration : `# Exception ADR-0004: nommage non conforme par exception`
- Créer règle : migrations mergées avant ADR-0003 peuvent garder nom original

**Avantages :**
- ✅ Aucun risque de casser chaîne Alembic
- ✅ Pas de modification migration déjà mergée
- ✅ Principe "ne pas modifier migrations mergées"

**Inconvénients :**
- ❌ Non-conformité ADR-0003 §3.2
- ❌ Incohérence avec migrations futures
- ❌ Traçabilité moins claire

**Impact :**
- Migration reste fonctionnelle
- Convention non respectée pour cette migration uniquement

---

## 🎯 Recommandation : OPTION B (Exception documentée)

### Justification

1. **Migration déjà mergée sur main**
   - Commit `0ebfb6c` (2026-02-19)
   - PR #84 mergée
   - Risque de casser chaîne Alembic si renommée

2. **Principe de stabilité des migrations**
   - Les migrations mergées ne doivent pas être modifiées (ADR-0003 §2.1)
   - Modifier `revision` après merge = risque de corruption DB

3. **Exception justifiée**
   - Migration créée avant clarification ADR-0004
   - M-SCHEMA-CORE ajouté après ADR-0003 (nécessite ADR-0004)
   - Migration fonctionnelle, seul le nommage est non conforme

4. **Documentation de l'exception**
   - Documenter dans ADR-0004 §6.2
   - Ajouter commentaire dans migration
   - Créer règle : migrations mergées avant ADR-0004 peuvent garder nom original

---

## 📝 Plan d'action recommandé

### Étape 1 — Documenter exception dans ADR-0004

Ajouter section §6.2 dans ADR-0004 :

```markdown
### §6.2 — Exception nommage migration 011

**Migration :** `011_add_missing_schema.py`  
**Milestone :** M-SCHEMA-CORE  
**Statut :** Mergée sur main (commit 0ebfb6c, PR #84)

**Exception :** Migration créée avant clarification ADR-0004.
Nommage non conforme ADR-0003 §3.2 par exception documentée.

**Règle :** Migrations mergées avant ADR-0004 peuvent garder nom original.
Toutes migrations futures doivent suivre convention `NNN_m_<milestone_snake>.py`.

**Justification :** Principe de stabilité — ne pas modifier migrations mergées.
```

### Étape 2 — Ajouter commentaire dans migration

```python
# Exception ADR-0004 §6.2: nommage non conforme par exception
# Migration mergée avant clarification ADR-0004
# Toutes migrations futures doivent suivre convention ADR-0003 §3.2
revision = '011_add_missing_schema'
```

### Étape 3 — Vérifier chaîne Alembic

```bash
alembic history --verbose
alembic current
```

### Étape 4 — Documenter dans README migrations

Ajouter note dans `alembic/versions/README.md` (si existe) ou créer :

```markdown
# Conventions de nommage

Format : `NNN_m_<milestone_snake>.py`

Exception : `011_add_missing_schema.py` (voir ADR-0004 §6.2)
```

---

## ✅ Décision finale recommandée

**OPTION B — Accepter écart par exception documentée**

**Raisons :**
1. Migration déjà mergée → risque de casser chaîne Alembic
2. Principe stabilité migrations > conformité nommage
3. Exception justifiée et documentable
4. Toutes migrations futures suivront convention stricte

**Actions :**
1. Documenter exception dans ADR-0004 §6.2
2. Ajouter commentaire dans migration 011
3. Créer règle : migrations mergées avant ADR-0004 = exception autorisée
4. Vérifier chaîne Alembic fonctionne correctement

---

*© 2026 — Decision Memory System — Analyse Décision Migration 011*
