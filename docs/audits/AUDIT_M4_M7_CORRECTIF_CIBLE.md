# AUDIT M4→M7 — CORRECTIF CIBLÉ

```
Tu ne refais pas l'audit.
Tu corriges 3 failles critiques de sentence.
Tu travailles en lecture seule.
Tout ce qui n'est pas prouvé est faux.
Tu répares la hiérarchie de vérité, le verdict FK, et la sentence migration par migration.
Tu rends une correction opposable, pas un commentaire.
```

**Date :** 2026-03-08  
**Nature :** Correctif ciblé — 3 failles de sentence — lecture seule  
**Référence :** DMS V4.1.0 FREEZE DÉFINITIF

---

## POINT 1 — FREEZE / HIÉRARCHIE DE VÉRITÉ

```
Objet :
  Freeze Partie XI — DMS V4.1.0_FREEZE.md

Formulation audit actuelle :
  "Freeze Partie XI = MENSONGE SYSTÈME — table obsolète / référence invalide"
  (AUDIT_M4_M7_TRIBUNAL.md, section 6. Verdict global)

Preuve brute invoquée :
  Freeze Partie XI annonce :
    M4 head attendu : "039_seed_vendors_mali"
    M6 head attendu : "041_procurement_dictionary"

  Repo réel (lecture alembic/versions/) :
    039 = "039_hardening_created_at_timestamptz" (M2B)  → 039_seed_vendors_mali ABSENT
    041 = "041_vendor_identities" (M4)                  → 041_procurement_dictionary ABSENT

Analyse :
  La preuve démontre que les migrations annoncées dans le freeze ne correspondent
  pas aux fichiers créés dans le repo.

  Deux interprétations possibles :
    (A) Le freeze est invalide → c'est ce que l'audit initial a conclu.
    (B) Le repo a divergé du freeze → le freeze reste le plan canonique, non exécuté.

  La doctrine DMS impose :
    "DMS V4.1.0 FREEZE DÉFINITIF, plan directeur unique"
    "Référence supérieure"
  Le freeze n'est pas invalidé par la divergence du repo.
  Il n'y a pas eu de patch officiel, d'ADR, ni d'amendement explicite du freeze.
  Le freeze n'a pas été remplacé.

  Conclusion prouvée :
    Le freeze est non-nul, non amendé, non remplacé.
    Le repo a produit des migrations sous des noms différents de ceux du freeze.
    C'est une DÉRIVE REPO vis-à-vis du freeze, pas une invalidation du freeze.

  La formulation "MENSONGE SYSTÈME" appliquée au freeze est doctrinalement fausse.
  Un mensonge système exige que le freeze prétende une vérité et que cette vérité
  soit prouvée fausse. Ce qui est prouvé ici c'est que le repo n'a pas suivi le freeze.
  La vérité que le freeze exprimait (intention des migrations M4 et M6) n'a jamais
  été implémentée — ce n'est pas un mensonge, c'est une non-exécution.

Verdict corrigé :
  DÉRIVE REPO CONFIRMÉE — le repo a divergé du freeze avant M4 sans amendement
  officiel du freeze.
  Le freeze Partie XI est une prévision non réalisée.
  Il reste canon supérieur jusqu'à amendement explicite par ADR ou patch officiel.
  La table de vérité correcte est : REPO NON CONFORME AU FREEZE.
  Corriger l'audit : remplacer "MENSONGE SYSTÈME" par "DÉRIVE REPO vs FREEZE".

Sévérité :
  S4 — maintenu.
  Non parce que le freeze ment, mais parce que l'absence d'alignement repo/freeze
  signifie que toute décision de reconstruction appuyée sur les noms de migration
  du freeze utilisera des références inexistantes dans le repo.
  Le risque est identique. La formulation seule change.

Impact sur la sentence globale :
  La sentence reste : la reconstruction requiert de corriger la table de vérité freeze.
  L'action reste : reconstruire la table freeze↔repo avec les vrais noms de migration.
  Seule la qualification change : le freeze n'est pas menteur, le repo n'est pas conforme.
```

---

## POINT 2 — FK / DELETE RULES

