# P3.2 ACTION F4 — Scope Decision (GCF-E2E-*)

**Date** : 2026-04-18  
**Statut** : ✅ **DÉCISION EXPLICITE**

---

## QUESTION

**GCF-E2E-* workspaces inclus dans migration 101 : OUI / NON ?**

---

## CORPUS CONNU

**Source vérité** : `decisions/p32_r1_corpus_90pct_decision.md` + Actions 1-3 P3.2-R1

**Workspaces actifs après nettoyage** :
- `CASE-28b05d85` : workspace canonique (50/40/10 capacity/commercial/sustainability)
- `GCF-E2E-TEST-001` (estimé)
- `GCF-E2E-TEST-002` (estimé)
- `GCF-E2E-TEST-003` (estimé)
- `GCF-E2E-TEST-004` (estimé)

**Statut GCF-E2E-*** : présumé `status != 'cancelled'` (workspaces E2E / test intégration)

---

## ANALYSE INCLUSION

### Critères migration 101 (l.76-96)

**Clause WHERE backfill** :
```sql
WHERE dc.family IS NOT NULL
  AND dc.ponderation IS NOT NULL
  AND pw.status NOT IN ('cancelled')
```

**Logique d'inclusion** :
- ✅ Si `pw.status != 'cancelled'` → **workspace inclus**
- ✅ Si `dc.ponderation IS NOT NULL` → **critères inclus**
- ✅ Si `dc.family IS NOT NULL` (post-backfill family) → **critères inclus**

**Conclusion** : **GCF-E2E-* INCLUS** si `status != 'cancelled'` (automatique, pas de filtre explicit workspace_id).

---

## DÉCISION EXPLICITE

**Réponse** : ✅ **OUI** — GCF-E2E-* workspaces **INCLUS** dans migration 101

**Justification** :

1. **Clause migration générique** : pas de filtre `workspace_id IN (...)` → tous workspaces actifs touchés
2. **Cohérence corpus P3.2** : GCF-E2E-* font partie du corpus actif post-nettoyage (21 LEGACY_90 exclus)
3. **Tests E2E** : GCF-E2E-* nécessitent schéma P3.2 pour tests intégration pipeline
4. **Doctrine workspace-first** : migration s'applique **uniformément** à tous workspaces actifs (pas de segmentation ad-hoc)

---

## IMPACT ATTENDU

### Rows `dao_criteria` affectées

**Estimation** :
- `CASE-28b05d85` : ~15 rows (3 familles × ~5 critères)
- `GCF-E2E-*` : 4 workspaces × ~15 rows = ~60 rows

**Total** : **~75 rows** dao_criteria backfillées

### Rows `process_workspaces` affectées

**Colonne** : `technical_qualification_threshold FLOAT NOT NULL DEFAULT 50.0`

**Workspaces touchés** : **5 workspaces** (CASE-28b05d85 + 4 GCF-E2E-*)

**Valeur** : default 50.0 appliqué à tous

---

## RISQUES GCF-E2E-*

### Risque 1 : `criterion_category = 'essential'` présent

**Si GCF-E2E-* contiennent critères essential** :
- `family = NULL` (doctrine métier)
- `criterion_mode = 'GATE'` (backfill l.118-123)
- Hors agrégat 50/40/10 (cohérent doctrine)

**Impact** : ✅ **acceptable** (doctrine opposable appliquée uniformément)

### Risque 2 : `ponderation IS NULL` sur GCF-E2E-*

**Si rows avec `ponderation IS NULL`** :
- `weight_within_family` reste NULL (exclus backfill)
- Brise somme famille (mais pas invariant CASE-28b05d85)

**Impact** : ⚠️  **acceptable SI E2E** (workspaces test peuvent avoir données incomplètes)

**Mitigation** : probe F2b confirme COUNT NULL par workspace

### Risque 3 : Distribution familles != 50/40/10

**Si GCF-E2E-* ont distribution différente** (ex: 30/60/10) :
- Backfill `weight_within_family` respecte distribution locale (calcul par workspace + famille)
- Pas d'imposition 50/40/10 (calcul intra-famille normalisé à 100%)

**Impact** : ✅ **acceptable** (formule générique, adapte distribution workspace)

---

## EXCLUSION ALTERNATIVE (REJETÉE)

**Option rejetée** : exclure GCF-E2E-* via filtre `workspace_id = 'CASE-28b05d85'`

**Raisons rejet** :
1. ❌ Brise doctrine workspace-first (migration sélective = tech debt)
2. ❌ GCF-E2E-* resteraient en schéma legacy (incompatible P3.2 ScoringCore)
3. ❌ Tests E2E échoueraient (colonnes manquantes family, weight_within_family)
4. ❌ Migration ultérieure nécessaire (double travail)

---

## VERDICT F4

**Décision** : ✅ **GCF-E2E-* INCLUS dans migration 101**

**Clause migration** : inchangée (générique, pas de filtre workspace_id)

**Impact attendu** : ~75 rows dao_criteria + 5 rows process_workspaces

**Risques acceptés** :
- ⚠️  NULLs résiduels possibles sur E2E (données test incomplètes) — probe F2 mesure
- ⚠️  Distribution != 50/40/10 possible sur E2E — formule intra-famille s'adapte

**Doctrine opposable** : migration s'applique uniformément à corpus actif (RÈGLE-ANCHOR workspace-first).

---

**F4 CLOSED — GCF-E2E-* INCLUS (décision explicite)**
