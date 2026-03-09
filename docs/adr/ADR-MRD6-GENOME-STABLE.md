# ADR-MRD6-GENOME-STABLE
# Genome stable DMS — Taxonomie + Creation + Collision
# Date     : 2026-03-09
# Decideur : AO — Abdoulaye Ousmane
# Statut   : ACCEPTE — FREEZE

## Contexte

MRD-5 a livre l'identite technique complete.
Trois briques manquent pour rendre le registre
utilisable par Couche A sans risque LLM.

Schema reel note :
  label_fr = colonne label reelle (pas label)
  item_id  = cle primaire (pas item_uid)
  dict_collision_log existe deja dans public (schema V4)
  taxo_version deja presente en DB

## Decisions

### BRIQUE-1 — Taxonomie derivee corpus reel
  Construite APRES registre — INV-07 + REGLE-29
  L1/L2/L3 depuis frequences reelles corpus 1490 items
  Coverage gate cible : >= 85%
  Coverage obtenu : 85.2% (1269/1490)
  taxo_version = '1.0' — versionnee
  Source : docs/data/MRD6_TAXONOMY_V1.md

### BRIQUE-2 — Stabilite semantique
  label_status : draft | validated | deprecated
  label_fr immuable si label_status = validated
  fn_protect_item_identity etendu a label_status
  Correction label validated -> creer alias, pas UPDATE
  Changement semantique -> deprecier + nouvel item
  Colonnes taxo_l1/l2/l3 creees (taxo_version deja presente)

### BRIQUE-3 — Collisions conceptuelles
  dict_collision_log existe en public (schema V4) — ne pas recreer
  Trigger append-only ajoute sur table existante
  Detection : rapidfuzz token_sort_ratio — seuil 85
  Resolution : humain uniquement — jamais auto

### M7 recadre
  M7 PEUT : proposer draft, detecter collision,
            enrichir alias, suggerer taxo
  M7 NE PEUT PAS : modifier item_id, fingerprint,
                   item_code, label validated,
                   passer draft -> validated

## Consequences
  Couche A peut interagir avec Couche B sans risque.
  Le LLM ne peut pas reecrire la realite du registre.
  C'est le genome stable qui debloque M8 -> M21.
