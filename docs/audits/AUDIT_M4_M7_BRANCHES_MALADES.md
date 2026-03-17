# AUDIT M4→M7 — BRANCHES MALADES

**Date :** 2026-03-08  
**Règle tribunal :** Une branche qui touche au-delà de son milestone = coupable jusqu'à preuve contraire  
**Référence :** DMS V4.1.0 FREEZE DÉFINITIF

---

## CARTOGRAPHIE COMPLÈTE BRANCHES M4→M7

### feat/m4-vendor-importer

| Attribut | Valeur |
|----------|--------|
| **Point de départ** | main (avant M4) |
| **Milestone annoncé** | M4 — import fournisseurs |
| **Milestone réel touché** | M4 |
| **Commits clés** | `a299c23 Update src/vendors/normalizer.py` |
| **Schéma touché** | OUI — 041_vendor_identities.py, 042_vendor_fixes.py, 043_vendor_activity_badge.py |
| **Scripts touchés** | OUI — src/vendors/ |
| **Tables cœur touchées** | vendors, vendor_identities |
| **Périmètre respecté** | OUI |
| **Verdict** | **SAINE** |

---

### feat/m4-patch-a

| Attribut | Valeur |
|----------|--------|
| **Point de départ** | main |
| **Milestone annoncé** | M4 — patch structure vendor |
| **Milestone réel touché** | M4 |
| **Commits clés** | `m4_patch_a_vendor_structure_v410.py` |
| **Schéma touché** | OUI — m4_patch_a_vendor_structure_v410 |
| **Scripts touchés** | OUI — etl_vendors_wave2.py |
| **Tables cœur touchées** | vendors |
| **Périmètre respecté** | OUI |
| **Verdict** | **SAINE** |

---

### feat/m4-patch-b

| Attribut | Valeur |
|----------|--------|
| **Point de départ** | main |
| **Milestone annoncé** | M4 — import wave 2 (661 fournisseurs) |
| **Milestone réel touché** | M4 |
| **Commits clés** | `f2bbee1 feat(PATCH-B): import wave 2 661 fournisseurs Mali FINAL` |
| **Schéma touché** | NON |
| **Scripts touchés** | OUI — etl_vendors_wave2.py |
| **Tables cœur touchées** | vendors |
| **Périmètre respecté** | OUI |
| **Verdict** | **SAINE** |

---

### feat/m5-mercuriale-ingest

| Attribut | Valeur |
|----------|--------|
| **Point de départ** | main |
| **Milestone annoncé** | M5 — ingestion mercuriales Mali 2023+2024 |
| **Milestone réel touché** | M5 |
| **Commits clés** | `9f83989 feat(m5-mercuriale): ingestion mercuriales officielles Mali 2024+2023` |
| **Schéma touché** | OUI — 040_mercuriale_ingest.py |
| **Scripts touchés** | OUI — import_mercuriale.py |
| **Tables cœur touchées** | mercuriale_sources, mercurials |
| **Périmètre respecté** | OUI |
| **Verdict** | **SAINE** |

---

### feat/m5-patch-imc-ingest

| Attribut | Valeur |
|----------|--------|
| **Point de départ** | main |
| **Milestone annoncé** | M5 — ingest INSTAT Mali (92 PDFs, 9 catégories/mois) |
| **Milestone réel touché** | M5 |
| **Commits clés** | `c82ae4d feat(m5-patch-imc): IMC ingest INSTAT Mali` |
| **Schéma touché** | OUI — m5_patch_imc_ingest_v410 |
| **Scripts touchés** | OUI — import_imc.py |
| **Tables cœur touchées** | imc_entries, mercuriale_sources |
| **Périmètre respecté** | OUI |
| **Verdict** | **SAINE** |

---

### feat/m6-dictionary-build

| Attribut | Valeur |
|----------|--------|
| **Point de départ** | main |
| **Milestone annoncé** | M6 — dictionnaire procurement AOF |
| **Milestone réel touché** | M6 |
| **Commits clés** | `a326329 feat(m6): dictionary build - 1488 items - 1596 aliases` |
| **Schéma touché** | OUI — m6_dictionary_build.py : étend procurement_dict_items, crée dict_proposals, étend dict_collision_log, recrée vues public |
| **Scripts touchés** | OUI — build_dictionary.py |
| **Tables cœur touchées** | procurement_dict_items, procurement_dict_aliases, dict_proposals, dict_collision_log |
| **Périmètre respecté** | OUI |
| **Anomalie** | AUCUNE — schéma étendu conformément à M6 |
| **Verdict** | **SAINE** |

---

### feat/m7-dictionary-enrichment

