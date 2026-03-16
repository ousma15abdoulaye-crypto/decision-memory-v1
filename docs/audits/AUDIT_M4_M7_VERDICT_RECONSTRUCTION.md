# AUDIT M4→M7 — VERDICT RECONSTRUCTION

**Date :** 2026-03-08  
**Nature :** Verdicts chirurgicaux par composant + périmètre minimal reconstruction  
**Référence :** DMS V4.1.0 FREEZE DÉFINITIF

---

## 1. CHRONOLOGIE DE LA PREMIÈRE CORRUPTION

### Frise causale prouvée

```
DERNIER POINT SÛR
─────────────────────────────────────────────────────────────────
  Tag v4.1.0-m6-dictionary
  Commit a326329 : feat(m6): dictionary build - 1488 items - 1596 aliases
  Migration m6_dictionary_build appliquée
  → 1488 items depuis mercurials + IMC
  → 1596 aliases terrain
  → dict_proposals créé (file validation humaine)
  → dict_collision_log étendu
  → Source de vérité : couche_b
  → Doctrine respectée : libellés réels M5 → normalisation M6

PREMIER POINT AMBIGU
─────────────────────────────────────────────────────────────────
  DMS_V4.1.0_FREEZE.md Partie XI
  → Annonce M4 head = 039_seed_vendors_mali (ABSENT)
  → Annonce M6 head = 041_procurement_dictionary (ABSENT)
  → La référence censée être le plan directeur est fausse
  → Toute décision appuyée sur ce freeze est construite sur du vide
  Sévérité : S4

PREMIER POINT DE DÉRIVE PROUVÉ
─────────────────────────────────────────────────────────────────
  Migration m7_2_taxonomy_reset (branche feat/m7-2-taxonomy-reset)
  Commit eb09dbf : feat(m7.2): taxonomy L1/L2/L3 enterprise grade
                   · 15 domaines · 57 familles · 155 sous-familles

  → Création taxo_l1_domains, taxo_l2_families, taxo_l3_subfamilies
  → Ajout de 7 colonnes structurelles sur procurement_dict_items
    (domain_id FK taxo_l1, family_l2_id FK taxo_l2, subfamily_id FK taxo_l3,
     taxo_version, taxo_validated, taxo_validated_by, taxo_validated_at)
  → Taxonomie L1/L2/L3 codée en dur dans seed_taxonomy_v2.py
    (15 domaines inventés, pas dérivés du corpus)
  Sévérité : S3

PREMIER POINT DE CORRUPTION D'INVARIANT
─────────────────────────────────────────────────────────────────
  Même migration : m7_2_taxonomy_reset
  Invariant G violé : taxonomie = socle imposé avant réel
    → L1/L2/L3 prédéfinis avant que le corpus soit classifié
    → Doctrine freeze : "le système s'adapte au réel"
    → Réalité : "le système impose son cadre au réel"
  Résultat prouvé : Phase A LLM → 77.9% flagged
    (le LLM invente des codes L3 inexistants car la taxonomie est insuffisante)

PREMIER POINT OÙ L'ON A CESSÉ DE PARTIR DU RÉEL
─────────────────────────────────────────────────────────────────
  seed_taxonomy_v2.py (exécuté après m7_2)
  → Structure L1/L2/L3 définie a priori en Python
  → Insertion AVANT classification du corpus réel
  → La taxonomie précède les données qu'elle doit classifier
  Ce n'est pas une dérive : c'est l'inversion complète de la doctrine.

PREMIER POINT OÙ M7 FAIT LE TRAVAIL DE M6
─────────────────────────────────────────────────────────────────
  Migration m7_4a_item_identity_doctrine
  → Doctrine identité item (item_uid, item_code, birth_*)
  → Ce travail de fondation aurait dû être décidé avant la création
    du premier item (M6), pas après que 1489 items existent
  → Backfill partial : seeds seulement (51 items)
  → 1438 items terrain sans ancre technique item_uid/item_code

PREMIER POINT OÙ L'IDENTITÉ EST CONTAMINÉE PAR LA CLASSIFICATION
─────────────────────────────────────────────────────────────────
  Migration m7_4a_item_identity_doctrine
  → birth_domain_id, birth_family_l2_id, birth_subfamily_id
  → L'identité "de naissance" est dérivée de la classification taxonomique
  → Un item dont la taxonomie est absente (1438 items terrain)
    a une identité de naissance incomplète (birth_* = NULL)
  → La doctrine prétend séparer identité et classification,
    mais les colonnes birth_* font dépendre l'identité permanente
    d'une classification préalable
```

