# P3.2 ÉTAPE 1 — PROBE SCHÉMA (résultats probe Railway)

**Date** : 2026-04-18  
**Environnement** : Railway prod (sci_mali)  
**Statut** : ✅ **PROBE TERMINÉ** — findings ci-dessous

---

## RÉSUMÉ EXÉCUTIF

**Colonne `is_active`** : ⚠️ **ABSENTE** — doit être créée par migration avant soft-delete

**Tables CTO** : 3/7 MISSING (noms incorrects ou legacy)

**Tables workspace_id réelles** : 28 tables trouvées

**Foreign keys CASCADE** : 28 FKs identifiés (mix CASCADE / NO ACTION / SET NULL)

**Colonne `status`** : ✅ **EXISTE** (alternative à `is_active` ?)

---

## PROBE 1.1 — Colonne `process_workspaces.is_active`

**Résultat** : ⚠️ **COLONNE ABSENTE**

**Conséquence** : Migration Alembic P3.2 **doit créer** `is_active BOOLEAN NOT NULL DEFAULT TRUE` avant soft-delete.

**Alternative** : Colonne **`status`** existe (type TEXT, défaut `'draft'::text`) — pourrait être utilisée au lieu de créer `is_active`.

---

## PROBE 1.2 — Tables avec colonne `workspace_id`

**Résultat** : ✅ **28 tables** trouvées avec `workspace_id UUID NOT NULL` (ou NULL pour 2 tables)

### Liste exhaustive :

| Table | workspace_id type | Nullable |
|---|---|---|
| `assessment_comments` | UUID | NOT NULL |
| `assessment_history` | UUID | NOT NULL |
| `bundle_documents` | UUID | NOT NULL |
| `clarification_requests` | UUID | NOT NULL |
| `committee_deliberation_events` | UUID | NOT NULL |
| `committee_session_members` | UUID | NOT NULL |
| `committee_sessions` | UUID | NOT NULL |
| `criterion_assessment_history` | UUID | NOT NULL |
| `criterion_assessments` | UUID | NOT NULL |
| `dao_criteria` | UUID | NOT NULL |
| `deliberation_messages` | UUID | NOT NULL |
| `deliberation_threads` | UUID | NOT NULL |
| `documents` | UUID | NOT NULL |
| `elimination_log` | UUID | NOT NULL |
| `evaluation_documents` | UUID | NOT NULL |
| `evaluation_domains` | UUID | NOT NULL |
| `market_surveys` | UUID | NULL |
| `mql_query_log` | UUID | NULL |
| `offer_extractions` | UUID | NOT NULL |
| `price_line_bundle_values` | UUID | NOT NULL |
| `price_line_comparisons` | UUID | NOT NULL |
| `score_history` | UUID | NOT NULL |
| `signal_relevance_log` | UUID | NULL |
| `source_package_documents` | UUID | NOT NULL |
| `supplier_bundles` | UUID | NOT NULL |
| `validated_analytical_notes` | UUID | NOT NULL |
| `workspace_events` | UUID | NOT NULL |
| `workspace_memberships` | UUID | NOT NULL |

**Constat** : Architecture workspace-first bien établie (28 tables liées).

---

## PROBE 1.3 — Tables listées par CTO (existence)

**Tables CTO** :
1. `process_runs` → ⚠️ **MISSING** (nom incorrect ou legacy)
2. `procurement_documents` → ⚠️ **MISSING** (nom incorrect ou legacy)
3. `vendor_offers` → ⚠️ **MISSING** (nom incorrect ou legacy)
4. `evaluation_documents` → ✅ **EXISTS** (avec workspace_id)
5. `criterion_assessments` → ✅ **EXISTS** (avec workspace_id)
6. `bundle_documents` → ✅ **EXISTS** (avec workspace_id)
7. `dao_criteria` → ✅ **EXISTS** (avec workspace_id)

### Équivalents probables (schéma réel) :

| Table CTO (attendue) | Table réelle (trouvée) | Hypothèse |
|---|---|---|
| `process_runs` | ❓ Aucune équivalence | Peut-être `workspace_events` ? |
| `procurement_documents` | `documents` | Table générique documents |
| `vendor_offers` | `offer_extractions` OU `supplier_bundles` | Offres vendors = extractions ou bundles |

