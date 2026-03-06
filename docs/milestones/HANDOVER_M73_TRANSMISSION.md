# NOTE DE TRANSMISSION — M7.3 DICT NERVE CENTER · SPRINT CLOS

```
Date de clôture : 2026-03-06
Sprint          : M7.3 Dict Nerve Center (alignement B2-A audit_log canon)
Agent           : Composer — session PR #169
Branche         : feat/m7-3-dict-nerve-center → PR #169 → merged main
Tag             : v4.1.0-m7.3-done
Successeur      : Agent M7 Dictionary Validation / M8+
Référence V4    : docs/freeze/DMS_V4.1.0_FREEZE.md
Mandat          : docs/mandates/M7_3_PATH_EXEC_AND_HASH_ALIGNMENT.md
```

---

## I. ÉTAT SYSTÈME À LA CLÔTURE

| Élément | Valeur |
|---------|--------|
| Branche de référence | `main` |
| Alembic head | `m7_3_dict_nerve_center` · **1 seul head** |
| Tag Git | `v4.1.0-m7.3-done` → commit clôture |
| Tests | 0 failed · 0 error (pytest -q) |
| ruff + black | Verts |
| Hash chain | **Conforme** · advisory lock + formule alignée |
| DB prod Railway | `m7_3_dict_nerve_center` à appliquer au prochain deploy |

---

## II. CE QUE CE SPRINT A LIVRÉ

### Migrations

| Révision | Contenu |
|----------|---------|
| `m7_2_taxonomy_reset` | Taxonomie L1/L2/L3 · 15 domaines · 57 familles · 155 sous-familles · taxo_proposals_v2 |
| `m7_3_dict_nerve_center` | Tables dict_price_references, dict_uom_conversions, dgmp_thresholds, dict_item_suppliers · colonnes procurement_dict_items · triggers fn_dict_compute_hash, fn_dict_write_audit, fn_compute_quality_score |

### Corrections CTO PR #169 (9 défauts D1–D9)

| Défaut | Correction appliquée |
|--------|----------------------|
| **D8** | `pg_advisory_xact_lock` dans `fn_dict_write_audit` · clé identique à `write_event()` logger.py:131 |
| **D5** | Backfill DML retiré de la migration · `scripts/seed_classification_backfill.py` créé · TECHNICAL_DEBT.md |
| **D7** | Downgrade m7_2 : DROP colonnes FK (domain_id, family_l2_id, subfamily_id, etc.) avant DROP TABLE taxo_* |
| **D6** | Tests head : `m6_dictionary_build` → `m7_3_dict_nerve_center` (5 fichiers) |
| **D2+D3** | `ok = False` après chaque [KO] L2/L3/DIVERS_NON_CLASSE dans `scripts/seed_taxonomy_v2.py` |
| **D1** | Labels : "L1/L2/L3 insérés" → "L1/L2/L3 tentés (ON CONFLICT DO NOTHING)" |
| **D9** | Index partiels dict_uom_conversions : suppression WHERE sur colonnes NOT NULL |
| **D4** | Documentation HEAD : HANDOVER_AGENT.md, migration-checklist.md |

### Hash chain — conformité

| Critère | Statut |
|---------|--------|
| Advisory lock (même clé que write_event) | ✅ `('x' || md5('audit_log:write_event'))::bit(64)::bigint` |
| Formule event_hash alignée fn_verify_audit_chain | ✅ entity \|\| entity_id \|\| action \|\| actor_id \|\| payload_canonical \|\| timestamp \|\| chain_seq \|\| prev_hash |
| Séquence unique audit_log_chain_seq_seq | ✅ |
| fn_verify_audit_chain (fix plage partielle) | ✅ M7.3 |

---

## III. DONNÉES — EMPLACEMENTS (NON COMMITTÉES)

| Donnée | Fichiers source | Emplacement local | Table PostgreSQL après import |
|--------|-----------------|-------------------|------------------------------|
| **Vendors (M4)** | `data/imports/m4/SUPPLIER DATA Mali FINAL.xlsx` | Local · .gitignore `data/**/*.xlsx` | `public.vendors` |
| **Mercuriales (M5)** | `data/imports/m5/*.pdf` | Local · non versionnés | `mercuriale_sources`, `mercurials` |
| **IMC** | `data/imports/imc/*.pdf` | Local · .gitignore `data/imports/imc/` | `imc_sources`, `imc_entries` |

