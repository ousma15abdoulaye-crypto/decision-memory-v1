# AUDIT M4→M7 — RAPPORT COMPLET POUR ÉVALUATION

**Mandat :** Audit médico-légal hostile · Version 2.0  
**Date :** 2026-03-08  
**Référence :** DMS V4.1.0 FREEZE DÉFINITIF  
**Nature :** Lecture seule · Aucune modification

---

# PARTIE I — SERMENT ET SYNTHÈSE

## Serment d'audit

```
Aucune écriture de code.
Aucune migration.
Aucune modification de données.
Aucune purge.
Aucune restauration.
Lecture seule.
Toute zone grise = anomalie.
Tout ce qui n'est pas prouvé = faux.
```

## Verdict global

| Critère | Statut |
|---------|--------|
| alembic heads | 1 ligne — CONFORME |
| DB locale | m7_4_dict_vivant ≠ head m7_4a — DÉRIVE |
| Repo | Working tree sale — CONTAMINÉ |
| Première corruption | M7.2 taxonomy_reset |
| Audit DONE | OUI |

---

# PARTIE II — PROBES RAW

## Git status

```
On branch feat/m7-rebuild-dict-from-terrain
Changes not staged for commit:
  modified:   docs/milestones/HANDOVER_AGENT.md
  modified:   scripts/build_dictionary.py
  modified:   scripts/etl_vendors_wave2.py
  modified:   scripts/seed_taxonomy_v2.py
  modified:   tests/dict/test_m7_3b_legacy_block.py

Untracked files: 50+ (probes, logs, mandats, scripts _probe_*)
```

## Alembic

```
heads:   m7_4a_item_identity_doctrine (head)
current: m7_4_dict_vivant
```

## Counts DB (local)

```
items: 1490
aliases: 1596
proposals pending: 1439
collision_log M6: 0
```

---

# PARTIE III — TABLE FREEZE ↔ REPO ↔ DB

| Milestone | Head attendu freeze | Migration repo | Verdict |
|-----------|---------------------|----------------|---------|
| M4 | 039_seed_vendors_mali | ABSENT — 039 = hardening (M2B) | USURPATION |
| M5 | 040_mercuriale_ingest | Existe (chaîne différente) | DÉRIVE |
| M6 | 041_procurement_dictionary | ABSENT — 041 = vendor_identities (M4) | USURPATION |
| M7 | — | m7_2 à m7_4a présents | INCOHÉRENT |

**Constat :** Table Partie XI DMS_V4.1.0_FREEZE.md OBSOLÈTE.

---

# PARTIE IV — CHAÎNE ALEMBIC RÉELLE

```
m7_4a_item_identity_doctrine  ← HEAD
  ↑ m7_4_dict_vivant
  ↑ m7_3b_deprecate_legacy_families
  ↑ m7_3_dict_nerve_center
  ↑ m7_2_taxonomy_reset
  ↑ m6_dictionary_build
  ↑ m5_patch_imc_ingest_v410
  ↑ m5_geo_patch_koutiala
  ↑ 040_mercuriale_ingest
  ↑ m5_geo_fix_master
  ↑ m5_cleanup_a_committee_event_type_check
  ↑ m5_fix_market_signals_vendor_type
  ↑ m5_pre_vendors_consolidation
  ↑ m4_patch_a_fix
  ↑ m4_patch_a_vendor_structure_v410
  ↑ 043_vendor_activity_badge
  ↑ 042_vendor_fixes
  ↑ 041_vendor_identities  ← M4 réel
  ↑ 040_geo_master_mali   ← M3
  ↑ 039_created_at_timestamptz  ← M2B
```

---

# PARTIE V — INVARIANTS ATOMIQUES (A→K)

| Invariant | Objet | Sévérité | Verdict |
|-----------|-------|----------|---------|
| A. Existence métier item | procurement_dict_items | S2 | HYBRIDE |
| B. Identité permanente | item_id, item_uid, item_code | S1 | CANONIQUE/NON CANONIQUE |
| C. Provenance source | source, dict_version | S2 | CONFORME |
| D. Normalisation | M5 brut → M6 | S0 | CONFORME |
| E. Alias | procurement_dict_aliases | S0 | CONFORME |
| F. Collision | dict_collision_log | S2 | À AUDITER |
| G. Taxonomie | taxo L1/L2/L3 | S3 | DÉRIVE ACTIVE |
| H. Enrichissement M7 | M7 vs M6 | S3 | USURPATION PARTIELLE |
| I. FK / delete rules | FKs taxo→dict | S0 | CONFORME |
| J. Scripts | build_dictionary, etl, seed_taxo | S2 | SUSPECT |
| K. Repo/DB truth | alignement | S2 | INCOHÉRENT |

