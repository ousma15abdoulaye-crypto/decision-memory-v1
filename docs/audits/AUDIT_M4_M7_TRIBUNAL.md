# AUDIT M4→M7 — TRIBUNAL TECHNIQUE

**Mandat :** Audit médico-légal hostile — Version 2.0  
**Date :** 2026-03-08  
**Référence :** DMS V4.1.0 FREEZE DÉFINITIF  
**Nature :** LECTURE SEULE — Aucune modification  
**Auditeur :** Agent système engineer entreprise-grade

---

## SERMENT D'AUDIT

```
Tu n'es pas ici pour aider le système.
Tu es ici pour découvrir où il ment.
Tout ce qui n'est pas prouvé est faux.
Toute ambiguïté est une anomalie hostile.
Tu n'écris aucun code.
Tu ne répares rien.
Tu démontes la chaîne M4→M7 jusqu'à identifier la première corruption causale.
Tu classes chaque branche, migration, script, table, invariant et dette.
Tu rends un verdict de chirurgie, pas une opinion.

Aucune écriture de code.
Aucune migration.
Aucune modification de données.
Aucune purge.
Aucune restauration.
Lecture seule.
Toute zone grise = anomalie.
Tout ce qui n'est pas prouvé = faux.
```

---

## 1. VERDICT REPO TRUTH

### Preuve brute — alembic heads

```
m7_4a_item_identity_doctrine (head)
```

**Résultat : 1 ligne — CONFORME au freeze (invariant : exactement 1 head)**

---

### Preuve brute — alembic current (DB locale)

```
m7_4_dict_vivant
```

**Résultat : DB locale sur m7_4_dict_vivant ≠ head m7_4a_item_identity_doctrine**

| Critère | Preuve brute | Verdict |
|---------|--------------|---------|
| `alembic heads` | `m7_4a_item_identity_doctrine (head)` | S0 — CONFORME |
| `alembic current` (local) | `m7_4_dict_vivant` | S2 — DÉRIVE : DB locale en retard d'une migration |
| Branche active | `feat/m7-rebuild-dict-from-terrain` | Branche M7 active, non mergée sur main |
| Fichiers modifiés non commités | 5 fichiers (HANDOVER_AGENT.md, build_dictionary.py, etl_vendors_wave2.py, seed_taxonomy_v2.py, test_m7_3b_legacy_block.py) | S2 — Repo sale |
| Fichiers untracked | 50+ (probes, logs, mandats, scripts _probe_*) | S1 — Pollution working tree |

**Verdict repo : REPO CONTAMINÉ — working tree sale, DB locale en retard sur head**

---

### Preuve brute — git branch -a (extrait M4→M7)

```
feat/m4-patch
feat/m4-patch-a
feat/m4-patch-b
feat/m4-vendor-importer
feat/m5-cleanup-a
feat/m5-fix-pre-ingest
feat/m5-geo-fix
feat/m5-mercuriale-2026
feat/m5-mercuriale-clean
feat/m5-mercuriale-ingest
feat/m5-patch-imc-ingest
feat/m5-pre-hardening
feat/m6-dictionary-build
feat/m7-2-taxonomy-reset
feat/m7-3-dict-nerve-center
feat/m7-3b-deprecate-legacy
feat/m7-dictionary-enrichment
* feat/m7-rebuild-dict-from-terrain
freeze/v4.1.0
```

Branches M4→M7 : identifiables. Chaîne traçable.

---

## 2. TABLE FREEZE ↔ REPO ↔ DB

Le freeze DMS V4.1.0 annonce dans sa Partie XI les noms canoniques suivants :
- M4 head attendu : `039_seed_vendors_mali`
- M5 head attendu : `040_mercuriale_ingest`
- M6 head attendu : `041_procurement_dictionary`

### Table de vérité réelle