---

## 2. AUTOPSIE DES MIGRATIONS M4→M7

| Migration | Objectif affiché | Tables créées/modifiées | Delete rules | Test invariant présent | Verdict |
|-----------|-----------------|------------------------|--------------|------------------------|---------|
| `m6_dictionary_build` | Extension schéma couche_b M6 | procurement_dict_items (+8 col), dict_proposals (CREATE), dict_collision_log (+4 col), vues public | dict_proposals→items : RESTRICT | OUI — fail-loud : items≥51, aliases≥157, slugs complets | **Migration canonique** |
| `m7_2_taxonomy_reset` | Taxonomie L1/L2/L3 | taxo_l1/l2/l3 (CREATE), taxo_proposals_v2 (CREATE), procurement_dict_items (+7 col FK taxo) | taxo_l2→l1 : RESTRICT, taxo_l3→l2 : RESTRICT, items→taxo : NO ACTION | OUI — vérifie présence colonnes | **Migration dérivante** — introduit taxonomie prédéfinie |
| `m7_3_dict_nerve_center` | Nerve center dictionnaire | dict_price_references (CREATE), dict_uom_conversions (CREATE), dgmp_thresholds (CREATE), dict_item_suppliers (CREATE), procurement_dict_items (+9 col), 3 triggers | RESTRICT partout | OUI — vérifie colonnes + triggers | **Migration dérivante** — infrastructure lourde, couplage quality↔taxo |
| `m7_3b_deprecate_legacy_families` | Dépréciation family_id | procurement_dict_items (DROP NOT NULL family_id), procurement_dict_families (+col deprecated), triggers blocage | — | OUI | **Migration canonique** — clôture dette, ADR-0016 |
| `m7_4_dict_vivant` | Dict vivant, quality O(1) | procurement_dict_items (+updated_at, quality_score→SMALLINT), taxo_proposals_v2 (+8 col), vue dict_classification_metrics | — | OUI | **Migration canonique** — corrige dette trigger M7.3 |
| `m7_4a_item_identity_doctrine` | Doctrine identité item_uid/item_code | procurement_dict_items (+9 col identité), contraintes UNIQUE, index, backfill seeds | — | OUI — vérifie colonnes + seeds=51 | **Migration dérivante** — doctrine introduite trop tard, coverage partielle |

---

## 3. VERDICT PAR COMPOSANT

### vendors M4

```
Objet :         Tables vendors, vendor_identities, vendor_activity_badge
Invariant :     Fournisseurs réels de terrain, doublons flaggés pour review humaine
Preuve brute :  661 fournisseurs wave2 importés. ETL etl_vendors_wave2.py.
                Migrations m4_patch_a_vendor_structure, 041_vendor_identities,
                042_vendor_fixes, 043_vendor_activity_badge.
Écart freeze :  Aucun. Structure conforme.
Sévérité :      S0
Verdict :       À CONSERVER
```

---

### mercuriale ingest M5

```
Objet :         Tables mercuriale_sources, mercurials
Invariant :     Ingestion brute M5. Pas de normalisation pendant l'import.
Preuve brute :  040_mercuriale_ingest.py. import_mercuriale.py = parse brut.
                12285 lignes Mali 2023+2024. 15111 lignes 2026. 100% geo.
                raw_label conservé intact.
Écart freeze :  M5 brut confirmé. Normalisation dans M6 (build_dictionary).
Sévérité :      S0
Verdict :       À CONSERVER
```

---

### dictionary build M6

