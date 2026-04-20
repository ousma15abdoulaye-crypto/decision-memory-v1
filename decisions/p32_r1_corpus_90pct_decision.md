# P3.2 R1 — DÉCISION CORPUS 90% (BRUIT LEGACY)

**Date** : 2026-04-18  
**Référence** : MANDAT_P3.2 R1-data-only — probe ponderation  
**Statut** : ⛔ **MIGRATION BLOQUÉE** — nettoyage corpus requis

---

## FINDINGS PROBE R1

**Tenant sci_mali** : `0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe`

### Workspace conforme (1/20)

| Workspace | Sum ponderation | Pattern famille | Statut |
|---|---|---|---|
| **CASE-28b05d85** | **100.00%** | 50/40/10 (technique/commercial/durabilité) | ✅ **CONFORME** |

**Conclusion workspace conforme** :
- Somme ponderation = 100% (tous critères)
- Pattern métier 50/40/10 respecté (SCI §5.2)
- **SEUL workspace de référence P3.2**

### Workspaces legacy (19/20)

**Pattern détecté** : sum = **90.00%** (30/50/10)

**Liste des 19 workspaces LEGACY_90** (à compléter après query ACTION 1) :

```
[PENDING — exécuter p32_action1_identify_90pct_workspaces.sql]

Attendu :
- 19 reference_codes avec sum=90%
- Pattern 30/50/10 (déviation par rapport à 50/40/10)
```

**Constat** :
- Somme ponderation = 90% (incohérente)
- Pattern 30/50/10 ≠ pattern métier 50/40/10
- **BRUIT LEGACY** — critères mal configurés ou abandonnés

---

## DÉCISION CTO

**Les 19 workspaces sum=90% sont du BRUIT LEGACY.**

**Exclusion corpus actif P3.2** :
- ❌ Ne servent **PAS** de référence pour backfill `weight_within_family`
- ❌ Ne sont **PAS** inclus dans benchmark B3 (concordance système)
- ❌ Ne sont **PAS** consommés par ScoringCore P3.2

**Workspace de référence P3.2** : **CASE-28b05d85 uniquement**

---

## IMPLICATIONS P3.2

### Backfill `weight_within_family`

**Méthode validée** (basée sur CASE-28b05d85) :
```sql
-- Backfill UNIQUEMENT sur workspace conforme (sum=100%)
WITH family_sums AS (
    SELECT 
        workspace_id,
        famille,
        SUM(ponderation) AS sum_famille
    FROM dao_criteria
    WHERE famille IS NOT NULL 
      AND ponderation IS NOT NULL
      AND workspace_id IN (
          -- Filtre : UNIQUEMENT workspaces sum=100%
          SELECT pw.id
          FROM dao_criteria dc
          JOIN process_workspaces pw ON dc.workspace_id = pw.id
          WHERE pw.tenant_id = '0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe'
            AND dc.ponderation IS NOT NULL
          GROUP BY pw.id
          HAVING ABS(SUM(dc.ponderation) - 100.0) <= 0.01
      )
    GROUP BY workspace_id, famille
)
UPDATE dao_criteria dc
SET weight_within_family = ROUND((dc.ponderation / fs.sum_famille) * 100.0)::INTEGER
FROM family_sums fs
WHERE dc.workspace_id = fs.workspace_id
  AND dc.famille = fs.famille
  AND dc.ponderation IS NOT NULL
  AND fs.sum_famille > 0;
```

**Exclusion explicite** : Les 19 workspaces LEGACY_90 ne reçoivent **PAS** de backfill `weight_within_family` (WHERE sum=100% uniquement).

### Benchmark B3 (Article 8)

**Corpus benchmark** : annotations sci_mali **doivent** correspondre à workspace(s) conforme(s) sum=100%.

**Action requise** : vérifier que `m12_corpus_from_ls.jsonl` (110 annotations) provient de CASE-28b05d85 ou workspaces sum=100%.

### ScoringCore P3.2 (Article 5)

**Consommation** : ScoringCore lit `dao_criteria.weight_within_family` **uniquement** sur workspaces actifs sum=100%.

**Validation runtime** : ajouter gate P3.2 qui rejette workspace si sum(ponderation) ≠ 100% ± 0.01.

---

## ACTIONS ORDONNÉES (BLOQUANTES MIGRATION)

### ⬜ ACTION 1 — Archivage décision (ce document)

**Statut** : ⏳ EN COURS

**Manque** : liste complète des 19 reference_codes (exécuter query `p32_action1_identify_90pct_workspaces.sql`)

### ⬜ ACTION 2 — Probe traçabilité

**Objectif** : identifier origine des 19 workspaces LEGACY_90

**Query** : `p32_action2_legacy_workspace_trace.sql` (à créer)

**Archivage** : `decisions/p32_r2_legacy_workspace_trace.md`

### ⬜ ACTION 3 — Proposition nettoyage

**Objectif** : rédiger 3 options traitement (hard delete / soft delete / isolation tenant)

**Archivage** : `decisions/p32_r3_nettoyage_corpus_proposal.md`

**Validation CTO requise** avant toute modification DB

---

## VERDICT R1 FINAL

**Ponderation = GLOBALE** (confirmé sur CASE-28b05d85 : sum=100% tous critères)

**Backfill weight_within_family** :
- **Méthode** : `(ponderation / SUM_famille) × 100`
- **Périmètre** : workspaces sum=100% **uniquement**
- **Exclusion** : 19 workspaces LEGACY_90

**Bloqueur migration P3.2** : nettoyage corpus (ACTION 2 + ACTION 3) requis avant `alembic upgrade`.

---

## COMMANDE SUIVANTE CTO

**Exécuter ACTION 1 query** :
```bash
# Railway psql
railway connect postgres

# Copier-coller contenu p32_action1_identify_90pct_workspaces.sql
```

**Remonter output complet** → agent complète ce document avec liste des 19 reference_codes.

---

**Décision opposable. Migration bloquée jusqu'à nettoyage corpus validé CTO.**
