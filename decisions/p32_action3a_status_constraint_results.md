# P3.2 ACTION 3A — Résultats contrainte CHECK status

**Date** : 2026-04-18  
**Environnement** : Railway prod (sci_mali)  
**Statut** : ✅ **PROBE TERMINÉ**

---

## RÉSULTATS PROBE

### Contrainte CHECK sur `process_workspaces.status`

**Contrainte détectée** : `process_workspaces_status_check`

**Définition** :
```sql
CHECK ((status = ANY (ARRAY[
    'draft'::text,
    'assembling'::text,
    'assembled'::text,
    'in_analysis'::text,
    'analysis_complete'::text,
    'in_deliberation'::text,
    'sealed'::text,
    'closed'::text,
    'cancelled'::text
])))
```

**Valeurs autorisées** (9 valeurs) :
1. `draft` — brouillon
2. `assembling` — assemblage en cours
3. `assembled` — assemblé (prêt analyse)
4. `in_analysis` — en analyse
5. `analysis_complete` — analyse complète
6. `in_deliberation` — en délibération
7. `sealed` — scellé (résultats figés)
8. `closed` — clôturé
9. `cancelled` — annulé

### Valeurs status actuelles (sci_mali)

**Total workspaces sci_mali** : 93 workspaces

| Status | Count | % |
|---|---|---|
| `assembling` | 52 | 56% |
| `draft` | 34 | 37% |
| `analysis_complete` | 3 | 3% |
| `sealed` | 2 | 2% |
| `in_deliberation` | 1 | 1% |
| `closed` | 1 | 1% |

**Constat** : 52 workspaces en status `assembling` — les 21 LEGACY_90 ciblés sont dans ce groupe.

---

## PROBLÈME : `ARCHIVED_LEGACY` NON AUTORISÉE

**Tentative initiale** : utiliser `status = 'ARCHIVED_LEGACY'` pour soft-delete.

**Blocage** : Contrainte CHECK n'autorise **pas** `ARCHIVED_LEGACY` → UPDATE rejeté par PostgreSQL.

**Options disponibles** :

### Option A : Utiliser `cancelled` (recommandé)

**Valeur** : `status = 'cancelled'`

**Sémantique** : workspace annulé/abandonné (cohérent avec legacy)

**Avantages** :
- Autorisée par CHECK constraint existant
- Sémantique claire (workspace non finalisé, abandonné)
- Déjà présente dans enum (pas de migration)

**Inconvénients** :
- Mélange workspaces annulés métier + legacy technique
- Si `cancelled` a usage métier existant, peut créer confusion

**SQL ACTION 3B** :
```sql
UPDATE process_workspaces
SET status = 'cancelled'
WHERE reference_code IN (...21 codes...)
  AND status = 'assembling';
```

### Option B : Utiliser `closed`

**Valeur** : `status = 'closed'`

**Sémantique** : workspace clôturé (finalisé)

**Avantages** :
- Autorisée par CHECK constraint
- Workspace "terminé" (ne sera plus traité)

**Inconvénients** :
- Sémantique incorrecte : LEGACY_90 ne sont **pas** clôturés proprement (sum=90% incohérent)
- 1 workspace déjà `closed` (usage métier existant)

### Option C : Modifier CHECK constraint (déconseillé)

**Action** : Migration Alembic ajoutant `'ARCHIVED_LEGACY'` au CHECK constraint

**SQL** :
```sql
ALTER TABLE process_workspaces
DROP CONSTRAINT process_workspaces_status_check;

ALTER TABLE process_workspaces
ADD CONSTRAINT process_workspaces_status_check CHECK (
    status = ANY (ARRAY[
        'draft', 'assembling', 'assembled', 'in_analysis',
        'analysis_complete', 'in_deliberation', 'sealed',
        'closed', 'cancelled', 'ARCHIVED_LEGACY'  -- ← ajoutée
    ]::text[])
);
```

**Avantages** :
- Valeur dédiée legacy (sémantique claire)
- Séparation concerns (legacy ≠ cancelled métier)

**Inconvénients** :
- Nécessite migration Alembic **avant** soft-delete
- Ajoute complexité (modification CHECK constraint)
- CTO a demandé **aucune migration avant corpus clean confirmé**

---

## RECOMMANDATION AGENT

**Option A recommandée** : `status = 'cancelled'`

**Justification** :
1. Autorisée par CHECK existant (pas de migration)
2. Sémantique acceptable (workspace abandonné)
3. Exécution immédiate possible (pas de blocage technique)
4. Filtrage runtime simple : `WHERE status NOT IN ('cancelled')`

**Alternative acceptable** : Option C (modifier CHECK) **si CTO accepte migration préalable** (mais contradictoire avec "aucune migration avant corpus clean").

---

## DÉCISION CTO REQUISE

**Question** : Quelle valeur status utiliser pour soft-delete 21 LEGACY_90 ?

**Options** :
- **A** : `cancelled` (immédiat, pas de migration)
- **B** : `closed` (immédiat, sémantique incorrecte)
- **C** : `ARCHIVED_LEGACY` (nécessite migration CHECK constraint avant)

**Critères décision** :
1. Usage métier actuel de `cancelled` / `closed` (conflit ?)
2. Acceptabilité migration CHECK avant soft-delete (Option C)
3. Filtrage runtime : `WHERE status NOT IN ('cancelled')` acceptable ?

---

## APRÈS DÉCISION CTO

**Si Option A ou B** : compléter template ACTION 3B avec valeur choisie → exécuter

**Si Option C** : créer migration Alembic CHECK constraint → exécuter migration → puis ACTION 3B

---

**Probe ACTION 3A archivé. Attente décision CTO sur valeur status.**