```
Objet :         couche_b.procurement_dict_items, procurement_dict_aliases
Invariant :     Dictionnaire construit depuis libellés réels M5.
Preuve brute :  1488 items + 1596 aliases (tag v4.1.0-m6-dictionary).
                build_dictionary.py lit mercurials + imc_entries.
                item_id = SHA256(slug)[:16] déterministe.
Écart freeze :  CONFORME — M6 construit depuis libellés réels.
Sévérité :      S0
Risque :        build_dictionary.py modifié non commité — AUDITER avant merge.
Verdict :       À CONSERVER
```

---

### dict enrichment M7 (baseline)

```
Objet :         Colonnes M7.2-M7.4a sur procurement_dict_items
Invariant :     M7 enrichit M6, ne refonde pas.
Preuve brute :  23 colonnes ajoutées sur procurement_dict_items par M7.
                Fondation dictionnaire dépendante de M7 pour fonctionner.
Écart freeze :  M7 a fait le travail de fondation de M6.
Sévérité :      S3
Verdict :       À FIGER — ne pas ajouter de nouvelles colonnes structurelles
                sans ADR et mandat explicite. Auditer avant toute extension.
```

---

### identité item

```
Objet :         item_id, item_uid, item_code, birth_*
Invariant :     Identité stable, non dépendante de l'ordre ou du LLM.
Preuve brute :  item_id = SHA256(slug)[:16] — STABLE. Non dépendant.
                item_uid/item_code = NULL sur 1438 items terrain.
                birth_* = NULL sur tous les items terrain (non human_validated).
Écart freeze :  Doctrine identité introduite en M7.4a, trop tard.
Sévérité :      S2 pour item_uid/item_code. S0 pour item_id.
Verdict :       item_id → À CONSERVER (canonique)
                item_uid/item_code → À REBÂTIR DEPUIS LE RÉEL
                (ADR requis : ancre item = item_id ou item_uid ou les deux)
```

---

### alias

```
Objet :         couche_b.procurement_dict_aliases
Invariant :     Alias = mémoire variation terrain réelle.
Preuve brute :  1596 aliases construits depuis libellés mercurials/IMC.
                UNIQUE normalized_alias. FK item_id.
Écart freeze :  CONFORME.
Sévérité :      S0
Verdict :       À CONSERVER
```

---

### collisions

```
Objet :         public.dict_collision_log, RÈGLE-26/27
Invariant :     Toute fusion auto loggée. 3 conditions obligatoires.
Preuve brute :  collision_log = 0 entrées. 1573 libellés traités par build.
                Preuve RÈGLE-26/27 = ABSENTE.
Écart freeze :  Impossible de prouver que les fusions sont tracées.
Sévérité :      S2
Verdict :       À FIGER — auditer logique build_dictionary sur collision
                avant toute réactivation du build en production.
```

---

### proposals

```
Objet :         couche_b.dict_proposals
Invariant :     File validation humaine pour items basse confiance.
Preuve brute :  1439 proposals pending. Format conforme (status IN pending/approved/rejected).
                FK item_id ON DELETE RESTRICT.
Écart freeze :  CONFORME.
Sévérité :      S0
Verdict :       À CONSERVER — file humaine opérationnelle.
```

---

### taxonomie L1/L2/L3

```
Objet :         taxo_l1_domains, taxo_l2_families, taxo_l3_subfamilies
Invariant :     Taxonomie dérivée du corpus, pas imposée a priori.
Preuve brute :  15 domaines codés en dur dans seed_taxonomy_v2.py.
                taxo_l3_subfamilies = 23 en base (≠ 155 annoncés).
                Phase A : 77.9% flagged — LLM invente codes L3 inexistants.
Écart freeze :  Doctrine inversée. Taxonomie précède le corpus.
Sévérité :      S3
Verdict :       À DÉPRÉCIER comme socle imposé.
                Les tables sont conservées (données intactes).
                Le principe de construction est à rejeter.
                Reconstruction : taxonomie par induction depuis corpus réel.
```

---

### scripts purge

