# ADR-MRD5-ITEM-IDENTITY-V1
# Regle d'identite canonique item — Version 1
# Date     : 2026-03-09
# Decideur : AO — Abdoulaye Ousmane
# Statut   : ACCEPTE — FREEZE

## Contexte

MRD-4 a cree fingerprint (sha256) et les triggers de protection.
Ces champs constituent l'identite technique d'un item.
La cle existante item_id (TEXT) est l'identifiant interne.
Il faut un code lisible, tracable, deterministe pour les
rapports, exports et communications terrain.

Note schema reel :
  item_id   = cle primaire TEXT (existante, immuable)
  fingerprint = sha256(normalize(label_fr)|source_type) MRD-4
  item_code = nouveau champ cree dans MRD-5

## Decision

### Champs d'identite — definitions finales

  item_id     : Cle primaire TEXT existante.
                Immuable. Protegee par trg_protect_item_identity.
                Identifiant interne.

  fingerprint : sha256(normalize(label_fr)|source_type).
                Immuable apres initialisation.
                Protegee par trg_protect_item_identity.
                Garantit deduplication UPSERT.

  item_code   : Code lisible genere au backfill.
                Format : {PREFIX}-{YYYYMM}-{SEQ6}
                PREFIX = MC | IC | SD | LG
                YYYYMM = annee+mois de birth_timestamp
                SEQ6   = sequence dans le run, padded 6 digits
                Exemple : LG-202603-000042
                Immuable apres creation.
                Protege par trg_protect_item_identity (etendu MRD-5).

### Regles de generation PREFIX

  MC : birth_source IN ('mercuriale', 'mercuriales')
  IC : birth_source IN ('imc')
  SD : birth_source IN ('seed', 'manual')
  LG : birth_source IN ('legacy', 'unknown', NULL)

  Les 1490 items actuels ont birth_source='unknown'
  -> PREFIX = LG pour ce corpus initial.

### Interdits

  [IS-09] item_code jamais derive d'une taxonomie
  [IS-10] item_code jamais modifiable apres creation
  [IS-11] item_id jamais recalcule
  [IS-12] fingerprint jamais modifiable apres initialisation

## Consequences

  Tout item a un code lisible tracable apres MRD-5.
  Les rapports peuvent referencer item_code.
  La taxonomie (MRD-6) ne conditionne pas item_code.
  item_code est stable independamment de tout changement taxonomique.