| Milestone | Head attendu (freeze Partie XI) | Migration présente repo | Appliquée local | Appliquée Railway | Verdict |
|-----------|----------------------------------|-------------------------|-----------------|-------------------|---------|
| M4 | `039_seed_vendors_mali` | **ABSENT** — 039 = `039_hardening_created_at_timestamptz` (M2B) | — | Non prouvé | **USURPATION** |
| M5 | `040_mercuriale_ingest` | `040_mercuriale_ingest` présente — down_revision = `m5_geo_fix_master` (chaîne divergente) | Prouvé (dans chaîne) | Non prouvé | **DÉRIVE** |
| M6 | `041_procurement_dictionary` | **ABSENT** — 041 = `041_vendor_identities` (M4 réel) | — | Non prouvé | **USURPATION** |
| M7 | non défini freeze | m7_2 → m7_3 → m7_3b → m7_4 → m7_4a présents | m7_4_dict_vivant (local) | Non prouvé | **INCOHÉRENT** |

**Constat prouvé :** La table Partie XI du freeze DMS V4.1.0 est OBSOLÈTE. Les noms `039_seed_vendors_mali`, `040_mercuriale_ingest` (chaîne), `041_procurement_dictionary` ne correspondent pas à la chaîne Alembic réelle du repo. La divergence est antérieure à M4.

---

## 3. CHAÎNE ALEMBIC RÉELLE (M4→M7)

```
m7_4a_item_identity_doctrine   ← HEAD (repo) — NON APPLIQUÉ local
  ↑
m7_4_dict_vivant               ← CURRENT local
  ↑
m7_3b_deprecate_legacy_families
  ↑
m7_3_dict_nerve_center
  ↑
m7_2_taxonomy_reset            ← PREMIER POINT DE DÉRIVE PROUVÉ
  ↑
m6_dictionary_build            ← DERNIER POINT SÛR
  ↑
m5_patch_imc_ingest_v410
  ↑
m5_geo_patch_koutiala
  ↑
040_mercuriale_ingest
  ↑
m5_geo_fix_master
  ↑
m5_cleanup_a_committee_event_type_check
  ↑
m5_fix_market_signals_vendor_type
  ↑
m5_pre_vendors_consolidation
  ↑
m4_patch_a_fix
  ↑
m4_patch_a_vendor_structure_v410
  ↑
043_vendor_activity_badge
  ↑
042_vendor_fixes
  ↑
041_vendor_identities          ← M4 réel (nommé 041 mais c'est M4)
  ↑
040_geo_master_mali            ← M3
  ↑
039_hardening_created_at_timestamptz  ← M2B (freeze annonce ce 039 comme M4)
  ↑
038_audit_hash_chain
  ...
```

---

## 4. SIGNAUX STOP DÉTECTÉS

| Signal | Statut | Preuve |
|--------|--------|--------|
| alembic heads > 1 | NON — 1 head | Conforme |
| Migration attendue freeze absente repo | **OUI** | `039_seed_vendors_mali` absent. `041_procurement_dictionary` absent. |
| Migration présente repo absente Railway (milestone prétendu done) | **NON PROUVÉ** | Railway non sondé directement |
| Table cœur absente en prod | **NON PROUVÉ** | Aucun accès Railway confirmé |
| Script destructif sans garde-fou | **OUI** | `scripts/m7_rebuild_t0_purge.py` : TRUNCATE taxo_proposals_v2, DELETE taxo L1/L2/L3, UPDATE domain_id=NULL sur tous items — aucun dry-run ni confirmation interactive |
| FK cascade taxonomie → dictionnaire | **NON** | FK procurement_dict_items → taxo : ON DELETE non spécifié = NO ACTION |
| ID item dépendant ordre batch / SQL | **NON** | item_id = SHA256(slug)[:16] — déterministe |
| M5 non brut | **NON PROUVÉ** | Scripts mercuriale audités = parse brut. Normalisation dans build_dictionary (M6). Conforme à la doctrine. |
| M6 non construit depuis libellés réels M5 | **NON** — build_dictionary lit `mercurials` + `imc_entries` | Conforme |
| M7 ayant usurpé fondation M6 | **OUI** | M7.2 : colonnes domain_id/family_l2_id/subfamily_id sur procurement_dict_items, FK vers taxo prédéfinie. M7.4a : doctrine identité (item_uid/item_code/birth_*) — travail de M6 exécuté en M7. |