```
Objet :         scripts/m7_rebuild_t0_purge.py
Invariant :     Tout script borné à son rôle, avec garde-fou.
Preuve brute :  TRUNCATE taxo_proposals_v2 + DELETE taxo L1/L2/L3
                + UPDATE domain_id=NULL sur 1489 items.
                Aucun --dry-run. Aucune confirmation interactive.
                Seule "garde" = vérification post-purge (trop tard).
Écart freeze :  Contraire à "les imperfections sont tracées, pas cachées."
                Contraire à "tout objet legacy encore alimenté = fuite active."
Sévérité :      S4
Verdict :       À INTERDIRE IMMÉDIATEMENT
```

---

### FKs dictionnaire

```
Objet :         FK procurement_dict_items → taxo (domain_id, family_l2_id, subfamily_id)
Invariant :     FKs protègent le registre, aucun CASCADE toxique.
Preuve brute :  ON DELETE non spécifié = NO ACTION. Pas de CASCADE.
                FK dict_proposals, dict_price_references → items : RESTRICT.
Écart freeze :  CONFORME.
Sévérité :      S0
Verdict :       À CONSERVER
```

---

### migrations M4→M7

```
Objet :         Chaîne alembic m4_patch_a_vendor_structure → m7_4a_item_identity_doctrine
Invariant :     Chaîne linéaire, 1 head, pas de bifurcation.
Preuve brute :  alembic heads = 1 ligne. down_revision vérifiés. Chaîne linéaire.
                m7_4a non appliqué local. Railway non prouvé.
Écart freeze :  Noms conventions non conformes (m4_patch_a vs 04x_).
Sévérité :      S0 pour la chaîne. S2 pour non-application locale.
Verdict :       À FIGER — chaîne en place, ne pas modifier.
                Appliquer m7_4a en local. Vérifier Railway.
```

---

### branches M4→M7

```
Objet :         feat/m4-*, feat/m5-*, feat/m6-*, feat/m7-*
Invariant :     Branches bornées à leur milestone.
Preuve brute :  8 saines, 3 suspectes (m7-2, m7-3, m7-rebuild).
Écart freeze :  Branches suspectes toutes mergées sur main. Irréversible.
Sévérité :      S1 pour les branches mergées (irréversibles).
                S2 pour feat/m7-rebuild-dict-from-terrain (active, sale).
Verdict :       Branches mergées → À FIGER (irréversibles, dette documentée).
                feat/m7-rebuild-dict-from-terrain → NETTOYER avant merge.
```

---

## 4. PÉRIMÈTRE MINIMAL RECONSTRUCTION CANONIQUE

### Segment à conserver intégralement

```
vendors (M4)
  → tables : vendors, vendor_identities
  → scripts : etl_vendors_m4.py, etl_vendors_wave2.py (version committée)
  → migrations : 041_vendor_identities, 042_vendor_fixes, 043_vendor_activity_badge, m4_patch_a_*

mercuriale ingest (M5)
  → tables : mercuriale_sources, mercurials
  → scripts : import_mercuriale.py, import_imc.py
  → migrations : 040_mercuriale_ingest, m5_*

dictionnaire M6 (tables uniquement)
  → tables : procurement_dict_items, procurement_dict_aliases, dict_proposals, dict_collision_log
  → scripts : build_dictionary.py (version committée — diff requis sur version modifiée)
  → migrations : m6_dictionary_build

proposals (file validation humaine)
  → 1439 proposals pending — conserver
  → dict_proposals : À CONSERVER

FKs NO ACTION
  → Protègent sans détruire
  → À CONSERVER
```

### Segment à figer (ne pas étendre, ne pas modifier)

```
Migrations M7.2 → M7.4a
  → Chaîne en place, appliquer m7_4a local
  → Interdire nouvelles migrations sans ADR

Colonnes M7 sur procurement_dict_items
  → domain_id, family_l2_id, subfamily_id, taxo_version, taxo_validated (M7.2)
  → item_type, default_uom, quality_score, last_hash, classification_* (M7.3)
  → item_uid, item_code, birth_*, id_version, llm_*_raw (M7.4a)
  → Figer en l'état. Ne pas retirer (risque). Ne pas étendre sans mandat.

classify_taxonomy_v2.py
  → Script malade (77.9% flagged). Figer. Ne pas réexécuter sans révision taxo.

seed_taxonomy_v2.py
  → Modifier le contenu = interdire sans ADR validé.
```