```
Objet :
  FKs / delete rules — dictionnaire ↔ taxonomie ↔ tables satellites

Preuve brute (lecture migrations — sources exactes) :

  [021_m_normalisation_items_tables.py — création originale]
    procurement_dict_items.family_id
      → couche_b.procurement_dict_families(family_id)
      ON DELETE RESTRICT

    procurement_dict_items.default_unit
      → couche_b.procurement_dict_units(unit_id)
      ON DELETE RESTRICT

    procurement_dict_aliases.item_id
      → couche_b.procurement_dict_items(item_id)
      ON DELETE CASCADE     ← NON IDENTIFIÉE DANS L'AUDIT INITIAL

  [024_mercuriale_raw_queue.py]
    couche_b.mercuriale_raw_queue.item_id
      → couche_b.procurement_dict_items(item_id)
      ON DELETE SET NULL

  [m6_dictionary_build.py — dict_proposals]
    couche_b.dict_proposals.item_id
      → couche_b.procurement_dict_items(item_id)
      ON DELETE RESTRICT

  [m7_2_taxonomy_reset.py — dict_items vers taxo]
    procurement_dict_items.domain_id
      → couche_b.taxo_l1_domains(domain_id)
      [AUCUN ON DELETE SPÉCIFIÉ → PostgreSQL défaut = NO ACTION]

    procurement_dict_items.family_l2_id
      → couche_b.taxo_l2_families(family_l2_id)
      [AUCUN ON DELETE SPÉCIFIÉ → NO ACTION]

    procurement_dict_items.subfamily_id
      → couche_b.taxo_l3_subfamilies(subfamily_id)
      [AUCUN ON DELETE SPÉCIFIÉ → NO ACTION]

  [m7_2_taxonomy_reset.py — taxo interne]
    couche_b.taxo_l2_families.domain_id
      → couche_b.taxo_l1_domains(domain_id)
      ON DELETE RESTRICT

    couche_b.taxo_l3_subfamilies.family_l2_id
      → couche_b.taxo_l2_families(family_l2_id)
      ON DELETE RESTRICT

  [m7_2_taxonomy_reset.py — taxo_proposals_v2]
    couche_b.taxo_proposals_v2.item_id
      → couche_b.procurement_dict_items(item_id)
      ON DELETE RESTRICT

    couche_b.taxo_proposals_v2.domain_id
      → couche_b.taxo_l1_domains(domain_id)
      ON DELETE RESTRICT

    couche_b.taxo_proposals_v2.family_l2_id
      → couche_b.taxo_l2_families(family_l2_id)
      ON DELETE RESTRICT

    couche_b.taxo_proposals_v2.subfamily_id
      → couche_b.taxo_l3_subfamilies(subfamily_id)
      ON DELETE RESTRICT

  [m7_3_dict_nerve_center.py]
    couche_b.dict_price_references.item_id
      → couche_b.procurement_dict_items(item_id)
      ON DELETE RESTRICT

    couche_b.dict_price_references.uom_id
      → couche_b.procurement_dict_units(unit_id)
      ON DELETE RESTRICT

    couche_b.dict_uom_conversions.from_unit_id
      → couche_b.procurement_dict_units(unit_id)
      ON DELETE RESTRICT

    couche_b.dict_uom_conversions.to_unit_id
      → couche_b.procurement_dict_units(unit_id)
      ON DELETE RESTRICT

    couche_b.dict_item_suppliers.item_id (ligne 131-132)
      → couche_b.procurement_dict_items(item_id)
      ON DELETE RESTRICT

FK saines :
  1. dict_proposals.item_id → dict_items : RESTRICT
     Protège les items contre suppression si proposals existent.
     Sens : satellite dépend du registre. Correct.

  2. taxo_proposals_v2.item_id → dict_items : RESTRICT
     Idem. Correct.

  3. dict_price_references.item_id → dict_items : RESTRICT
     Idem. Correct.

  4. dict_item_suppliers.item_id → dict_items : RESTRICT
     Idem. Correct.

  5. taxo_l2_families.domain_id → taxo_l1 : RESTRICT
     Protège la hiérarchie taxonomique interne. Correct.

  6. taxo_l3_subfamilies.family_l2_id → taxo_l2 : RESTRICT
     Idem. Correct.

  7. dict_items.family_id → dict_families : RESTRICT (LEGACY — deprecated M7.3b)
     Bloque suppression d'une famille si des items la référencent.
     Correct même si legacy.

  8. dict_items.default_unit → dict_units : RESTRICT
     Protège les unités. Correct.

  9. mercuriale_raw_queue.item_id → dict_items : SET NULL
     Si un item est supprimé, la queue est orphelinée (item_id=NULL) mais pas détruite.
     Comportement acceptable — pas de perte de données.

FK ambiguës :
  1. procurement_dict_items.domain_id → taxo_l1_domains : NO ACTION
     NO ACTION = DELETE taxo_l1 ÉCHOUE si items le référencent.
     MAIS : m7_rebuild_t0_purge.py exécute d'abord
       UPDATE procurement_dict_items SET domain_id=NULL
     puis DELETE FROM taxo_l1_domains.
     Ce pattern CONTOURNE la protection NO ACTION.
     La FK ne protège pas contre UPDATE NULL précédant le DELETE.
     Verdict ambiguë : protège contre DELETE direct, contournable par script.

  2. procurement_dict_items.family_l2_id → taxo_l2_families : NO ACTION
     Même analyse. Même contournement prouvé (m7_rebuild_t0_purge.py).

  3. procurement_dict_items.subfamily_id → taxo_l3_subfamilies : NO ACTION
     Idem.

  4. taxo_proposals_v2.domain_id/family_l2_id/subfamily_id → taxo : RESTRICT
     taxo_proposals_v2 RESTREINT la suppression de taxo si des proposals existent.
     MAIS m7_rebuild_t0_purge.py exécute TRUNCATE taxo_proposals_v2 en T0-A
     avant DELETE taxo. Ce pattern contourne aussi le RESTRICT.
     Verdict : FK RESTRICT sur proposals = protège le chemin normal,
               contournable par la séquence TRUNCATE + DELETE du script purge.

FK toxiques :
  1. procurement_dict_aliases.item_id → procurement_dict_items(item_id) : ON DELETE CASCADE
     SOURCE : 021_m_normalisation_items_tables.py, ligne 63-64
     PREUVE BRUTE :
       "item_id TEXT NOT NULL REFERENCES couche_b.procurement_dict_items(item_id)
        ON DELETE CASCADE"
     EFFET : si un item est supprimé (DELETE FROM procurement_dict_items),
             TOUS ses aliases sont supprimés automatiquement et silencieusement.
     CONTEXTE : 1596 aliases prouvés en base. Résultat de mois de terrain M5→M6.
     DANGER : un futur script de "rebuild" qui DELETE + re-INSERT les items
              entraînerait la perte totale irréversible des 1596 aliases terrain.
     L'audit initial a classé "FKs dictionnaire → À CONSERVER" sans identifier
     cette cascade. Ce verdict est insuffisant.

  2. Couplage structurel par contournement (NO ACTION + UPDATE NULL)
     Les 3 FK NO ACTION (domain_id, family_l2_id, subfamily_id) ne sont pas
     des cascades formelles, mais le pattern UPDATE NULL + DELETE prouvé dans
     m7_rebuild_t0_purge.py constitue une destruction de classification
     fonctionnellement équivalente à une cascade sur 1489 items.
     Ce n'est pas une FK toxique au sens formel, mais un PATTERN DESTRUCTIF
     prouvé dans le codebase.

Verdict corrigé :
  Le verdict global "FKs dictionnaire → À CONSERVER" est insuffisant.
  Verdict corrigé par classe :

  Class A — À CONSERVER sans réserve :
    dict_proposals, taxo_proposals_v2, dict_price_references, dict_item_suppliers
    → dict_items : RESTRICT. Saines.

  Class B — AMBIGUËS À RE-PROBER :
    dict_items.domain_id/family_l2_id/subfamily_id → taxo : NO ACTION
    Protège contre DELETE direct.
    Non protège contre le pattern UPDATE NULL + DELETE.
    Verdict : conserver les FK, INTERDIRE le pattern UPDATE NULL + DELETE
    sans mandat explicite et backup vérifié.

  Class C — TOXIQUE IDENTIFIÉE :
    procurement_dict_aliases.item_id → dict_items : ON DELETE CASCADE
    Cette FK était absente de l'audit initial. Elle constitue une bombe à
    retardement : tout script qui supprime des items détruit les aliases.
    Verdict : à traiter en priorité par ADR.
    Action : ajouter une guard dans tout script qui touche DELETE sur dict_items.
    L'alias doit survivre à un DELETE item si le modèle de reconstruction
    est "supprimer + recréer les items depuis le réel".

Sévérité :
  S3 pour la FK CASCADE aliases : dérive active — non identifiée, risque prouvé
  S2 pour les FK NO ACTION contournables : dette réelle contenue

Impact sur reconstruction :
  Tout mandat de "rebuild depuis le réel" qui passe par DELETE + INSERT sur
  procurement_dict_items DÉTRUIRA SILENCIEUSEMENT les 1596 aliases terrain.
  La reconstruction propre doit interdire DELETE sur dict_items.
  Si purge nécessaire : UPDATE active=FALSE, jamais DELETE.
```