**Action requise** : ÉTAPE 2 doit utiliser les **noms réels** (`documents`, `offer_extractions`, `supplier_bundles`, etc.) et **ignorer** les noms CTO inexistants.

---

## PROBE 1.4 — Foreign keys `workspace_id` → `process_workspaces`

**Résultat** : ✅ **28 foreign keys** identifiés

### Règles CASCADE :

| Table | DELETE rule | UPDATE rule |
|---|---|---|
| `assessment_comments` | **CASCADE** | NO ACTION |
| `assessment_history` | **CASCADE** | NO ACTION |
| `bundle_documents` | NO ACTION | NO ACTION |
| `clarification_requests` | **CASCADE** | NO ACTION |
| `committee_deliberation_events` | NO ACTION | NO ACTION |
| `committee_session_members` | NO ACTION | NO ACTION |
| `committee_sessions` | NO ACTION | NO ACTION |
| `criterion_assessment_history` | **CASCADE** | NO ACTION |
| `criterion_assessments` | **CASCADE** | NO ACTION |
| `dao_criteria` | NO ACTION | NO ACTION |
| `deliberation_messages` | **CASCADE** | NO ACTION |
| `deliberation_threads` | **CASCADE** | NO ACTION |
| `documents` | NO ACTION | NO ACTION |
| `elimination_log` | NO ACTION | NO ACTION |
| `evaluation_documents` | NO ACTION | NO ACTION |
| `evaluation_domains` | **CASCADE** | NO ACTION |
| `market_surveys` | NO ACTION | NO ACTION |
| `mql_query_log` | **SET NULL** | NO ACTION |
| `offer_extractions` | NO ACTION | NO ACTION |
| `price_line_bundle_values` | **CASCADE** | NO ACTION |
| `price_line_comparisons` | **CASCADE** | NO ACTION |
| `score_history` | NO ACTION | NO ACTION |
| `signal_relevance_log` | **SET NULL** | NO ACTION |
| `source_package_documents` | **CASCADE** | NO ACTION |
| `supplier_bundles` | NO ACTION | NO ACTION |
| `validated_analytical_notes` | **CASCADE** | NO ACTION |
| `workspace_events` | NO ACTION | NO ACTION |
| `workspace_memberships` | NO ACTION | NO ACTION |

### Analyse CASCADE :

**Tables CASCADE (12/28)** : soft-delete `is_active = FALSE` ne déclenche **PAS** CASCADE (UPDATE pas DELETE).

**Tables NO ACTION (14/28)** : données liées restent intactes (ex: `dao_criteria`, `evaluation_documents`, `supplier_bundles`).

**Tables SET NULL (2/28)** : `mql_query_log`, `signal_relevance_log` → `workspace_id` devient NULL si workspace supprimé (pas impacté par soft-delete).

**Conclusion** : Soft-delete `is_active = FALSE` **ne déclenche aucun CASCADE** (seul DELETE déclenche CASCADE). Toutes les données liées (critères, offres, évaluations) restent intactes.

---

## PROBE 1.5 — Schéma complet `process_workspaces`

**Résultat** : ✅ **28 colonnes** identifiées

### Colonnes clés :

