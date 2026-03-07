# CONTEXTE DE SESSION — Nouvelle session agent

**Date :** 2026-03-06  
**Objectif :** Reprise de session — mémoire agent arrivée à terme  
**Workspace :** `C:\Users\abdoulaye.ousmane\decision-memory-v1`  
**Branche :** `feat/m7-3b-deprecate-legacy` (PR #170)  
**Tag courant :** `v4.2.0-m7-3b-done`

---

## 1. RÉSUMÉ EXÉCUTIF — CE QUI A ÉTÉ FAIT

### Sprint M7.3b Dépréciation legacy (PR #170)

| Action | Statut |
|--------|--------|
| ADR-0016 détour M7.2/M7.3 | ✅ Committé |
| Migration `m7_3b_deprecate_legacy_families` | ✅ Livrée |
| family_id READ-ONLY (triggers INSERT + UPDATE) | ✅ Actif |
| Corrections PR #170 (D1–D5) | ✅ Appliquées |
| Tag `v4.2.0-m7-3b-done` | ✅ Créé et poussé |
| Handovers et chat context | ✅ À jour |

### Sprint M7.3 Dict Nerve Center (PR #169 — merged)

| Action | Statut |
|--------|--------|
| Migration `m7_3_dict_nerve_center` | ✅ Livrée |
| Migration `m7_2_taxonomy_reset` | ✅ Livrée |
| Corrections CTO (9 défauts D1–D9) | ✅ Appliquées |
| Tag `v4.1.0-m7.3-done` | ✅ Créé |

### Corrections PR #170 (D1–D5)

| D | Désignation | Correction |
|---|-------------|------------|
| D2 | downgrade non idempotent | DO block EXECUTE pour DROP NOT NULL |
| D3 | Trigger UPDATE laisse passer SET NULL | WHEN sans AND NEW.family_id IS NOT NULL |
| D4 | URL psycopg | Normalisation postgresql:// dans probe_m7_3b |
| D1 | Noms tests désalignés | test_p10/pa8 → test_alembic_head_est_m7_3b |
| D5 | Pollution DB tests | uuid suffix, fixture tx rollback |

### Défauts CTO M7.3 corrigés (D1–D9)

| D | Désignation | Correction |
|---|-------------|------------|
| D8 | Advisory lock | `pg_advisory_xact_lock` dans `fn_dict_write_audit` (aligné avec `write_event()`) |
| D5 | Backfill dans migration | Backfill retiré · script `scripts/seed_classification_backfill.py` créé |
| D7 | Downgrade M7.2 | DROP colonnes FK avant DROP TABLE taxo_* |
| D6 | Tests head | `m6_dictionary_build` → `m7_3_dict_nerve_center` (5 fichiers) |
| D2+D3 | Seed taxonomy | `ok = False` après chaque [KO] dans `scripts/seed_taxonomy_v2.py` |
| D1 | Libellés L1/L2/L3 | Libellés « tentés (ON CONFLICT DO NOTHING) » |
| D9 | Index partiels | Index partiels corrigés sur `dict_uom_conversions` |
| D4 | Documentation | HANDOVER_AGENT.md, migration-checklist.md mis à jour |

---

## 2. DONNÉES PARSÉES — SOURCES ET EMPLACEMENTS

### Règle absolue

Les fichiers Excel/PDF contenant des données terrain ne sont **jamais committés** (RÈGLE-15).  
`.gitignore` : `data/**/*.xlsx`, `data/**/*.csv`, `data/**/*.json`, `data/imports/imc/`, `data/imports/m5/cache/`.

### Tableau des imports

| Source | Format | Emplacement local | Script d'import | Table(s) PostgreSQL |
|--------|--------|-------------------|-----------------|----------------------|
| **Vendors M4** | Excel (.xlsx) | `data/imports/m4/` | `scripts/etl_vendors_m4.py` | `public.vendors` |
| **Vendors Wave 2** | Excel | `data/imports/m4/SUPPLIER DATA Mali FINAL.xlsx` | `scripts/etl_vendors_wave2.py` | `public.vendors` |
| **Mercuriales** | PDF | `data/imports/m5/*.pdf` | `scripts/import_mercuriale.py` | `mercuriale_sources`, `mercurials` |
| **IMC** | PDF | `data/imports/imc/*.pdf` | `scripts/import_imc.py` | `imc_sources`, `imc_entries` |

### Parsers (code source)

| Parser | Fichier | Rôle |
|--------|---------|------|
| **Mercuriale** | `src/couche_b/mercuriale/parser.py` | Parse PDF mercuriales DGMP · regex PARSE-001 à PARSE-006 |
| **Mercuriale ingest** | `src/couche_b/mercuriale/ingest_parser.py` | Intégration LlamaCloud / extraction |
| **IMC** | `src/couche_b/imc/parser.py` | Parse PDF INSTAT Mali · pdfplumber · matériaux construction Bamako |

### Mapping colonnes (réf. docs)

- **Mercuriales :** `docs/data/MERCURIALE_COLUMN_MAP.md` — item_code, item_canonical, unit_raw, price_min/avg/max, zone_raw, group_label, year
- **IMC :** `category_raw`, `index_value`, `year`, `month` — format AOUT18, JAN26, DEC25, etc.

### Zones mercuriales (16 zones Mali)

`_ZONE_FROM_FILENAME` dans `import_mercuriale.py` : Bamako, Bougouni, Dioïla, Gao, Kidal, Kita, Koulikoro, Ménaka, Mopti, Nara, Nioro, San, Ségou, Sikasso, Taoudeni, Tombouctou.

---

## 3. HANDOVERS ET RAPPORTS

### Documents de transmission

| Fichier | Rôle |
|---------|------|
| `docs/milestones/HANDOVER_AGENT.md` | **Source de vérité agent** — règles, état repo, pièges, PROBE-SQL-01 |
| `docs/milestones/HANDOVER_M73B_TRANSMISSION.md` | Transmission M7.3b + PR #170 |
| `docs/milestones/HANDOVER_M73_TRANSMISSION.md` | Transmission M7.3 — migrations, D1–D9, validation 13 gates |
| `docs/mandates/M7_3B_MANDAT_ADR.md` | Mandat M7.3b + ADR-0016 |
| `docs/milestones/HANDOVER_M4_TRANSMISSION.md` | Verdict enterprise-grade · failles F1–F9 |
| `docs/milestones/HANDOVER_M5FIX_TRANSMISSION.md` | PIÈGE-8 à PIÈGE-15 |
| `docs/milestones/HANDOVER_M5PRE_TRANSMISSION.md` | Sprint M5-PRE |

### Rapports et audits

| Fichier | Rôle |
|---------|------|
| `docs/freeze/DMS_V4.1.0_FREEZE.md` | **Source de vérité unique** — 29 règles, architecture |
| `TECHNICAL_DEBT.md` | Dettes actives, stubs, Backfill M7.3 |
| `docs/dev/migration-checklist.md` | Doctrine migrations · DML interdit |
| `docs/mandates/M7_3_PATH_EXEC_AND_HASH_ALIGNMENT.md` | Mandat M7.3 |

---

## 4. TAXONOMIE ACTUELLE (M7.2)

| Niveau | Table | Nombre |
|--------|--------|--------|
| L1 (domaines) | `taxo_l1_domains` | 15 |
| L2 (familles) | `taxo_l2_families` | 57 |
| L3 (sous-familles) | `taxo_l3_subfamilies` | 155 (+ DIVERS_NON_CLASSE) |

**Legacy :** `procurement_dict_families` = 9 familles.

### Scripts post-migration obligatoires

```bash
# 1. Seed taxonomie (M7.2)
python scripts/seed_taxonomy_v2.py --verify
python scripts/seed_taxonomy_v2.py

# 2. Backfill classification_confidence (M7.3)
python scripts/seed_classification_backfill.py --dry-run
python scripts/seed_classification_backfill.py
```

---

## 5. GAPS / À FAIRE

| Élément | État |
|---------|------|
| `procurement_dict_items` | 1488 items · `domain_id`, `family_l2_id`, `subfamily_id` à NULL pour beaucoup |
| `taxo_proposals_v2` | Vide ou non alimentée |
| `seed_classification_backfill.py` | Met à jour `classification_confidence` uniquement · pas les colonnes taxonomie |
| Classification L1/L2/L3 | Aucun script ne produit de propositions (LLM ou règles manquants) |
| **Prochain sprint** | M7 réel : classify_taxo.py → seed_apply_taxo.py → v4.2.0-m7-dict-vivant |

---

## 6. ÉTAT SYSTÈME

| Élément | Valeur |
|---------|--------|
| Alembic head | `m7_3b_deprecate_legacy_families` |
| Tests | 825 passed · 36 skipped · 0 failed |
| ruff + black | Verts |
| family_id | READ-ONLY total · triggers actifs |

### Chaîne Alembic (du plus récent)

```
m7_3b_deprecate_legacy_families  ← HEAD
m7_3_dict_nerve_center
m5_patch_imc_ingest_v410
m5_geo_patch_koutiala
040_mercuriale_ingest
m5_geo_fix_master
m5_cleanup_a_committee_event_type_check
m5_fix_market_signals_vendor_type
m5_pre_vendors_consolidation
...
```

---

## 7. SCRIPTS UTILITAIRES

| Script | Usage |
|--------|-------|
| `scripts/etl_vendors_m4.py` | Import vendors M4 (Bamako + Mopti) |
| `scripts/etl_vendors_wave2.py` | Import SUPPLIER DATA Mali FINAL.xlsx |
| `scripts/import_mercuriale.py` | Import PDF mercuriales (LlamaCloud) |
| `scripts/import_imc.py` | Import PDF IMC (pdfplumber, local) |
| `scripts/build_dictionary.py` | Build procurement dict depuis couche_b |
| `scripts/seed_taxonomy_v2.py` | Seed L1/L2/L3 |
| `scripts/seed_classification_backfill.py` | Backfill classification_confidence post-M7.3 |
| `scripts/probe_m7_3b.py` | Probe pré-migration M7.3b |
| `scripts/apply_fk_prod.py` | FK market_signals → vendors (prod uniquement) |

---

## 8. RÉFÉRENCES RAPIDES

- **Agent transcripts :** `C:\Users\abdoulaye.ousmane\.cursor\projects\c-Users-abdoulaye-ousmane-decision-memory-v1\agent-transcripts`
- **7 gates merge :** alembic heads, history, upgrade, cycle down/up, pytest, ruff+black, fichiers hors périmètre
- **RÈGLE-ORG-10 :** Agent ne merge que si 7 gates vertes ET autorisation CTO explicite

---

---

## 9. M7.3b — RÈGLES GRAVÉES

- **RÈGLE-DICT-01** : family_id = READ-ONLY après M7.3b
- **RÈGLE-DICT-02** : domain_id/family_l2_id/subfamily_id = cibles M7.2
- **RÈGLE-39** : URL postgresql:// · jamais postgresql+psycopg://

---

*Document généré pour reprise de session · 2026-03-06 · M7.3b done*