---

## POINT 3 — VERDICT MIGRATION PAR MIGRATION

---

```
Objet :
  m6_dictionary_build

But affiché :
  Extension schéma couche_b existant. Ajouter colonnes M6 sur procurement_dict_items.
  Créer dict_proposals (file validation humaine). Étendre dict_collision_log.
  Recréer vues public.dict_items / public.dict_aliases.

Effet réel prouvé :
  + 8 colonnes sur procurement_dict_items :
    canonical_slug (TEXT), dict_version (TEXT DEFAULT '1.0.0'),
    confidence_score (NUMERIC(5,4) DEFAULT 0.5), human_validated (BOOL DEFAULT FALSE),
    validated_by (TEXT), validated_at (TIMESTAMPTZ),
    sources (JSONB DEFAULT '[]'), last_seen (DATE), updated_at (TIMESTAMPTZ)
  + canonical_slug peuplé depuis item_id (slug → slug, déterministe)
  + confidence_score = 0.9 + human_validated = TRUE pour les 51 seeds
  + Index trgm sur normalized_alias et canonical_slug (fuzzy matching)
  + CREATE TABLE couche_b.dict_proposals (item_id FK ON DELETE RESTRICT)
  + Colonnes M6 sur public.dict_collision_log :
    collision_type, item_a_id, item_b_id, alias_conflicted
  + Vues public.dict_items et public.dict_aliases recréées
  Vérification fail-loud : items ≥ 51, aliases ≥ 157, slugs complets.
  Prouvé : tag v4.1.0-m6-dictionary, 1488 items, 1596 aliases.

Écart au freeze :
  AUCUN. M6 = construction canonique depuis libellés réels M5.
  Séquence respectée : ingestion brute M5 → normalisation M6.
  Provenance tracée : sources JSONB.
  item_id déterministe : SHA256(slug)[:16].

Sévérité :
  S0

Verdict :
  À CONSERVER

Conséquence CTO :
  Aucune action requise sur la migration elle-même.
  build_dictionary.py (modifié non commité) doit être audité (diff)
  avant toute réutilisation en prod.
```