| Attribut | Valeur |
|----------|--------|
| **Point de départ** | feat/m7-3-dict-nerve-center |
| **Milestone annoncé** | M7 — enrichissement LLM, dict_version 1.1.0 |
| **Milestone réel touché** | M7 |
| **Commits clés** | `32b2ef0 feat(m7): dictionary enrichment - LLM classification` |
| **Schéma touché** | NON |
| **Scripts touchés** | OUI — classify (LLM) |
| **Tables cœur touchées** | procurement_dict_items (via classification) |
| **Périmètre respecté** | OUI |
| **Anomalie** | Point de départ non-main (part de feat/m7-3-dict-nerve-center) — branche secondaire |
| **Verdict** | **SAINE** |

---

### feat/m7-2-taxonomy-reset

| Attribut | Valeur |
|----------|--------|
| **Point de départ** | main (après M6) |
| **Milestone annoncé** | M7 — taxonomie L1/L2/L3 enterprise grade |
| **Milestone réel touché** | M7 — mais touche fondation M6 |
| **Commits clés** | `eb09dbf feat(m7.2): taxonomy L1/L2/L3 enterprise grade · 15 domaines · 57 familles · 155 sous-familles` |
| **Schéma touché** | OUI — m7_2_taxonomy_reset.py |
| **Scripts touchés** | OUI — seed_taxonomy_v2.py |
| **Tables cœur touchées** | taxo_l1_domains, taxo_l2_families, taxo_l3_subfamilies, procurement_dict_items (colonnes ajoutées) |
| **Périmètre respecté** | NON |
| **Anomalie 1** | Colonnes domain_id/family_l2_id/subfamily_id ajoutées sur procurement_dict_items → modification de la table cœur M6 depuis une branche M7 |
| **Anomalie 2** | Taxonomie L1/L2/L3 prédéfinie dans le code Python (15 domaines codés en dur) avant classification corpus → doctrine inversée |
| **Anomalie 3** | seed_taxonomy_v2.py insère une structure imposée, pas dérivée du réel |
| **Verdict** | **SUSPECTE** — périmètre M7 dépassé, taxonomie imposée avant réel |

---

### feat/m7-3-dict-nerve-center

| Attribut | Valeur |
|----------|--------|
| **Point de départ** | main (après M7.2) |
| **Milestone annoncé** | M7.3 — dict nerve center, infrastructure cœur dictionnaire |
| **Milestone réel touché** | M7 — mais touche structure profonde |
| **Commits clés** | `1dd9efb feat(m7.3): dict nerve center - aligned hash canon B2-A` / `52b741c fix(PR#169): corrections CTO` |
| **Schéma touché** | OUI — m7_3_dict_nerve_center.py |
| **Scripts touchés** | NON (migration seule) |
| **Tables cœur touchées** | procurement_dict_items (7 colonnes ajoutées), dict_price_references (créée), dict_uom_conversions (créée), dgmp_thresholds (créée), dict_item_suppliers (créée), 3 triggers |
| **Périmètre respecté** | PARTIEL |
| **Anomalie 1** | Infrastructure lourde (4 tables nouvelles, 3 triggers) introduite en M7 — travail de fondation, pas d'enrichissement |
| **Anomalie 2** | Trigger fn_compute_quality_score dépend de domain_id (colonne M7.2) → couplage quality_score ↔ taxonomie dans le trigger même |
| **Anomalie 3** | Colonnes unspsc_code, item_type, default_uom, default_currency = structure métier imposée en M7 sans mandat M6 |
| **Verdict** | **SUSPECTE** — infrastructure métier lourde hors périmètre enrichissement |

---

### feat/m7-3b-deprecate-legacy

| Attribut | Valeur |
|----------|--------|
| **Point de départ** | main (après M7.3) |
| **Milestone annoncé** | M7.3b — dépréciation family_id legacy M6 |
| **Milestone réel touché** | M7.3b — clôture dette M6 |
| **Commits clés** | `4f46955 feat(m7.3b): deprecate legacy family_id - triggers, migration, tests` |
| **Schéma touché** | OUI — m7_3b_deprecate_legacy_families.py : trigger blocage, DROP NOT NULL family_id, commentaires |
| **Scripts touchés** | NON |
| **Tables cœur touchées** | procurement_dict_items (family_id DROP NOT NULL, triggers), procurement_dict_families (colonne deprecated) |
| **Périmètre respecté** | OUI — action de clôture sur dette M6 documentée ADR-0016 |
| **Verdict** | **SAINE** |

---

### feat/m7-rebuild-dict-from-terrain