| Colonne | Type | Nullable | Default | Note |
|---|---|---|---|---|
| `id` | UUID | NOT NULL | gen_random_uuid() | PK |
| `tenant_id` | UUID | NOT NULL | - | FK tenants (RLS) |
| `created_by` | INTEGER | NOT NULL | - | FK users |
| `reference_code` | TEXT | NOT NULL | - | Identifiant workspace |
| `title` | TEXT | NOT NULL | - | Titre dossier |
| `process_type` | TEXT | NOT NULL | - | dao / rfp / devis_unique |
| `estimated_value` | NUMERIC | NULL | - | Valeur estimée |
| `currency` | TEXT | NOT NULL | 'XOF' | Devise |
| `humanitarian_context` | TEXT | NOT NULL | 'none' | Contexte humanitaire |
| `min_offers_required` | INTEGER | NOT NULL | 1 | Seuil offres minimum |
| `sealed_bids_required` | BOOLEAN | NOT NULL | false | Plis scellés requis |
| `committee_required` | BOOLEAN | NOT NULL | false | Comité requis |
| **`status`** | **TEXT** | **NOT NULL** | **'draft'** | **État workflow** |
| `procurement_file` | JSONB | NOT NULL | '{"po": "absent", ...}' | Fichiers dossier |
| `created_at` | TIMESTAMPTZ | NOT NULL | now() | Date création |
| `assembled_at` | TIMESTAMPTZ | NULL | - | Date assemblage |
| `sealed_at` | TIMESTAMPTZ | NULL | - | Date scellement |
| `closed_at` | TIMESTAMPTZ | NULL | - | Date clôture |
| `legacy_case_id` | TEXT | NULL | - | ID legacy (migration cases) |

### Colonnes absentes :

- ❌ **`is_active`** — doit être créée

### Colonne alternative : `status`

**Type** : TEXT  
**Défaut** : `'draft'`  
**Usage actuel** : workflow (draft / active / completed / archived ?)

**Question décision** : Utiliser **`status`** existante pour soft-delete (ex: `status = 'ARCHIVED_LEGACY'`) **OU** créer nouvelle colonne **`is_active`** ?

---

## DECISION POINT — `is_active` vs `status`

### Option A : Créer `is_active` (conformité Option B CTO)

**Migration** :
```sql
ALTER TABLE process_workspaces
ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
```

**Avantages** :
- Colonne dédiée soft-delete (sémantique claire)
- Indépendant de `status` (workflow séparé de archivage)

**Inconvénients** :
- Nouvelle colonne (augmente largeur table)
- Redondance potentielle avec `status` (deux mécanismes exclusion)

### Option B : Utiliser `status` existante

**Soft-delete** :
```sql
UPDATE process_workspaces
SET status = 'ARCHIVED_LEGACY'
WHERE id IN (...19 IDs...);
```

**Avantages** :
- Pas de nouvelle colonne (utilise existant)
- Cohérent workflow DMS (`status` contrôle cycle de vie)

**Inconvénients** :
- Mélange workflow métier (draft/active/completed) et archivage legacy
- Nécessite audit valeurs `status` actuelles (quelles valeurs autorisées ?)

### Recommandation agent :

**Option A — créer `is_active`** (conformité décision CTO "soft-delete via `is_active = FALSE`").

**Justification** :
- Décision CTO explicite : "Option B — soft-delete via `is_active = FALSE`"
- Séparation concerns : `status` = workflow métier, `is_active` = archivage technique
- Évite pollution `status` avec valeur `ARCHIVED_LEGACY` (non métier)

**Alternative acceptable** : Si CTO préfère utiliser `status` existante (éviter nouvelle colonne), documenter mapping :
- `status = 'ARCHIVED_LEGACY'` → workspace exclu corpus actif P3.2

---

## ACTIONS POST-PROBE SCHÉMA

### ✅ PROBE 1 TERMINÉ

**Findings** :
1. `is_active` **ABSENTE** → doit être créée
2. 3 tables CTO **MISSING** → utiliser équivalents réels (`documents`, `offer_extractions`, `supplier_bundles`)
3. 28 tables workspace_id identifiées
4. 28 FKs CASCADE/NO ACTION/SET NULL (soft-delete ne déclenche pas CASCADE)
5. Colonne `status` existe (alternative à `is_active`)

### ⬜ ÉTAPE 2 — Traçabilité réelle (next)

**Queries ÉTAPE 2** doivent utiliser **noms tables réels** :
- ❌ `process_runs` → remplacer par `workspace_events` (hypothèse)
- ❌ `procurement_documents` → remplacer par `documents`
- ❌ `vendor_offers` → remplacer par `offer_extractions` + `supplier_bundles`

**Migration Alembic préalable** (avant soft-delete) :
```sql
-- Créer is_active si décision CTO = Option A
ALTER TABLE process_workspaces
ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
```

---

**Probe schéma archivé. Attente décision CTO : créer `is_active` (Option A) ou utiliser `status` (Option B) ?**