---

```
Objet :
  m7_2_taxonomy_reset

But affiché :
  Créer hiérarchie taxonomique L1/L2/L3 enterprise grade.
  Ajouter colonnes domain_id/family_l2_id/subfamily_id sur procurement_dict_items.

Effet réel prouvé :
  + CREATE TABLE couche_b.taxo_l1_domains (15 domaines via seed)
  + CREATE TABLE couche_b.taxo_l2_families (FK→taxo_l1 ON DELETE RESTRICT)
  + CREATE TABLE couche_b.taxo_l3_subfamilies (FK→taxo_l2 ON DELETE RESTRICT)
  + CREATE TABLE couche_b.taxo_proposals_v2 (FK→dict_items ON DELETE RESTRICT,
    FK→taxo L1/L2/L3 ON DELETE RESTRICT)
  + 7 colonnes ajoutées sur procurement_dict_items :
    domain_id (FK→taxo_l1 NO ACTION), family_l2_id (FK→taxo_l2 NO ACTION),
    subfamily_id (FK→taxo_l3 NO ACTION), taxo_version, taxo_validated,
    taxo_validated_by, taxo_validated_at
  Probe : 1489 items, 0 avec domain_id au moment de la probe.
  Probe : taxo_l3_subfamilies = 23 en base (seed annonce 155 — divergence prouvée).
  Phase A classification : 77.9% flagged (LLM invente codes L3 inexistants).

Écart au freeze :
  La doctrine impose : "le système s'adapte au réel".
  Cette migration impose le contraire : structure taxonomique codée en dur
  dans seed_taxonomy_v2.py AVANT classification du corpus réel.
  Les 15 domaines, 57 familles, 155 sous-familles sont définis a priori,
  pas dérivés des libellés mercurials/IMC.
  M7 = enrichissement selon le freeze. Cette migration introduit de la fondation
  structurelle (colonnes FK sur la table cœur M6) depuis une branche M7.

Sévérité :
  S3 — dérive active

Verdict :
  À FIGER
  La migration est appliquée et irréversible sans rebuild complet.
  Interdire toute nouvelle colonne FK taxonomique sur procurement_dict_items
  sans ADR et mandat explicite.
  Interdire seed_taxonomy_v2.py sans révision de la doctrine taxo-dérivée.

Conséquence CTO :
  Ouvrir ADR "taxonomie dérivée vs imposée" avant tout rebuild ou extension.
  Aucune nouvelle table taxo, aucune nouvelle FK taxo→dict sans cet ADR.
```

