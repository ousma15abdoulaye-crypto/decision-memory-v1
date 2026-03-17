# M7.3 — PATH EXEC + ALIGNEMENT HASH CANON

**Règle absolue** : M7.3 n'introduit aucun ledger parallèle. Le mécanisme `audit_log`/`decision_snapshots` est canon. Toute traçabilité dict doit s'aligner dessus.

**Modification obligatoire (STEP 4)** : Supprimer toute idée de "nouvelle chaîne hash parallèle" type `dict_item_history` comme ledger principal. Remplacer par : `public.audit_log` reçoit les événements dict (entity='DICT_ITEM', entity_id=item_id, action='UPDATE', payload minimal). Hash calculé avec l'algo canon existant (`public.digest` / `fn_verify_audit_chain` pattern). **Résultat** : M7.3 ne crée aucun second mécanisme de chaîne "autorité".

---

## ORDRE EXÉCUTION (STEP 1→5)

| STEP | Action | STOP si |
|------|--------|---------|
| 1 | DB safe info (local + Railway) | Railway = localhost |
| 2 | Vendors sur Railway prod | — |
| 3 | ETL wave2 (si prod vendors=0) | dry-run obligatoire |
| 4 | Hash alignment B2-A + probe N_HASH | — |
| 5 | M7.3 TEMPS 0→6 | après 2/3/4 |

**Règle sortie** : toute sortie doit commencer par db/host/port/user + alembic_version.

**PREUVE 1 obligatoire** (identité DB ETL) : `host` ≠ localhost/::1 si prod. `public.vendors = 661`. Si host = localhost → 661 = local, pas prod.

**PREUVE 2 obligatoire** (M7.2 prérequis) : `alembic_version = m7_2_taxonomy_reset`, `couche_b.taxo_l1_domains exists = 1`. Si m6_dictionary_build → M7.2 non appliquée → **STEP 5 M7.3 illégal**. Appliquer/merger M7.2 d'abord.

---

## ALIGNEMENT HASH CANON (B2-A)

### Phrase clé mandat

> M7.3 n'introduit aucun ledger parallèle. Le mécanisme `audit_log`/`decision_snapshots` est canon. Toute traçabilité dict doit s'aligner dessus.

### Décision : CHEMIN B2-A — Reuse audit_log comme ledger

**Pas de nouvelle table blockchain** pour le dict. Chaque update sur `procurement_dict_items` écrit un événement dans `public.audit_log` avec :

- `entity` = 'DICT_ITEM'
- `entity_id` = item_id
- `action` = 'UPDATE'
- `payload` JSON (old/new minimal)
- `event_hash` / `prev_hash` calculés via la fonction existante (pattern fn_verify_audit_chain)
- Append-only déjà enforced → on réutilise.

**Résultat** : une seule chaîne pour tout le système.

**Correction A** : `dict_item_history` (si maintenu) = table technique *non autoritaire*. Ou supprimée du mandat et journalisation dans audit_log uniquement.

### 3 raisons factuelles (issues B1)

1. **audit_log existe** avec `entity`, `entity_id`, `action`, `prev_hash`, `event_hash` — schéma déjà compatible.
2. **fn_verify_audit_chain** + `digest(..., 'sha256')` — algo canon en place.
3. **trg_audit_log_no_delete_update** — append-only déjà enforced.

---

## PATH EXEC (checklist exécution)

Chaque étape = commande + output à poster + STOP.

### TEMPS 0 — Baseline

```bash
git status
alembic heads
pytest --tb=short -q 2>&1 | tail -5
```

**Output à poster** : brut. **STOP-N01** si git non clean. **STOP-N02** si heads > 1. **STOP-N03** si pytest rouge.

---

### TEMPS 1 — Probe N0→N_HASH (incluant B1)

```bash
python scripts/probe_m7_3_nerve_center.py
python scripts/_probe_m73_todo.py   # Part A + Part B
```

**Output à poster** : N0→N9, N_HASH, A1→A3, B1 (tables/colonnes hash, fonctions, triggers).

**STOP-PRE** si M7.2 absente. **STOP-N04** si colonnes/tables M7.3 présentes. **STOP-N11** si hash existant incompatible.

---

### TEMPS 1bis — Décision alignement hash (B2-A OBLIGATOIRE)

**Décision prise** : B2-A. Aucune alternative.

- `public.audit_log` reçoit les événements dict (entity='DICT_ITEM', entity_id=item_id, action='UPDATE', payload minimal).
- Hash calculé avec l'algo canon existant (`public.digest` / `fn_verify_audit_chain` pattern).
- **Interdit** : nouvelle chaîne hash parallèle type `dict_item_history` comme ledger principal.

**Output à poster** : décision + 3 raisons factuelles.

**STOP.** Pas de migration M7.3 tant que B2 n'est pas tranché.

---

### TEMPS 2 — Migration M7.3 (après GO TL)

- down_revision = valeur exacte probe N1
- **Hash chain = audit_log canon** : trigger sur procurement_dict_items → INSERT audit_log (entity='DICT_ITEM')
- Si `last_hash` reste dans `procurement_dict_items` : dérivé du ledger canon ou marqué "cache/denormalized", jamais vérité concurrente
- pgcrypto digest(...,'sha256')
- backfill classification_confidence
- index NULL-safe uom_conv_*

```bash
alembic upgrade head
alembic heads
```

**Output à poster** : alembic heads + alembic current.

---

### TEMPS 3 — Probe post-migration

```bash
python scripts/probe_m7_3_post_migration.py
```

**Output à poster** : complet. **STOP** si erreurs.

---

### TEMPS 4 — Seed UOM

```bash
python scripts/seed_uom_by_family.py
```

**Output à poster** : nb items mis à jour + top 10 familles.

---

### TEMPS 5 — Tests

```bash
pytest tests/test_m7_3_nerve_center.py --tb=short -q
```

**STOP-N10** si rouge. **Output à poster** : tail + premier failure.

---

### TEMPS 6 — Merge / Tag (après ADR-MERGE-002 + GO CTO)

```bash
git add -A
git commit -m "feat(m7.3): dict nerve center · aligned hash canon"
git push origin feat/m7-3-dict-nerve-center
```

**STOP-ADR** : merge/tag = ADR-MERGE-002 + GO CTO obligatoire.

---

## PART A — VENDORS (vérité factuelle)

### A4 — Si prod ≠ 102 minimum → cause racine

Poster uniquement :

- DATABASE_URL cible (masquer secrets, garder host/dbname)
- output A1/A2/A3

**STOP.** Pas d'ETL wave2 avant d'avoir tranché.

### A5 — Si wave2 doit être importée (et seulement si GO)

1. Corriger `scripts/etl_vendors_wave2.py` : recherche xlsx par glob dans `data/imports/m4/`.
2. Mettre à jour références `vendor_identities` → `vendors` (post M5-PRE).
3. `--dry-run` existe déjà.
4. Exécuter dry-run puis réel sur DB cible.

**Outputs à poster** : dry-run résumé, post-run counts + duplicates fingerprint.

---

## Correction B — dict_price_references ≠ mercuriales

Les mercuriales = prix par ligne/zone/année (marché). `dict_price_references` = benchmark stabilisé par item_id + uom + currency + source + période (ex : "prix médian 2024 Mopti", "prix validé AO") — pas "recréer les mercuriales", mais **extraire une référence** utilisable par CBA.

- `dict_price_references` démarre **vide** ✅
- Hydratation depuis mercuriales (M5) via job explicite — pas dans M7.3 (nerve center schema only)