**Règle absolue :** Les fichiers Excel/PDF contenant des données terrain ne sont jamais committés (RÈGLE-15). Déposer manuellement avant chaque import.

---

## IV. SCRIPTS POST-MIGRATION OBLIGATOIRES

### 1. Seed taxonomie (M7.2)

```bash
python scripts/seed_taxonomy_v2.py --verify   # Vérification seule
python scripts/seed_taxonomy_v2.py            # Insertion L1/L2/L3
```

### 2. Backfill classification_confidence (M7.3)

**À exécuter manuellement après `alembic upgrade head`** (DML interdit dans migrations).

```bash
python scripts/seed_classification_backfill.py --dry-run
python scripts/seed_classification_backfill.py
```

Documenté dans `TECHNICAL_DEBT.md` section "Backfill M7.3".

---

## V. RÉTROSPECTIVE HASH CHAIN (V4 depuis M4)

**Verdict :** Aucune correction rétroactive nécessaire.

| Point d'écriture audit_log | Jalon | Advisory lock | Formule | Statut |
|----------------------------|-------|---------------|---------|--------|
| `write_event()` | M1B | ✅ | ✅ | Conforme |
| `fn_dict_write_audit` | M7.3 | ✅ (D8) | ✅ | Conforme |

Migrations M4 → M7.2 : aucune écriture audit_log. Seul M7.3 ajoute un trigger conforme.

---

## VI. PIÈGES RENCONTRÉS

### PIÈGE-M73-1 · D7 downgrade FK

Le downgrade de `m7_2_taxonomy_reset` doit DROP les colonnes FK (`domain_id`, `family_l2_id`, `subfamily_id`, etc.) de `procurement_dict_items` **avant** DROP TABLE taxo_l1_domains/l2/l3. Sinon : `ERROR: cannot drop table taxo_l1_domains because other objects depend on it`.

**Fix appliqué :** DROP COLUMN en tête du downgrade m7_2.

### PIÈGE-M73-2 · D8 race condition hash chain

Le trigger `fn_dict_write_audit` lisait `prev_hash` sans advisory lock. Concurrence avec `write_event()` → risque de chaîne corrompue (deux entrées avec même prev_hash).

**Fix appliqué :** `PERFORM pg_advisory_xact_lock(('x' || md5('audit_log:write_event'))::bit(64)::bigint)` en tête de la fonction.

### PIÈGE-M73-3 · D5 DML dans migration

Le backfill `UPDATE classification_confidence` dans la migration viole la doctrine (migration-checklist.md lignes 406-416). DML interdit dans Alembic.

**Fix appliqué :** Backfill retiré · script `seed_classification_backfill.py` · exécution manuelle documentée.

---

## VII. VALIDATION AVANT MERGE (13 GATES PR #169)

```
[✓] D8  pg_advisory_xact_lock présent · clé identique logger.py:131
[✓] D5  UPDATE absent migration · seed script créé · TECHNICAL_DEBT.md
[✓] D7  downgrade cycle complet · 0 erreur
[✓] D6  grep m6_dictionary_build tests/ → 0 résultat
[✓] D2  ok=False après L2 KO
[✓] D3  ok=False après L3 KO et DIVERS KO
[✓] D1  labels corrects
[✓] D9  index partiels corrigés
[✓] D4  documentation HEAD à jour
[✓] pytest -q → 0 failed · 0 errors
[✓] ruff + black → verts
[✓] alembic heads → 1 · m7_3_dict_nerve_center
[✓] alembic downgrade -1 + upgrade head → 0 erreur
```

---

## VIII. PROCHAIN SPRINT — M7 DICTIONARY VALIDATION

- **dict_proposals** : 1439 pending → validation humaine → intégration procurement_dict_items
- **Taxonomie** : seed_taxonomy_v2.py à exécuter si non fait
- **Backfill** : seed_classification_backfill.py post-migration

---

*Agent : Composer · DMS V4.1.0 · M7.3 Dict Nerve Center · 2026-03-06*