---

```
Objet :
  m7_3_dict_nerve_center

But affiché :
  Dict nerve center. Alignement B2-A audit_log canon.
  Colonnes enrichissement sur dict_items. Triggers hash + audit + quality.

Effet réel prouvé :
  + CREATE TABLE couche_b.dict_price_references (FK→dict_items RESTRICT, FK→units RESTRICT)
  + CREATE TABLE couche_b.dict_uom_conversions (FK→units RESTRICT × 2)
  + CREATE TABLE couche_b.dgmp_thresholds (standalone)
  + CREATE TABLE couche_b.dict_item_suppliers (FK→dict_items RESTRICT)
  + 9 colonnes ajoutées sur procurement_dict_items :
    item_type, default_uom, default_currency, unspsc_code,
    classification_confidence, classification_source, needs_review,
    quality_score, last_hash
  + Trigger fn_dict_compute_hash : BEFORE UPDATE → SHA256 → last_hash
  + Trigger fn_dict_write_audit : AFTER UPDATE → INSERT audit_log
  + Trigger fn_compute_quality_score : BEFORE INSERT OR UPDATE
    (version initiale avec sous-requête — dette comblée en M7.4)
  + Advisory lock sur dict_items (correction PR#169)
  Probe probe_post.txt : 6 triggers actifs sur procurement_dict_items confirmés.
  Trigger quality_score : domain_id non null → +30 pts (couplage taxo→qualité prouvé).

Écart au freeze :
  M7 = enrichissement. Cette migration crée 4 tables d'infrastructure métier,
  9 colonnes structurelles, 3 triggers sur la table cœur — c'est de la fondation.
  Le couplage quality_score ↔ domain_id (colonne taxonomique) dans le trigger
  signifie que la "qualité" d'un item dépend de sa classification taxonomique.
  Items sans taxo = qualité dégradée de 30 points par construction.

Sévérité :
  S3 — dérive active (infrastructure fondation introduite en M7)
  S2 — dette contenue (trigger quality patché en O(1) en M7.4)

Verdict :
  À FIGER
  Infrastructure en place. Ne pas étendre sans ADR.
  Interdire nouvelles tables ou colonnes structurelles via branches M7.
  Le couplage quality_score↔taxonomie doit être documenté comme dette.

Conséquence CTO :
  ADR "périmètre M6 vs M7 schéma" pour décider quelles colonnes M7.3
  appartiennent à la fondation M6.
  Interdire nouvelle colonne sur procurement_dict_items sans ce cadre.
```

---

