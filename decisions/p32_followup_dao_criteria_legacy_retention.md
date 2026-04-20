# P3.2 FOLLOW-UP — dao_criteria LEGACY RETENTION

**Date** : 2026-04-18  
**Référence** : P3.2 ACTION 3D — séparation concerns  
**Statut** : 📋 **NOTE HORS EXÉCUTION** — arbitrage ultérieur

---

## CONSTAT

**63 rows `dao_criteria` legacy** associées aux 21 workspaces LEGACY_90 (status `ARCHIVED_LEGACY`) restent présentes en base de données.

**Calcul** : 21 workspaces × ~3 critères/workspace = 63 rows `dao_criteria` (estimation)

---

## DÉCISION CTO ACTION 3

**Soft-delete logique** : exclusion corpus actif P3.2 via `process_workspaces.status` uniquement.

**Préservation trace legacy** : aucune suppression `dao_criteria` à ce stade.

**Motif** : exclusion corpus actif ≠ destruction de trace legacy.

---

## STATUT dao_criteria LEGACY

### Conservation provisoire

**Rows conservées** : 63 `dao_criteria` associées aux 21 workspaces `ARCHIVED_LEGACY`

**Raisons conservation** :
1. **Audit trail** : trace historique des critères legacy (analyse forensic future possible)
2. **Réversibilité** : si soft-delete workspace annulé (`status` restauré), critères restent disponibles
3. **Analyse pattern** : comprendre pourquoi sum=90% (pattern 30/50/10 vs 50/40/10)
4. **Compliance** : obligations légales conservation données (si applicable)

### Impact P3.2

**Backfill `weight_within_family`** : 63 rows legacy **exclus** du backfill (WHERE workspace actif uniquement)

**ScoringCore P3.2** : 63 rows legacy **jamais consommés** (ScoringCore filtre workspace actif)

**Benchmark B3** : 63 rows legacy **exclus** du benchmark (annotations corpus = workspace conforme uniquement)

**Performance DB** : 63 rows représentent volume négligeable (vs milliers rows actives futures)

---

## FILTRAGE RUNTIME

**Queries DMS** doivent filtrer workspaces actifs :

```sql
-- Pattern filtrage corpus actif P3.2
SELECT ...
FROM dao_criteria dc
JOIN process_workspaces pw ON dc.workspace_id = pw.id
WHERE pw.tenant_id = '0daf2d94-93dc-4d56-a8b9-84a2a4b17bbe'
  AND pw.status NOT IN ('ARCHIVED_LEGACY')  -- Filtre workspaces exclus
  AND dc.ponderation IS NOT NULL;
```

**Toutes queries P3.2** (backfill, ScoringCore, benchmark) incluent ce filtre.

---

## ARBITRAGE ULTÉRIEUR

**Hors périmètre P3.2** : décision sur rétention long terme des 63 rows `dao_criteria` legacy.

**Options futures** (post-P3.2) :

### Option A : Conservation permanente

**Action** : Aucune suppression, rows legacy conservées indéfiniment.

**Justification** : audit trail, compliance, réversibilité.

**Coût** : volume DB négligeable (63 rows).

### Option B : Suppression différée

**Action** : `DELETE FROM dao_criteria WHERE workspace_id IN (21 IDs legacy)` après période rétention (ex: 6 mois).

**Justification** : nettoyage DB après confirmation aucun besoin audit.

**Prérequis** : validation compliance/légal avant suppression.

### Option C : Archivage externe

**Action** : Export CSV/JSON des 63 rows → stockage externe (R2, S3) → suppression DB.

**Justification** : libérer DB tout en préservant trace accessible.

**Coût** : implémentation pipeline export/archivage.

---

## DÉCISION ATTENDUE (POST-P3.2)

**Timeline** : après migration P3.2 en production + validation corpus actif stable.

**Parties prenantes** : CTO + compliance/légal (si obligations conservation).

**Critères décision** :
1. Besoin audit trail long terme ?
2. Obligations légales conservation données ?
3. Coût stockage DB vs bénéfice conservation ?
4. Probabilité réversibilité soft-delete workspace legacy ?

---

## ACTIONS P3.2 (IMMÉDIATES)

✅ **Aucune suppression dao_criteria** : 63 rows conservées provisoirement

✅ **Filtrage runtime** : toutes queries P3.2 incluent `WHERE status NOT IN ('ARCHIVED_LEGACY')`

✅ **Backfill exclu** : 63 rows legacy ne reçoivent **pas** de backfill `weight_within_family`

✅ **Documentation** : ce fichier archive décision conservation provisoire

---

## RÉSUMÉ

**Constat** : 63 rows `dao_criteria` legacy toujours présentes (associées 21 workspaces `ARCHIVED_LEGACY`)

**Décision immédiate** : conservation provisoire (trace legacy préservée)

**Action P3.2** : aucune suppression, filtrage runtime uniquement

**Arbitrage futur** : rétention long terme à décider post-P3.2 (hors périmètre ouverture migration)

---

**Note archivée. Hors exécution P3.2. Arbitrage ultérieur requis.**
