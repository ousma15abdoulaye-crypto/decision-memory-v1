# ADR-0016 — Détour M7.2 / M7.3 et retour M7 réel

**Fichier     :** docs/adrs/ADR-0016_m7-detour-taxonomy-nerve-center.md
**Date        :** 2026
**Statut      :** ACCEPTÉ
**Décideur    :** Abdoulaye Ousmane (CTO)
**Rédigé par  :** Tech Lead / Systems Engineer

---

## Contexte

Le Plan Directeur V4.1.0 (référence FREEZE) définit M7 ainsi :

  M7 = enrichissement contrôlé
       collisions + proposals
       dictionnaire vivant depuis données réelles M5/M6

À l'issue de M6, le dictionnaire contenait :
  · 1 488 items ingérés depuis mercurials.item_canonical
  · 9 familles plates (procurement_dict_families)
  · family_id = 'equipements' sur 1 443 items (97%)
  · domain_id / family_l2_id / subfamily_id = NULL sur tous

M7 tel que prévu devait enrichir ce dictionnaire
via proposals + validation humaine.

---

## Problème identifié avant M7

Deux défauts structurels ont été détectés :

DÉFAUT-STRUCT-01 · Taxonomie insuffisante
  9 familles plates ne permettent pas :
  · Une défense devant un auditeur DGMP / USAID / BM
  · Un lien avec les seuils DGMP par type d'achat
  · Une distinction item_type (good / service / works)
  · Un signal marché M9 contextualisé par domaine
  Solution → M7.2 : taxonomie L1/L2/L3 enterprise grade
             15 domaines · 57 familles · 155 sous-familles

DÉFAUT-STRUCT-02 · Infrastructure manquante
  Le dictionnaire n'avait pas :
  · Hash chain / audit trail sur les modifications
  · Seuils DGMP accessibles programmatiquement
  · Conversions UOM ISO
  · quality_score calculé automatiquement
  · Lien item ↔ fournisseur
  Sans cette infrastructure, M7 enrichissement = données
  sans traçabilité = non défendable en audit.
  Solution → M7.3 : nerve center · 4 tables + 9 colonnes + triggers

---

## Décision

Accepter le détour M7.2 + M7.3 avant M7 enrichissement réel.

Raison : construire sur du sable = refaire deux fois.
Un dictionnaire enrichi sans taxonomie correcte
= 1 488 items dans 9 familles plates
= inutilisable pour M9 (signal marché par domaine)
= indéfendable pour M14 (évaluation par type d'achat)
= rejeté par un auditeur DGMP au premier contrôle.

---

## Conséquences

POSITIF :
  · Taxonomie L1/L2/L3 disponible pour classify_taxo.py
  · Infrastructure audit trail opérationnelle
  · Seuils DGMP dans dgmp_thresholds (non hardcodés)
  · quality_score calculé automatiquement
  · family_id legacy déprécié proprement (M7.3b)

NÉGATIF :
  · Délai de 3 jalons sur M7 enrichissement réel
  · Complexité accumulée (à maîtriser · pas à ignorer)
  · 1 488 items avec domain_id = NULL
    jusqu'à exécution de classify_taxo.py

---

## M7 RÉEL — CE QUI DOIT ÊTRE LIVRÉ MAINTENANT

Après M7.3b (ce mandat), le plan V4.1.0 reprend
exactement comme prévu :

  ÉTAPE 1 · classify_taxo.py
    Peuple taxo_proposals_v2
    3 niveaux : seed_exact · trgm · llm_mistral
    Output : proposals · status=pending/approved/flagged

  ÉTAPE 2 · Validation humaine AO
    Review taxo_proposals_v2 status=pending
    Familles CRITIQUE en priorité :
    CARB_LUB · ALIM_VIVRES · SANTE · VEHICULES_ENGINS
    human_validated = TRUE sur items validés

  ÉTAPE 3 · seed_apply_taxo.py
    Copie domain_id / family_l2_id / subfamily_id
    depuis taxo_proposals_v2 status=approved
    vers procurement_dict_items
    RÈGLE-M7-03 : backfill script · jamais dans migration

  ÉTAPE 4 · Validation finale
    KPI : résiduel DIVERS_NON_CLASSE ≤ 25%
    KPI : quality_score moyen > 60
    Tag : v4.2.0-m7-dict-vivant

---

## Règles gravées issues de ce détour

RÈGLE-DICT-01  family_id legacy = READ-ONLY après M7.3b
RÈGLE-DICT-02  domain_id/family_l2_id/subfamily_id = cibles M7.2
RÈGLE-DICT-03  taxo_proposals_v2 = table de passage
               LLM propose · AO valide · backfill script applique
RÈGLE-DICT-04  Jamais deux systèmes de familles actifs simultanément
               Legacy = lecture historique uniquement
               M7.2 = source de vérité operative

---

## Alternatives rejetées

ALT-01 · Enrichir directement sur les 9 familles plates
         Rejeté : non défendable DGMP · inutilisable M9

ALT-02 · Supprimer family_id legacy (DROP COLUMN)
         Rejeté : RÈGLE-T04 · données historiques perdues
         Dépréciation propre = conservé + bloqué en écriture

ALT-03 · Attendre un sprint dédié taxonomie
         Rejeté : M9 bloqué sans domaines corrects
         Coût différé > coût immédiat

---

*ADR-0016 · DMS V4.2.0 · Tech Lead · 2026*