```
Objet :
  m7_3b_deprecate_legacy_families

But affiché :
  Dépréciation family_id (colonne M6 legacy).
  ADR-0016. Bloquer les nouvelles écritures sur family_id.

Effet réel prouvé :
  + ALTER TABLE procurement_dict_items DROP NOT NULL family_id
    (family_id devient nullable — items M7.2+ sans family_id acceptés)
  + ALTER TABLE procurement_dict_families ADD COLUMN deprecated BOOLEAN DEFAULT TRUE
  + COMMENT ON TABLE procurement_dict_families : 'DEPRECATED M7.3b'
  + COMMENT ON COLUMN procurement_dict_items.family_id : 'LEGACY M6 — READ-ONLY'
  + CREATE FUNCTION couche_b.fn_block_legacy_family_write() : RAISE EXCEPTION
  + Triggers BEFORE INSERT / BEFORE UPDATE bloquant family_id sur nouveaux items
  Probe probe_post.txt : triggers trg_block_legacy_family_insert et
  trg_block_legacy_family_update confirmés actifs.

Écart au freeze :
  AUCUN. Cette migration soldé une dette M6 documentée (ADR-0016).
  Elle ne modifie pas le périmètre fonctionnel du dictionnaire.
  Elle renforce la séparation legacy/M7.2 en bloquant les écritures family_id.

Sévérité :
  S0

Verdict :
  À CONSERVER

Conséquence CTO :
  Aucune action requise.
  La table procurement_dict_families reste en base comme archive historique.
  Aucun nouveau code ne doit écrire family_id.
```

---

```
Objet :
  m7_4_dict_vivant

But affiché :
  Dict vivant. Quality score O(1). Métriques proposals. Vue classification_metrics.

Effet réel prouvé :
  + ALTER TABLE procurement_dict_items ADD COLUMN updated_at (si absent)
  + ALTER TABLE procurement_dict_items quality_score TYPE SMALLINT
    (conversion NUMERIC → SMALLINT 0-100 avec USING)
  + 8 colonnes sur taxo_proposals_v2 :
    token_entropy, confidence_source (CHECK), calibrated_confidence,
    batch_job_id, batch_custom_id, approved_by (FK→users), approved_at,
    reviewed_by (FK→users), updated_at
  + Remplacement fn_compute_quality_score : sous-requête N → O(1) colonnes locales
    guard pg_trigger_depth ajouté (évite récursion)
  + Vue public.dict_classification_metrics
  Probe probe_post.txt P0B_TRIGGER_GUARD : "pg_trigger_depth guard : OK · O(1) OK"
  Dette trigger M7.3 (N sous-requêtes) : soldée.
  Vérification fail-loud présente.

Écart au freeze :
  AUCUN STRUCTUREL. Cette migration corrige une dette M7.3 (trigger O(1)).
  Elle ajoute des colonnes d'audit sur taxo_proposals_v2 (conformes M7).
  FK approved_by / reviewed_by → users(id) : RÉFÉRENCES non spécifiées
  comme ON DELETE → NO ACTION par défaut. Absence de ON DELETE explicite
  sur des colonnes d'audit est acceptable.

Sévérité :
  S0 pour la correction trigger.
  S1 pour l'absence de ON DELETE explicite sur FK approved_by/reviewed_by.

Verdict :
  À CONSERVER

Conséquence CTO :
  Aucune action bloquante.
  Documenter que quality_score O(1) ne tient pas compte des prix
  (dict_price_references) — ce calcul est déléré à scripts/recompute_quality.py.
```

---