### Segment à reconstruire si décision humaine

```
Taxonomie L1/L2/L3
  → Principe : reconstruire par induction depuis le corpus réel
    (clustering libellés mercurials + IMC → familles émergentes)
  → Pas de structure a priori
  → Tables conservées — contenu à remplacer

Doctrine identité item
  → Si rebâtir item_uid/item_code : backfill complet sur tous les 1490 items
  → ADR avant backfill (format, génération, immuabilité)
  → item_id (SHA256) reste l'ancre pérenne en attendant

Dictionnaire (si décision de purge)
  → Séquence : mercurials + IMC → build_dictionary → procurement_dict_items
  → Zéro dépendance taxonomique pour l'existence de l'item
  → Taxonomie = table de mapping séparée, pas colonne FK sur dict_items
```

### Segment à interdire immédiatement

```
m7_rebuild_t0_purge.py
  → Interdire sans dry-run + confirmation + backup vérifié
  → ADR "mandat purge M7" requis
```

---

## 5. ORDRE D'OUVERTURE DES MANDATS SUIVANTS

| Ordre | Mandat | Condition d'ouverture |
|-------|--------|----------------------|
| 1 | **Interdiction m7_rebuild_t0_purge.py** | Immédiat — sans condition |
| 2 | **Probe Railway** (alembic current + counts) | Accès DATABASE_URL Railway |
| 3 | **Diff scripts modifiés** (build_dictionary, etl_vendors_wave2, seed_taxonomy_v2) | Accès git diff HEAD |
| 4 | **Mise à jour table freeze** (Partie XI → table vérité réelle) | Après probe Railway |
| 5 | **ADR séparation identité/registre/taxonomie** | Après freeze mis à jour |
| 6 | **ADR taxonomie dérivée vs imposée** | Après ADR identité |
| 7 | **Mandat dépréciation** colonnes M7 structurelles | Après ADR taxonomie |
| 8 | **Mandat reconstruction** (si décision) | Après ADR + dépréciation |

---

## 6. CONDITIONS DONE — AUDIT

| Condition | Statut |
|-----------|--------|
| Tous probes bruts postés | **OUI** — voir AUDIT_M4_M7_PROBES_RAW.md |
| Table freeze↔repo↔local↔Railway existe | **OUI** (Railway = NON PROUVÉ documenté) |
| Chaque branche M4→M7 classée | **OUI** — 8 saines, 3 suspectes — voir BRANCHES_MALADES |
| Chaque migration M4→M7 classée | **OUI** — 6 migrations classées (2 canoniques, 2 dérivantes, 2 canoniques) |
| Chaque invariant atomique A→K jugé | **OUI** — voir INVARIANTS |
| Première corruption causale identifiée | **OUI** — M7.2 taxonomy_reset |
| Toutes dettes M4→M7 classées | **OUI** — 17 dettes, voir DETTES_CHIRURGICALES |
| Tous composants ont verdict chirurgical | **OUI** — 13 composants, voir section 3 |
| Aucune ligne de code écrite | **OUI** |
| Aucune DB modifiée | **OUI** |

**VERDICT FINAL : AUDIT DONE.**

---

## 7. PHRASE FINALE DE CLÔTURE

La première corruption causale de la chaîne M4→M7 est prouvée et localisée :

**M7.2 taxonomy_reset** — introduction d'une taxonomie prédéfinie et imposée (15 domaines, 57 familles, 155 sous-familles codés en dur) sur un registre dictionnaire de 1488 items déjà construits depuis le réel, via des colonnes FK structurelles ajoutées sur la table cœur de M6.

Ce point est la première fois que le système a cessé de partir du réel pour imposer son cadre au réel.

Tout ce qui suit (M7.3 nerve center, M7.4 vivant, M7.4a identité) est construit sur cette fondation dérivante.

M6 reste le dernier point sûr.