---

## 5. RÉSUMÉ EXÉCUTIF TRIBUNAL

**Verdict 1 — Freeze obsolète (S4)**  
La table Partie XI du freeze ne reflète pas le repo. Les noms 039/041 n'existent pas. Le freeze est une référence non fiable pour tout audit ou reconstruction.

**Verdict 2 — DB locale en retard (S2)**  
`alembic current` = m7_4_dict_vivant alors que head = m7_4a. La migration m7_4a_item_identity_doctrine n'est pas appliquée localement.

**Verdict 3 — Script destructif sans garde-fou (S4)**  
`m7_rebuild_t0_purge.py` exécute TRUNCATE + DELETE + UPDATE massif en une transaction. Aucun mode dry-run identifié. Aucune confirmation interactive. Exécution accidentelle = destruction totale de la classification et de la taxonomie.

**Verdict 4 — Taxonomie prédéfinie avant corpus (S3)**  
`seed_taxonomy_v2.py` insère 15 domaines / 57 familles / 155 sous-familles définis en dur dans le code Python, sans derivation depuis le corpus réel (mercurials/IMC). C'est l'inverse de la doctrine : le système impose le cadre au réel.

**Verdict 5 — M7 usurpe fondation M6 (S3)**  
M7.2 ajoute des colonnes structurelles (domain_id, family_l2_id, subfamily_id) sur procurement_dict_items. M7.4a ajoute la doctrine identité (item_uid/item_code/birth_*). Ces deux travaux auraient dû être décidés en M6. M7 a fait le travail de M6.

**Verdict 6 — LLM Phase A 77.9% flagged (S3)**  
La tentative de classification automatique M7.4 Phase A a produit 77.9% de propositions flagged (834/1070). Cause prouvée : le LLM invente des codes L3 inexistants dans la taxonomie DB (qui ne contient que 23 codes L3). La taxonomie L3 est insuffisante pour couvrir le corpus réel de 1484 items.

**Verdict 7 — Repo sale, scripts critiques modifiés non commités (S2)**  
build_dictionary.py, etl_vendors_wave2.py, seed_taxonomy_v2.py sont modifiés mais non commités sur la branche active. Le périmètre exact des modifications n'est pas auditable sans diff.

---

## 6. VERDICT GLOBAL

| Composant | Sévérité | Verdict |
|-----------|----------|---------|
| Freeze Partie XI | S4 | MENSONGE SYSTÈME — table obsolète |
| DB locale | S2 | DÉRIVE ACTIVE — en retard sur head |
| m7_rebuild_t0_purge.py | S4 | DESTRUCTION POTENTIELLE — à interdire |
| Taxonomie prédéfinie | S3 | CORRUPTION D'INVARIANT — imposée avant réel |
| M7 usurpation M6 | S3 | DÉRIVE ACTIVE — périmètre M7 hors mandat |
| LLM Phase A | S3 | ÉCHEC PROUVÉ — taxonomie incompatible corpus |
| Repo scripts modifiés | S2 | DETTE RÉELLE |
| Chaîne alembic | S0 | CONFORME — 1 head unique |
| FKs dict→taxo | S0 | CONFORME — NO ACTION, pas CASCADE |
| item_id déterministe | S0 | CONFORME — SHA256(slug)[:16] |

**PREMIÈRE CORRUPTION CAUSALE IDENTIFIÉE :** M7.2 taxonomy_reset — introduction d'une taxonomie prédéfinie (15 domaines codés en dur) couplée structurellement au registre dictionnaire via FK, alors que la doctrine impose que la taxonomie soit dérivée du corpus réel.

---

*Livrables complets : voir AUDIT_M4_M7_PROBES_RAW.md, AUDIT_M4_M7_INVARIANTS.md, AUDIT_M4_M7_BRANCHES_MALADES.md, AUDIT_M4_M7_DETTES_CHIRURGICALES.md, AUDIT_M4_M7_VERDICT_RECONSTRUCTION.md*