```
Objet :
  m7_4a_item_identity_doctrine

But affiché :
  Doctrine identité items. item_uid (UUIDv7), item_code (ITM.BD.BF.BS.SERIAL.CD),
  birth_* lineage, llm_*_raw audit trail.

Effet réel prouvé :
  + 9 colonnes sur procurement_dict_items :
    item_uid (TEXT UNIQUE), item_code (TEXT UNIQUE),
    birth_domain_id, birth_family_l2_id, birth_subfamily_id,
    id_version (TEXT NOT NULL DEFAULT '1.0'),
    llm_domain_id_raw, llm_family_l2_id_raw, llm_subfamily_id_raw
  + Contraintes UNIQUE uq_dict_items_item_uid et uq_dict_items_item_code
  + Index sur item_uid, item_code, birth_subfamily_id, subfamily_id
  + Backfill birth_domain_id/family_l2_id/subfamily_id :
    WHERE human_validated=TRUE AND domain_id IS NOT NULL AND birth_domain_id IS NULL
    → seeds (51 items) uniquement
    → 1438 items terrain : birth_* = NULL
  Vérification fail-loud : seeds=51. Non appliquée localement (alembic current = m7_4).

Écart au freeze :
  La doctrine identité item (ancre technique immuable) aurait dû être définie
  en M6, avant la création des premiers items. Elle est introduite en M7.4a
  après que 1489 items existent déjà.
  Résultat : item_uid et item_code couvrent 51 items (seeds) mais pas 1438 items
  terrain. L'identité est composite et incomplète.
  De plus, birth_* dépend de domain_id (classification taxonomique) pour les seeds.
  Pour les items terrain, birth_* reste NULL car domain_id = NULL.
  L'identité "de naissance" est donc indexée sur la taxonomie — ce qui contredit
  le principe d'une ancre immuable indépendante de la classification mutable.

Sévérité :
  S2 — dette réelle (couverture partielle)
  S3 — dérive de principe (birth_* dépend de taxonomie mutable)

Verdict :
  À DÉPRÉCIER comme fondation de doctrine identité.
  La migration est appliquée — ses colonnes sont conservées (irréversible sans rebuild).
  La doctrine est non applicable en l'état : couverture partielle + dépendance taxo.
  ADR impératif : définir l'ancre item (item_id SHA256 seul ? item_uid UUIDv7 ?).
  Interdire tout usage de item_uid ou item_code comme clé étrangère dans d'autres
  tables avant que le backfill complet soit prouvé (1490/1490 non NULL).

Conséquence CTO :
  Ne pas construire de nouveaux objets sur item_uid ou item_code comme PK/FK.
  item_id (SHA256 déterministe) reste l'ancre pérenne prouvée.
  Ouvrir ADR "doctrine identité item" avant toute extension.
```

---

## SYNTHÈSE CORRECTIFS

| Point | Verdict initial | Verdict corrigé | Changement |
|-------|-----------------|-----------------|------------|
| Freeze Partie XI | MENSONGE SYSTÈME | DÉRIVE REPO vs FREEZE — le freeze reste canon | Formulation corrigée |
| FK procurement_dict_aliases | À CONSERVER (global) | ON DELETE CASCADE → FK TOXIQUE — aliase détruits si item DELETE | Faille non détectée ajoutée |
| FK NO ACTION domain_id/family_l2_id/subfamily_id | À CONSERVER | AMBIGUËS — contournables par UPDATE NULL + DELETE (pattern prouvé) | Nuance ajoutée |
| m6_dictionary_build | Migration canonique | À CONSERVER | Confirmé |
| m7_2_taxonomy_reset | Migration dérivante | À FIGER | Confirmé avec preuve renforcée |
| m7_3_dict_nerve_center | Migration dérivante | À FIGER | Confirmé |
| m7_3b_deprecate_legacy_families | Migration canonique | À CONSERVER | Confirmé |
| m7_4_dict_vivant | Migration canonique | À CONSERVER | Confirmé |
| m7_4a_item_identity_doctrine | Migration dérivante | À DÉPRÉCIER (doctrine inapplicable) | Verdict durci |

---

## CONDITION DONE

| Condition | Statut |
|-----------|--------|
| Phrase freeze corrigée avec preuve irréfutable | OUI — dérive repo, freeze reste canon |
| FK reclassées en saines / ambiguës / toxiques | OUI — CASCADE aliases = toxique identifiée |
| 6 migrations avec verdict atomique | OUI |
| Fichier unique rédigé | OUI — docs/audits/AUDIT_M4_M7_CORRECTIF_CIBLE.md |
| Aucune autre action entreprise | OUI |
| Aucune ligne de code écrite | OUI |
| Aucune DB modifiée | OUI |

**CORRECTIF DONE.**