---

# PARTIE VI — BRANCHES M4→M7

| Branche | Verdict |
|---------|---------|
| feat/m4-* | SAINE |
| feat/m5-* | SAINE |
| feat/m6-dictionary-build | SAINE |
| feat/m7-dictionary-enrichment | SAINE |
| feat/m7-2-taxonomy-reset | SUSPECTE |
| feat/m7-3-dict-nerve-center | SUSPECTE |
| feat/m7-3b-deprecate-legacy | SAINE |
| feat/m7-rebuild-dict-from-terrain | SUSPECTE |

**Résumé :** 8 SAINES, 3 SUSPECTES, 0 MALADES.

---

# PARTIE VII — AUTOPSIE MIGRATIONS

| Migration | Verdict |
|-----------|---------|
| m6_dictionary_build | Canonique |
| m7_2_taxonomy_reset | Dérivante |
| m7_3_dict_nerve_center | Dérivante |
| m7_3b_deprecate_legacy_families | Canonique |
| m7_4_dict_vivant | Canonique |
| m7_4a_item_identity_doctrine | Dérivante |

---

# PARTIE VIII — DETTES CHIRURGICALES

| Dette | Sévérité | Bloque reconstruction ? |
|-------|----------|-------------------------|
| Freeze table Partie XI obsolète | S4 | Oui |
| Taxonomie prédéfinie vs dérivée | S3 | Oui |
| M7 usurpation fondation M6 | S3 | Oui |
| DB locale ≠ head | S2 | Non |
| collision_log M6 = 0 | S2 | Non |
| TD-009, TD-001, TD-016, etc. | S1-S2 | Non |

---

# PARTIE IX — CHRONOLOGIE PREMIÈRE CORRUPTION

| Point | Identification |
|-------|----------------|
| Dernier point sûr | M6 dictionary build |
| Premier point ambigu | Freeze Partie XI obsolète |
| **Premier point de dérive prouvé** | **M7.2 taxonomy_reset** |
| Premier point corruption invariant | Couplage registre↔taxonomie |
| Premier point hors réel | Taxonomie L1/L2/L3 prédéfinie (15/57/155) |
| M7 fait travail M6 | M7.4a item_uid, item_code, birth_* |

---

# PARTIE X — VERDICT PAR COMPOSANT

| Composant | Verdict |
|-----------|---------|
| vendors M4 | À CONSERVER |
| mercuriale ingest M5 | À CONSERVER |
| dictionary build M6 | À CONSERVER |
| dict enrichment M7 | À FIGER |
| identité item | À REBÂTIR DEPUIS LE RÉEL |
| alias | À CONSERVER |
| collisions | À FIGER |
| proposals | À CONSERVER |
| taxonomie | À DÉPRÉCIER |
| scripts purge | À INTERDIRE |
| FKs dictionnaire | À CONSERVER |
| migrations M4→M7 | À FIGER |
| branches M4→M7 | À CONSERVER |

---

# PARTIE XI — PÉRIMÈTRE RECONSTRUCTION

**À conserver :** vendors, mercuriale_sources, mercurials, procurement_dict_items, procurement_dict_aliases, dict_proposals, dict_collision_log, build_dictionary, ETL.

**À reconstruire (si décision) :** Dictionnaire depuis mercurials + IMC, identité item (item_uid/item_code backfill complet), séparation registre/taxonomie.

**À figer :** Migrations M7.2 à M7.4a, colonnes taxo sur dict_items, classify_taxonomy_v2, seed_taxonomy_v2.

---

# PARTIE XII — ORDRE OUVERTURE SUITE

1. **Probe** : Mettre à jour table freeze↔repo. Probe collision_log.
2. **Migration** : alembic upgrade head local.
3. **ADR** : Séparation identité/registre/taxonomie. Taxonomie dérivée vs imposée.
4. **Mandat dépréciation** : Documenter colonnes M7 structurelles.
5. **Mandat reconstruction** : Si rebâtir — mercurials + IMC → dict, zéro dépendance taxonomie.

---

# FICHIERS SOURCE (détails complets)

- `AUDIT_M4_M7_TRIBUNAL.md`
- `AUDIT_M4_M7_PROBES_RAW.md`
- `AUDIT_M4_M7_INVARIANTS.md`
- `AUDIT_M4_M7_BRANCHES_MALADES.md`
- `AUDIT_M4_M7_DETTES_CHIRURGICALES.md`
- `AUDIT_M4_M7_VERDICT_RECONSTRUCTION.md`