| Attribut | Valeur |
|----------|--------|
| **Point de départ** | main |
| **Branche active** | OUI — HEAD courant |
| **Milestone annoncé** | Restauration migrations m7_4/m7_4a — alignement Railway prod |
| **Commits** | `7219636 chore(m7): restore m7_4/m7_4a migrations · alignement Railway prod` |
| **Schéma touché** | OUI — restore migrations |
| **Scripts touchés** | OUI — build_dictionary.py, etl_vendors_wave2.py, seed_taxonomy_v2.py MODIFIÉS non commités |
| **Tables cœur touchées** | procurement_dict_items (via m7_4a) |
| **Périmètre respecté** | NON |
| **Anomalie 1** | 5 fichiers modifiés non commités dont 3 scripts critiques — le périmètre réel de cette branche est non auditable |
| **Anomalie 2** | build_dictionary.py modifié non commité — script M6 touché depuis branche M7 |
| **Anomalie 3** | seed_taxonomy_v2.py modifié non commité — structure taxonomie non figée |
| **Anomalie 4** | test_m7_3b_legacy_block.py modifié non commité — tests de régression potentiellement altérés |
| **Verdict** | **SUSPECTE** — working tree sale, scripts critiques modifiés hors scope du commit officiel |

---

## SYNTHÈSE CLASSIFICATION

| Branche | Verdict | Justification |
|---------|---------|---------------|
| feat/m4-vendor-importer | SAINE | Périmètre M4 respecté |
| feat/m4-patch-a | SAINE | Périmètre M4 respecté |
| feat/m4-patch-b | SAINE | Périmètre M4 respecté |
| feat/m5-mercuriale-ingest | SAINE | Périmètre M5 respecté |
| feat/m5-patch-imc-ingest | SAINE | Périmètre M5 respecté |
| feat/m6-dictionary-build | SAINE | Périmètre M6 respecté, résultats prouvés |
| feat/m7-dictionary-enrichment | SAINE | Enrichissement uniquement |
| feat/m7-3b-deprecate-legacy | SAINE | Clôture dette documentée ADR-0016 |
| feat/m7-2-taxonomy-reset | **SUSPECTE** | Taxonomie prédéfinie imposée avant corpus, colonnes M6 modifiées depuis M7 |
| feat/m7-3-dict-nerve-center | **SUSPECTE** | Infrastructure lourde en M7, couplage quality_score↔taxonomie |
| feat/m7-rebuild-dict-from-terrain | **SUSPECTE** | Scripts critiques modifiés non commités, périmètre non auditable |

| Verdict | Nombre |
|---------|--------|
| SAINE | 8 |
| SUSPECTE | 3 |
| MALADE | 0 |
| À DÉPRÉCIER | 0 |
| À ABANDONNER | 0 |

---

## BRANCHES SUSPECTES — ANALYSE CAUSALE

### Pourquoi feat/m7-2-taxonomy-reset est SUSPECTE et non MALADE

Elle n'est pas MALADE car :
- La migration est appliquée et fonctionnelle
- Les FK sont NO ACTION (pas de CASCADE)
- Le travail d'ADR-0016 a partiellement reconnu le problème

Elle est SUSPECTE car :
- Elle a touché la table cœur M6 (procurement_dict_items) depuis une branche M7
- Elle a introduit une taxonomie imposée avant corpus
- Elle a créé le couplage structurel registre↔taxonomie

### Pourquoi feat/m7-3-dict-nerve-center est SUSPECTE et non MALADE

Elle n'est pas MALADE car :
- Le trigger quality_score a été patché en O(1) (M7.4)
- Les tables créées (dict_price_references, etc.) sont vides ou controlées
- La révision CTO (PR#169) a corrigé 8 dérives identifiées

Elle est SUSPECTE car :
- Elle a introduit 4 tables d'infrastructure en M7 (travail de fondation, pas d'enrichissement)
- Le couplage trigger↔taxonomie reste actif

### Pourquoi feat/m7-rebuild-dict-from-terrain est SUSPECTE et non MALADE

Elle n'est pas MALADE car :
- Son seul commit officiel (`restore m7_4/m7_4a`) est justifié
- La chaîne alembic reste linéaire

Elle est SUSPECTE car :
- 3 scripts critiques sont modifiés mais non commités
- Le périmètre réel de ces modifications est non auditable
- Le working tree sale empêche tout audit complet de cette branche

---

## VERDICT CHIRURGICAL BRANCHES

| Branche | Action |
|---------|--------|
| feat/m4-* (3 branches) | À CONSERVER — saines, mergées sur main |
| feat/m5-* (2 branches) | À CONSERVER — saines, mergées sur main |
| feat/m6-dictionary-build | À CONSERVER — saine, mergée sur main, fondation prouvée |
| feat/m7-dictionary-enrichment | À CONSERVER — enrichissement conforme |
| feat/m7-3b-deprecate-legacy | À CONSERVER — clôture dette, mergée sur main |
| feat/m7-2-taxonomy-reset | À FIGER — mergée sur main, dette documentée, interdire nouvelles colonnes |
| feat/m7-3-dict-nerve-center | À FIGER — mergée sur main, infrastructure en place, interdire extension |
| feat/m7-rebuild-dict-from-terrain | À NETTOYER — commiter ou reverter les 5 fichiers modifiés avant tout merge |
