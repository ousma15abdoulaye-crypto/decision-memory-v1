# FRAMEWORK ANNOTATION DMS v3.0.1a — FREEZE OPPOSABLE FINAL

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  DMS — ANNOTATION FRAMEWORK FINAL OPPOSABLE v3.0.1a                       ║
║  Auteur    : Abdoulaye Ousmane — CTO DMS                                   ║
║  Date      : 2026-03-15                                                    ║
║  Statut    : FREEZE DÉFINITIF — référence unique M11-bis → M15            ║
║  Supérieur : v3.0.1 · v3.0 · v2.2 · v2.1 · v1.0                         ║
║  Portée    : Documents amont uniquement                                    ║
║  Exclusion : PV/rapports = source patterns, jamais matière première M12   ║
║                                                                            ║
║  4 micro-corrections v3.0.1a :                                            ║
║    MC-1 : gate_value booléen réel + gate_state séparé                     ║
║    MC-2 : RÈGLE GATE-CONFIDENCE 0.6/0.8/1.0 explicite                    ║
║    MC-3 : price_date ABSENT autorisé avec fallback document_date          ║
║    MC-4 : evaluation_report interdit avant M15 — verrouillage explicite   ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## PARTIE 0 — AXIOMES FONDATEURS (IMMUABLES)

```
AXIOME-1  Le pipeline apprend UNE grammaire générale du dépouillement.
          Pas les règles SCI. SCI est le premier terrain d'entraînement.

AXIOME-2  Un champ n'existe que s'il sert à :
            → classer un document
            → activer ou bloquer un gate
            → expliquer un score
            → nourrir la mémoire marché (Couche B)
            → enrichir un profil fournisseur

AXIOME-3  GOODS | SERVICES est le premier tri. Toujours. Sans exception.
          Avant d'ouvrir un document. Avant toute extraction.

AXIOME-4  Atomic first. Les preuves élémentaires sont annotées.
          Les signaux agrégés sont DÉRIVÉS — jamais annotés manuellement.

AXIOME-5  Un record DONE sans annotated_validated n'existe pas.

AXIOME-6  SCI = premier référentiel terrain de haute qualité. Pas le plafond.
```

---

## PARTIE I — TAXONOMIE COMPLÈTE 3 NIVEAUX

### Niveau 1 — Famille principale (BP-20 : 2 secondes max)

| Code | Libellé |
|------|---------|
| `goods` | Fournitures / biens physiques |
| `services` | Prestations intellectuelles ou physiques |

---

### Niveau 2 — Sous-famille

**GOODS**

| Code | Exemples terrain Mali |
|------|-----------------------|
| `food` | Rations alimentaires, vivres, céréales |
| `office_consumables` | Papeterie, cartouches, fournitures bureau |
| `construction_materials` | Ciment, fer, matériaux bâtiment |
| `nfi` | Non-food items, kits NFI, bâches |
| `it_equipment` | Ordinateurs, serveurs, périphériques |
| `software` | Licences, abonnements SaaS |
| `nutrition_products` | ATPE, compléments nutritionnels |
| `vehicles` | Véhicules 4x4, camions |
| `motorcycles` | Motos, deux-roues |
| `other_goods` | Tout bien non classé ci-dessus |

**SERVICES**

| Code | Exemples terrain Mali |
|------|-----------------------|
| `consultancy` | Études, évaluations, conseils |
| `audit` | Audit financier, audit technique |
| `training` | Formation, renforcement capacités |
| `catering` | Restauration, traiteur |
| `vehicle_rental` | Location véhicules avec/sans chauffeur |
| `survey` | Enquêtes, collecte données terrain |
| `audiovisual` | Production vidéo, communication |
| `works` | Travaux construction, réhabilitation |
| `other_services` | Tout service non classé ci-dessus |

```
RÈGLE CRITIQUE — JAMAIS CONFONDRE :
  works                  = services  (prestation de construction)
  construction_materials = goods     (fourniture de matériaux)
```

---

### Niveau 3 — Taxonomy Core

| Code | Description | document_role associé |
|------|-------------|----------------------|
| `dao` | Dossier d'Appel d'Offres | `source_rules` |
| `rfq` | Request for Quotation | `source_rules` |
| `rfp_consultance` | Request for Proposal consultance | `source_rules` |
| `tdr_consultance_audit` | Termes de Référence | `source_rules` |
| `offer_technical` | Offre technique fournisseur | `technical_offer` |
| `offer_financial` | Offre financière fournisseur | `financial_offer` |
| `offer_combined` | Offre technique+financière combinée | `combined_offer` |
| `annex_pricing` | DQE / BPU / BOQ annexe prix | `annex_pricing` |
| `supporting_doc` | Attestation / CV / Licence / Certificat | `supporting_doc` |
| `evaluation_report` | PV / Rapport d'analyse | `evaluation_report` |
| `marketsurvey` | Enquête marché / sondage prix | `source_rules` |

```
MC-4 — VERROUILLAGE evaluation_report :
  evaluation_report est défini dans la taxonomie pour stabilité du framework.
  Son annotation est STRICTEMENT INTERDITE avant M15.
  Activation conditionnée à ≥ 50 annotated_validated sur familles A+B+C+D.
  Tout record evaluation_report créé avant M15 = INVALIDE — rejeté.
```

---

### Document Role — Liste complète

| Code | Définition | Erreur fatale si confondu avec |
|------|-----------|-------------------------------|
| `source_rules` | Document émetteur des règles du jeu | `technical_offer` |
| `technical_offer` | Offre technique d'un fournisseur X | `source_rules` |
| `financial_offer` | Offre financière d'un fournisseur X | `annex_pricing` |
| `combined_offer` | Offre technique+financière en un seul document | `source_rules` |
| `annex_pricing` | Annexe prix BPU/DQE/BOQ liée à une offre | `financial_offer` |
| `supporting_doc` | Pièce justificative admin/technique | `technical_offer` |
| `evaluation_report` | PV ou rapport d'analyse post-offres | Toute famille A/B/C — INTERDIT M12/M13 |

```
RÈGLE : taxonomy_core = offer_combined → document_role = combined_offer
        Un champ n'a jamais deux rôles simultanés.
        1 document confondu avec 1 offre = erreur d'annotation irrécupérable.
```

### Mapping taxonomy_client_adapter → taxonomy_core (SCI Mali)

| Wording client | taxonomy_core |
|----------------|---------------|
| "cotation formelle" | `rfq` |
| "avis d'appel d'offres" | `dao` |
| "termes de référence" | `tdr_consultance_audit` |
| "demande de proposition" | `rfp_consultance` |
| "invitation à soumissionner" | `dao` |
| "demande de cotation" | `rfq` |
| "invitation to tender" | `dao` |

---

## PARTIE II — NULL DOCTRINE (JAMAIS VIOLÉE)

### Les 3 états distincts

| État | Signification | Exemple terrain |
|------|--------------|-----------------|
| `ABSENT` | Champ exigé, non trouvé dans le document | `has_nif` = ABSENT |
| `AMBIGUOUS` | Présent mais contradictoire ou illisible | `delivery_delay_days` = AMBIGUOUS |
| `NOT_APPLICABLE` | Non pertinent pour ce type/famille | `phytosanitary_cert_present` = NOT_APPLICABLE sur IT |

```
null   = état PENDING uniquement — pré-annotation Mistral non corrigée
         Un record annotated_validated ne contient AUCUN null.

INTERDIT : valeur nue sans état
INTERDIT : laisser null sur un record validé
INTERDIT : mélanger ABSENT et NOT_APPLICABLE
```

### LIST-NULL-RULE (PATCH-3)

```
Cas 1 — Champ liste NON CRITIQUE :
  liste vide [] = valide si champ réellement non trouvé

Cas 2 — Champ liste CRITIQUE :
  lot_scope        obligatoire sur offer_*       → ABSENT si non trouvé
  zone_scope       obligatoire sur offer_*       → ABSENT si non trouvé
  submission_mode  obligatoire sur source_rules  → ABSENT si non trouvé
  eligibility_gates obligatoire sur source_rules → [] uniquement si régime
                    explicitement déclaré sans gate éliminatoire

Règle compagnon :
  Si liste critique = [] → documenter dans _meta :
  "list_null_reason": {"<champ>": "ABSENT|NOT_APPLICABLE|not_required"}

Objectif : zéro trou silencieux dans les listes.
```

### Matrice de décision NULL

```
Le champ est-il pertinent pour cette famille/type ?
    │
    ├── NON → NOT_APPLICABLE
    │
    └── OUI → Le champ est-il trouvable dans le document ?
                  │
                  ├── OUI, texte exact      → value + confidence 1.0
                  ├── OUI, inféré           → value + confidence 0.8
                  ├── OUI, OCR dégradé      → value + confidence 0.6
                  ├── NON, champ absent     → ABSENT
                  └── Présent mais flou     → AMBIGUOUS
```

---

## PARTIE III — FORMAT CANONIQUE CHAMP CRITIQUE (RÈGLE-19)

```json
{
  "value":      "<valeur extraite>",
  "confidence": 1.0,
  "evidence":   "<5-10 mots EXACTS copiés du document>"
}
```

### Grille confidence — universelle

| Valeur | Condition | Exemple |
|--------|-----------|---------|
| `1.0` | Texte exact copié du document | "NIF obligatoire sous peine d'élimination" |
| `0.8` | Inféré / formulé indirectement | Délai inféré depuis le calendrier |
| `0.6` | OCR dégradé / lecture fragile | Chiffre partiellement lisible |

```
INTERDIT : confidence hors grille 0.6 / 0.8 / 1.0
INTERDIT : champ critique sans evidence
INTERDIT : evidence inventée
```

---

## PARTIE IV — OCR-RULE (BP-21)

```
OCR-RULE :

Périmètre d'annotation :
  L'annotation porte sur le fragment utile minimal.
  Jamais sur le document entier si > 20 pages.

page_range obligatoire si document > 20 pages :
  "page_range": {"start": 3, "end": 7}

evidence localisable :
  Format recommandé : "p.4 — NIF obligatoire sous peine d'élimination"

OCR trop dégradé :
  confidence = 0.6 OBLIGATOIRE
  review_required = true AUTOMATIQUE
  annotation_status reste in_review jusqu'à validation humaine

Fragments OCR illisibles (> 30% du champ) :
  → value = AMBIGUOUS
  → evidence = "OCR dégradé — fragment illisible"
  → review_required = true
```

---

## PARTIE V — ARCHITECTURE 5 COUCHES COMPLÈTE

### Vue d'ensemble

```
COUCHE 1 — ROUTING          → classement en < 5 secondes
COUCHE 2 — CORE PROCUREMENT → universel · transférable · jamais SCI-specific
COUCHE 3 — POLICY ADAPTER   → SCI V1 · isolé · remplaçable par autre client
COUCHE 4 — ATOMIC EVIDENCE  → preuves élémentaires annotées par l'humain
COUCHE 5 — GATES MÉTIER     → ce qui ouvre ou ferme les portes
```

---

### COUCHE 1 — ROUTING IMMÉDIAT

```json
{
  "procurement_family_main":  "goods | services",
  "procurement_family_sub":   "<sous-famille>",
  "taxonomy_core":            "<type document>",
  "taxonomy_client_adapter":  "<wording exact client>",
  "document_stage":           "solicitation | offer | evaluation | decision",
  "document_role":            "source_rules | technical_offer | financial_offer | combined_offer | annex_pricing | supporting_doc | evaluation_report"
}
```

---

### COUCHE 2 — CORE PROCUREMENT

#### Bloc A — Identité dossier

| Champ | Type | Criticité | NULL si absent |
|-------|------|-----------|----------------|
| `procedure_reference` | string | CRITIQUE | ABSENT |
| `issuing_entity` | string | CRITIQUE | ABSENT |
| `project_name` | string | standard | ABSENT |
| `lot_count` | int | standard | ABSENT |
| `lot_scope` | list[string] | CRITIQUE sur offer_* | ABSENT |
| `zone_scope` | list[string] | CRITIQUE sur offer_* | ABSENT |
| `office_scope` | list[string] | standard | [] si non trouvé |
| `submission_deadline` | string | CRITIQUE | ABSENT |
| `submission_mode` | list[enum] | CRITIQUE source_rules | ABSENT |
| `submission_address` | string | standard | ABSENT |
| `offer_validity_days` | int | standard | ABSENT |
| `result_type` | enum | CRITIQUE | ABSENT |

#### Bloc B — Règles de jugement

| Champ | Type | Description |
|-------|------|-------------|
| `eligibility_gates` | list[object] | Critères éliminatoires + eliminatoire=true |
| `scoring_structure` | list[object] | {critere, poids_pct, seuil, evidence} |
| `technical_threshold` | int | Seuil minimum technique → passage financier |
| `commercial_stage_condition` | string | Condition activation évaluation commerciale |
| `visit_required` | bool/NOT_APPLICABLE | Visite de site obligatoire |
| `sample_required` | bool/NOT_APPLICABLE | Échantillons requis |
| `negotiation_allowed` | bool/NOT_APPLICABLE | Négociation autorisée |
| `regime_dominant` | enum | AUTOMATIQUE/CONDITIONNEL/PENALITE_FISCALE/MIXTE/AUCUN |
| `modalite_paiement` | string | Description modalités paiement |

**Format scoring_structure canonique**

```json
[
  {
    "critere":    "technique",
    "poids_pct":  70,
    "seuil":      60,
    "evidence":   "offres techniques notées sur 70 points minimum 60"
  },
  {
    "critere":    "financier",
    "poids_pct":  30,
    "seuil":      null,
    "evidence":   "offre financière évaluée sur 30 points"
  }
]
```

**Vérification cohérence pondération — RÈGLE MATHÉMATIQUE STRICTE**

$$\sum_{i=1}^{n} \text{poids\_pct}_i = 100$$

```
Si somme ≠ 100 ET champs présents → ambiguites += "AMBIG-2_ponderation_manquante"
Si somme = 0   ET scoring déclaré → ambiguites += "AMBIG-2_ponderation_manquante"
Si scoring absent du document     → ponderation_coherence = "non_precisee_dans_doc"
```

---

### COUCHE 3 — POLICY ADAPTER SCI V1

```
DOCTRINE : Jamais fusionner dans Couche 2.
           Tag explicite Label Studio.
           Export filtrable par couche.
           Remplaçable par autre client sans toucher Couche 2.
```

| Champ | Type | NOT_APPLICABLE si |
|-------|------|-------------------|
| `has_sci_conditions_signed` | bool/ABSENT/NOT_APPLICABLE | Marché local < 1 000 $ |
| `has_iapg_signed` | bool/ABSENT/NOT_APPLICABLE | Fournisseur sans historique SCI |
| `has_non_sanction` | bool/ABSENT/NOT_APPLICABLE | Marché local < 1 000 $ |
| `ariba_network_required` | bool/ABSENT/NOT_APPLICABLE | Dossier non-Ariba |
| `sci_sustainability_pct` | int/NOT_APPLICABLE | Type sans critère durabilité |

---

### COUCHE 4 — ATOMIC EVIDENCE FIELDS

#### 4A — Conformité administrative (universelle)

| Champ | NOT_APPLICABLE si |
|-------|-------------------|
| `has_nif` | Marché international |
| `has_rccm` | Marché international |
| `has_rib` | Paiement cash uniquement |
| `has_id_representative` | Jamais NOT_APPLICABLE |
| `has_statutes` | Personne physique |
| `has_quitus_fiscal` | Exonération documentée |
| `has_certificat_non_faillite` | Marché < seuil |

#### 4B — Capacité SERVICES consultancy / audit / training / survey

| Champ | Type | Description |
|-------|------|-------------|
| `similar_assignments_count` | int/ABSENT | Nombre missions similaires |
| `lead_expert_years` | int/ABSENT | Années expérience chef de mission |
| `lead_expert_similar_projects_count` | int/ABSENT | Projets similaires chef de mission |
| `team_composition_present` | bool/ABSENT | Composition équipe fournie |
| `methodology_present` | bool/ABSENT | Note méthodologique présente |
| `workplan_present` | bool/ABSENT | Plan de travail / chronogramme |
| `qa_plan_present` | bool/ABSENT/NOT_APPLICABLE | Plan qualité |
| `ethics_plan_present` | bool/ABSENT/NOT_APPLICABLE | Plan éthique |

#### 4C — Capacité SERVICES works

| Champ | Type | Description |
|-------|------|-------------|
| `execution_delay_days` | int/ABSENT | Délai exécution en jours |
| `work_methodology_present` | bool/ABSENT | Méthodologie travaux |
| `environment_plan_present` | bool/ABSENT | Plan environnemental |
| `site_visit_pv_present` | bool/ABSENT | PV visite de site |
| `equipment_list_present` | bool/ABSENT | Liste équipements |
| `key_staff_present` | bool/ABSENT | Personnel clé identifié |
| `local_labor_commitment_present` | bool/ABSENT | Engagement main-d'œuvre locale |

#### 4D — Capacité GOODS

| Champ | NOT_APPLICABLE si |
|-------|-------------------|
| `client_references_present` | Marché < seuil références |
| `warranty_present` | Consommables sans garantie |
| `delivery_schedule_present` | Jamais NOT_APPLICABLE |
| `warehouse_capacity_present` | Livraison directe usine |
| `stock_sufficiency_present` | Sur commande uniquement |
| `product_specs_present` | Jamais NOT_APPLICABLE |
| `official_distribution_license_present` | Fabricant direct |
| `sample_submission_present` | Catégorie sans échantillon |
| `phytosanitary_cert_present` | Non-alimentaire |
| `bank_credit_line_present` | Marché < seuil |

#### 4E — Durabilité

| Champ | Type |
|-------|------|
| `local_content_present` | bool/ABSENT/NOT_APPLICABLE |
| `community_employment_present` | bool/ABSENT/NOT_APPLICABLE |
| `environment_commitment_present` | bool/ABSENT/NOT_APPLICABLE |
| `gender_inclusion_present` | bool/ABSENT/NOT_APPLICABLE |
| `sustainability_certifications` | list[string]/NOT_APPLICABLE |

#### 4F — Financier (financial_offer / combined_offer uniquement)

| Champ | Valeurs | Règle |
|-------|---------|-------|
| `financial_layout_mode` | structured_table / boq_dqe / narrative_quote / lump_sum_only / mixed / NOT_APPLICABLE | BP-18 : déclarer AVANT line_items |
| `pricing_scope` | line / lot / document / NOT_APPLICABLE | — |
| `total_price` | float/ABSENT | — |
| `currency` | XOF/USD/EUR/ABSENT | — |
| `price_basis` | HT/TTC/non_precise/NOT_APPLICABLE | — |
| `price_date` | string/ABSENT | MC-3 : voir règle ci-dessous |
| `delivery_delay_days` | int/ABSENT | — |
| `validity_days` | int/ABSENT | — |
| `discount_terms_present` | bool/ABSENT | — |
| `review_required` | bool | Automatique si narrative_quote ou mixed |

```
MC-3 — RÈGLE price_date révisée :
  OBLIGATOIRE si explicitement présent ou déductible du document financier.
  ABSENT si non trouvé ou non déductible.
  Si ABSENT → fallback analytique ultérieur = document_date (calculé par pipeline).
  Ne jamais forcer price_date = document_date dans l'annotation humaine.
  Un ABSENT honnête vaut mieux qu'une inférence silencieuse.
```

**Règle review_required automatique**

```
structured_table → review_required = False
boq_dqe         → review_required = False
narrative_quote  → review_required = True   ← AUTOMATIQUE
lump_sum_only    → review_required = False
mixed            → review_required = True   ← AUTOMATIQUE
```

#### 4G — LINE ITEMS (BP-15 · BP-19 — CONTRAT ABSOLU)

```
RÈGLE DONE :
  Si tableau présent → line_items OBLIGATOIRES.
  Montant global seul acceptable UNIQUEMENT si lump_sum_only confirmé.
  1 ligne tableau = 1 unité d'annotation financière atomique.
```

| Champ | Obligatoire | Type |
|-------|-------------|------|
| `item_line_no` | OUI | int |
| `lot_number` | OUI | string/NOT_APPLICABLE |
| `supplier_name_raw` | OUI | string |
| `procedure_reference` | OUI | string |
| `zone_scope` | OUI | list[string] |
| `item_description_raw` | OUI | string |
| `item_canonical_candidate` | OUI | string |
| `specification_hint` | OUI | string/ABSENT |
| `brand_hint` | OUI | string/ABSENT |
| `packaging_hint` | OUI | string/ABSENT |
| `unit_raw` | OUI | string |
| `quantity` | OUI | float |
| `unit_price` | OUI | float |
| `line_total` | OUI | float |
| `currency` | OUI | enum |
| `price_basis` | OUI | enum |
| `pricing_scope` | OUI | enum |
| `price_date` | OUI | string/ABSENT |
| `evidence_hint` | OUI | string |
| `confidence` | OUI | 0.6/0.8/1.0 |

**Vérification mathématique obligatoire par ligne**

$$\text{line\_total} = \text{quantity} \times \text{unit\_price}$$

$$\text{Si } \left| \text{line\_total} - (\text{quantity} \times \text{unit\_price}) \right| > 0.01 \times \text{line\_total}$$

```
→ ambiguites += "AMBIG-3_reference_contradictoire"
→ review_required = True
```

---

### COUCHE 5 — GATES MÉTIER (BP-14)

```
DOCTRINE : Un pipeline amateur annote les scores.
           Un pipeline pro annote aussi ce qui ouvre ou ferme les portes.
           Tout document DOIT déclarer ses gates ou NOT_APPLICABLE.
```

#### MC-1 — Format canonique gate (booléen réel séparé de l'état métier)

```json
{
  "gate_name":            "<code gate>",
  "gate_value":           true,
  "gate_state":           "APPLICABLE",
  "gate_threshold_value": 60,
  "gate_reason_raw":      "<texte justificatif extrait du document>",
  "gate_evidence_hint":   "<5-10 mots exacts du document>",
  "confidence":           0.8
}
```

**Cas NOT_APPLICABLE**

```json
{
  "gate_name":            "gate_visit_required",
  "gate_value":           null,
  "gate_state":           "NOT_APPLICABLE",
  "gate_threshold_value": null,
  "gate_reason_raw":      "consultance sans visite de site",
  "gate_evidence_hint":   "NOT_APPLICABLE",
  "confidence":           1.0
}
```

**Règle gate_value / gate_state**

| gate_state | gate_value | Signification |
|-----------|-----------|---------------|
| `APPLICABLE` | `true` | Gate applicable — condition remplie |
| `APPLICABLE` | `false` | Gate applicable — condition non remplie |
| `NOT_APPLICABLE` | `null` | Gate non pertinent pour ce type/famille |

```
INTERDIT : gate_value = "true" (string)
INTERDIT : gate_value = "false" (string)
INTERDIT : gate_value = "NOT_APPLICABLE" (string)
gate_value est toujours un booléen réel ou null.
```

#### MC-2 — RÈGLE GATE-CONFIDENCE (explicite)

```
Les gates suivent STRICTEMENT la même grille confidence que les champs critiques :
  0.6 / 0.8 / 1.0 uniquement.

INTERDIT : confidence = 0.7
INTERDIT : confidence = 0.9
INTERDIT : confidence = 0.95
INTERDIT : toute valeur hors grille

Application :
  gate_value déduit de texte exact      → confidence = 1.0
  gate_value inféré depuis le contexte  → confidence = 0.8
  gate_value sur document OCR dégradé   → confidence = 0.6
```

#### Catalogue gates complet

| gate_name | NOT_APPLICABLE si | Exemple seuil terrain |
|-----------|-------------------|-----------------------|
| `gate_eligibility_passed` | Jamais | Tous docs admin présents |
| `gate_capacity_passed` | source_rules sans offre | 36/60 cap+durabilité |
| `gate_visit_required` | Famille sans visite | food si non exigé |
| `gate_visit_passed` | visit_required=false | PV signé fourni |
| `gate_samples_required` | Famille sans échantillon | food, nfi |
| `gate_samples_passed` | samples_required=false | Échantillons conformes |
| `gate_commercial_eligible` | source_rules | Seuil technique atteint |
| `gate_negotiation_reached` | negotiation_allowed=false | Shortlist 3 fournisseurs |
| `gate_financial_format_usable` | source_rules | Layout extractable |
| `gate_line_item_extractable` | lump_sum_only | Tableau présent et lisible |

#### Patterns gates par famille (terrain SCI Mali)

```
works / construction :
  gate_capacity_passed     → seuil 36/60 (capacité + durabilité)
  gate_visit_required      → true si DAO avec visite obligatoire

food / nfi :
  gate_samples_required    → true
  gate_visit_required      → true (inspection entrepôt)

consultance / audit :
  gate_capacity_passed     → seuil 60/70 technique
  gate_commercial_eligible → seuil technique atteint → financier

it_equipment / office_consumables :
  gate_negotiation_reached → shortlist 3 mieux notés → négociation
```

---

## PARTIE VI — UNITÉ D'ANNOTATION — RECORD CANONIQUE

```
1 record = 1 document
         + 1 document_role
         + 1 case_id
         + 1 supplier_id    (si document_role ≠ source_rules)
         + 1 lot_scope      (si applicable)
```

### Identifiants obligatoires

| Champ | Format | Règle |
|-------|--------|-------|
| `case_id` | `{procedure_reference}_{lot_number}_{zone}` | Jamais null |
| `supplier_id` | `{supplier_name_normalized}_{procedure_reference}` | NOT_APPLICABLE si source_rules |
| `supplier_name_raw` | Texte brut extrait | Voir règle PATCH-4 |
| `supplier_name_normalized` | Minuscules, sans accents | Dérivé de raw |
| `supplier_identifier_raw` | NIF ou RCCM si trouvable | ABSENT si non trouvé |

### Règle supplier_name_raw (PATCH-4 confirmé)

```
OBLIGATOIRE sur :
  technical_offer    → sans exception
  financial_offer    → sans exception
  combined_offer     → sans exception
  annex_pricing      → sans exception

Sur supporting_doc :
  → OBLIGATOIRE si visible dans le document
  → ABSENT si non visible
  → Héritage obligatoire via parent_document_id + parent_supplier_id

Sur source_rules :
  → NOT_APPLICABLE

Sur evaluation_report :
  → OBLIGATOIRE par fournisseur évalué (1 record par fournisseur)
  → INTERDIT avant M15
```

---

## PARTIE VII — RELATION PARENT/ENFANT (PATCH-5)

```
RELATION-RULE :

Tout record annex_pricing ou supporting_doc DOIT déclarer :

  "parent_document_id":   "<case_id du document principal>",
  "parent_document_role": "<document_role du parent>",
  "case_id":              "<même case_id que le parent>",
  "supplier_id":          "<même supplier_id que le parent si applicable>"

Règle d'héritage :
  Si supplier_name_raw = ABSENT sur supporting_doc
  → supplier_name_raw hérité du parent via parent_document_id
  → documenter dans _meta :
    "supplier_inherited_from": "<parent_document_id>"

Règle d'intégrité :
  Aucun document annexe ne vit seul.
  annex_pricing sans parent_document_id  = NOT DONE
  supporting_doc sans parent_document_id = NOT DONE

Format canonique liaison :
{
  "parent_document_id":   "AO-SCI-MLI-MPT-2026-001_lot2_Mopti",
  "parent_document_role": "technical_offer",
  "case_id":              "AO-SCI-MLI-MPT-2026-001_lot2_Mopti",
  "supplier_id":          "sarl_mali_construct_AO-SCI-MLI-MPT-2026-001"
}
```

---

## PARTIE VIII — _META OBLIGATOIRE (RÈGLE-23)

```json
{
  "_meta": {
    "schema_version":           "v3.0.1a",
    "doc_stage":                "solicitation | offer | evaluation | decision",
    "document_role":            "source_rules | technical_offer | financial_offer | combined_offer | annex_pricing | supporting_doc | evaluation_report",
    "procurement_family_main":  "goods | services",
    "procurement_family_sub":   "<sous-famille>",
    "case_id":                  "<procedure_reference>_<lot>_<zone>",
    "supplier_id":              "<supplier_name_normalized>_<procedure_reference> | NOT_APPLICABLE",
    "supplier_inherited_from":  "<parent_document_id> | null",
    "parent_document_id":       "<case_id parent> | NOT_APPLICABLE",
    "parent_document_role":     "<role parent> | NOT_APPLICABLE",
    "page_range":               {"start": null, "end": null},
    "list_null_reason":         {},
    "annotated_by":             "<identifiant annotateur>",
    "annotated_at":             "<ISO 8601>",
    "annotation_duration_min":  0,
    "annotation_status":        "pending | in_review | annotated | annotated_validated",
    "is_gold_standard":         false,
    "framework_version":        "v3.0.1a",
    "mistral_model_used":       "mistral-small-latest",
    "review_required":          false
  }
}
```

---

## PARTIE IX — ÉTATS ANNOTATION ET WORKFLOW

```
pending
  │  Mistral pré-annote
  ▼
in_review
  │  Annotateur ouvre le document
  ▼
annotated
  │  Annotateur soumet
  ▼
annotated_validated    ← SEUL ÉTAT COMPTABLE POUR M12 / M15
```

### SLA workflow

| Transition | Condition | SLA |
|-----------|-----------|-----|
| pending → in_review | Mistral pré-annoté | < 1h après ingestion |
| in_review → annotated | DONE checklist complète | < 48h |
| annotated → annotated_validated | Review queue validée | < 24h |
| annotated → in_review | confidence < 0.75 ou review_required | SLA 48h BP-10 |

---

## PARTIE X — DONE BINAIRE — 10 CONDITIONS

| # | Condition | Bloquant |
|---|-----------|---------|
| 1 | routing complet | taxonomy_core + family_main + family_sub + document_role ≠ null/ABSENT |
| 2 | document_role cohérent | source_rules↔solicitation · offer_*↔offer |
| 3 | supplier / lot / zone | OBLIGATOIRES sur offer_* ou NOT_APPLICABLE documenté |
| 4 | gates déclarés | gate_value booléen + gate_state déclarés. NOT_APPLICABLE documenté |
| 5 | champs critiques | Tous {value + confidence + evidence} — aucun null résiduel |
| 6 | financial_layout_mode | Déclaré si financial_offer ou combined_offer |
| 7 | line_items | Extraits si tableau présent ET layout ≠ lump_sum_only |
| 8 | market_memory_readiness | True si financial_offer ou combined_offer |
| 9 | annotation_status | = annotated_validated |
| 10 | parent_document_id | Déclaré si annex_pricing ou supporting_doc |

```
1 condition non remplie = NOT DONE. Sans exception. Sans dérogation sans GO CTO.
```

---

## PARTIE XI — BEST PRACTICES BP-01 → BP-21

| Code | Titre | Règle |
|------|-------|-------|
| BP-01 | Pré-annotation obligatoire | Mistral pré-annote. Humain corrige uniquement. |
| BP-02 | Gold Standard Set | 5 docs figés, 100% manuels, jamais modifiés. |
| BP-03 | IAA Cohen Kappa ≥ 0.80 | Sur champs critiques. κ < 0.60 → refaire guideline. |
| BP-04 | Guidelines versionnées | 1 page par famille. Figé avant chaque lot. |
| BP-05 | Calibration session | 1er doc de chaque lot = comparé Mistral. Écarts logués. |
| BP-06 | Active learning | Priorité tasks confidence < 0.75. |
| BP-07 | annotated_validated seul comptable | Min 15 avant M12. Min 50 avant M15. |
| BP-08 | Evidence obligatoire | Champ critique sans evidence = INVALIDE. Bloquant. |
| BP-09 | Séparation CORE / POLICY / SIGNALS | Tag explicite LS. Export filtrable par couche. |
| BP-10 | Review Queue SLA 48h | confidence < 0.75 → review_required = True. |
| BP-11 | Versioning sha256 | annotated_at + annotated_by + duration_min sur chaque record. |
| BP-12 | Test set isolé 20% | 12 train / 3 test sur 15 docs M12. Jamais mélangés. |
| BP-13 | Atomic first | Preuves élémentaires annotées. Signaux agrégés dérivés. |
| BP-14 | Gates explicit first | Tout doc déclare ses gates ou NOT_APPLICABLE. Bloquant DONE. |
| BP-15 | Financial lines mandatory | Offre fin sans line_items si tableau = NOT DONE. |
| BP-16 | Supplier/lot/zone mandatory | supplier_name_raw + lot + zone OBLIGATOIRES sur offer_*. |
| BP-17 | Market-memory readiness | "Cette annotation peut-elle nourrir Couche B ?" avant clôture. |
| BP-18 | Financial routing first | financial_layout_mode déclaré AVANT line_items. |
| BP-19 | Line item extractability | Si tableau → extraction ligne par ligne. Vérifier $\text{qty} \times \text{unit\_price} = \text{line\_total}$. |
| BP-20 | GOODS/SERVICES routing first | Aucun doc ouvert sans procurement_family_main déclaré. |
| BP-21 | OCR-RULE | page_range si > 20 pages. confidence 0.6 + review_required si OCR dégradé. |

---

## PARTIE XII — CE QU'IL NE FAUT PAS ANNOTER

```
INTERDIT :
  prose institutionnelle non décisionnelle
  introductions contextuelles sans impact gate/score/prix
  noms des membres du comité (sauf si requis par gate)
  narratif cérémonial / remerciements
  rappels juridiques sans effet opératoire
  répétitions textuelles identiques

TEST D'ADMISSION D'UN CHAMP :
  "Ce champ sert-il à classer, gater, scorer, mémoriser ou profiler ?"
  NON → Le champ n'entre pas dans le schéma.
```

---

## PARTIE XIII — SIGNAUX DÉRIVÉS (CALCULÉS — JAMAIS ANNOTÉS)

| Signal | Source | Formule |
|--------|--------|---------|
| `passed_to_next_stage` | gate_commercial_eligible | True si gate_value = true |
| `capacity_evidence_present` | couche4.capacite_* | ≥ 3 champs ≠ ABSENT |
| `price_extractable` | financial_layout_mode | ≠ narrative_quote ET ≠ mixed |
| `line_items_complete` | line_items | Tous champs obligatoires ≠ ABSENT |
| `financial_anomaly_candidate` | line_total vs qty×unit_price | Écart > 1% |
| `market_memory_ready` | financial_offer + price_extractable | True si les deux |
| `price_date_resolved` | price_date + document_date | fallback pipeline si price_date = ABSENT |

---

## PARTIE XIV — SCHÉMAS D'ACTIVATION PAR FAMILLE

### FAMILLE A — SOLICITATION (source_rules)

```
COUCHE 1  → routing complet obligatoire
COUCHE 2  → identité dossier + règles jugement COMPLETS
COUCHE 3  → policy SCI si applicable
COUCHE 4  → conformite_admin      = NOT_APPLICABLE
            capacite_*            = NOT_APPLICABLE
            durabilite            = NOT_APPLICABLE
            financier             = NOT_APPLICABLE
COUCHE 5  → gate_eligibility      = NOT_APPLICABLE
            gate_capacity         = NOT_APPLICABLE
            gate_visit_required   → DÉCLARER (gate_state = APPLICABLE)
            gate_samples_required → DÉCLARER (gate_state = APPLICABLE)
            gate_financial_format = NOT_APPLICABLE
            gate_line_item        = NOT_APPLICABLE
```

### FAMILLE B — OFFRE TECHNIQUE (technical_offer)

```
COUCHE 1  → routing + supplier_name_raw + lot_scope + zone_scope
COUCHE 2  → procedure_reference OBLIGATOIRE
COUCHE 3  → has_sci_conditions + has_iapg + has_non_sanction
COUCHE 4  → conformite_admin COMPLET
            capacite_services OU capacite_goods selon family_main
            durabilite si sci_sustainability_pct > 0
            financier = NOT_APPLICABLE
COUCHE 5  → gate_eligibility_passed   (gate_state = APPLICABLE)
            gate_capacity_passed      si scoring déclaré
            gate_visit_passed         si visit_required = true
            gate_samples_passed       si sample_required = true
            gate_financial_format     = NOT_APPLICABLE
            gate_line_item            = NOT_APPLICABLE
```

### FAMILLE C — OFFRE FINANCIÈRE (financial_offer / combined_offer)

```
COUCHE 1  → routing + supplier_name_raw + lot_scope + zone_scope
COUCHE 2  → procedure_reference OBLIGATOIRE
COUCHE 3  → NOT_APPLICABLE
COUCHE 4  → conformite_admin  = NOT_APPLICABLE
            capacite_*        = NOT_APPLICABLE
            financier COMPLET — financial_layout_mode PREMIER
            line_items OBLIGATOIRES si tableau présent
COUCHE 5  → gate_commercial_eligible      (gate_state = APPLICABLE)
            gate_financial_format_usable  (gate_state = APPLICABLE)
            gate_line_item_extractable   (gate_state = APPLICABLE)
            gate_eligibility              = NOT_APPLICABLE
            gate_capacity                 = NOT_APPLICABLE
```

### FAMILLE D — PIÈCES SUPPORT (supporting_doc / annex_pricing)

```
COUCHE 1  → routing + parent_document_id OBLIGATOIRE
COUCHE 2  → procedure_reference OBLIGATOIRE
            supplier_name_raw si visible sinon hérité
COUCHE 3  → selon type pièce
COUCHE 4  → champs pertinents selon type pièce
COUCHE 5  → gates = NOT_APPLICABLE sauf si pièce déclenche un gate
```

### FAMILLE E — RAPPORT D'ANALYSE / PV (evaluation_report)

```
INTERDIT avant M15.
Défini dans la taxonomie pour stabilité du framework uniquement.
Activation conditionnée à ≥ 50 annotated_validated sur A+B+C+D.
Tout record evaluation_report créé avant M15 = INVALIDE — rejeté automatiquement.
```

---

## PARTIE XV — SCOPE PAR MILESTONE

| Milestone | Périmètre | Volume requis | Condition activation |
|-----------|-----------|---------------|---------------------|
| M10B | Calibration Gold Standard | 3 docs 100% manuels | Figés avant M11-bis |
| M11-bis | Infrastructure annotation | LS + backend v3.0.1a + XML | Opérationnel — milestone actuel |
| M12 | Familles A + B + C | ≥ 15 annotated_validated | Procedure Recognizer precision ≥ 0.70 |
| M13 | Famille D — pièces support | ≥ 25 annotated_validated | Après M12 validé |
| M15 | Famille E — PV / rapports | ≥ 50 annotated_validated | Après M13 validé |

---

## PARTIE XVI — FORMULE DE SYNTHÈSE GRAVÉE

$$\text{dossier} \rightarrow \text{famille} \rightarrow \text{critères} \rightarrow \text{preuves} \rightarrow \text{score} \rightarrow \text{gate} \rightarrow \text{décision}$$

```
Ultra-précis dans l'apprentissage.
Abstrait dans l'architecture.
SCI = premier référentiel terrain de haute qualité. Pas le plafond.
```

---

## PARTIE XVII — GOUVERNANCE — RÈGLE DE FREEZE

```
FREEZE v3.0.1a — DATE : 2026-03-15
AUTEUR CTO : Abdoulaye Ousmane

Toute évolution future :
  → ADDITIVE uniquement
  → GO CTO explicite obligatoire — documenté

INTERDIT sans GO CTO :
  supprimer un gate
  affaiblir l'exigence line-item
  relâcher supplier / lot / zone / evidence / annotated_validated
  fusionner POLICY dans CORE
  réduire les 10 conditions DONE BINAIRE
  modifier la NULL doctrine
  changer la grille confidence 0.6 / 0.8 / 1.0
  supprimer un niveau de taxonomie
  modifier la RELATION-RULE parent/enfant
  contourner la LIST-NULL-RULE
  contourner la OCR-RULE
  modifier le format gate_value / gate_state
  activer evaluation_report avant M15
```

---

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  FRAMEWORK v3.0.1a — FREEZE DÉFINITIF — RÉFÉRENTIEL UNIQUE OPPOSABLE      ║
║                                                                            ║
║  Ce document gouverne :                                                    ║
║    → backend.py prompt Mistral                                             ║
║    → XML Label Studio                                                      ║
║    → Schema JSON groundtruth                                               ║
║    → Export JSONL entraînement M12                                         ║
║    → Toute décision d'annotation M11-bis → M15                            ║
║                                                                            ║
║  10 patches intégrés depuis v3.0 :                                         ║
║    PATCH-1  : Milestone M11-bis / M12 / M13 / M15 séquencé                 ║
║    PATCH-2  : combined_offer + document_role séparé                        ║
║    PATCH-3  : LIST-NULL-RULE listes critiques                              ║
║    PATCH-4  : supplier_name_raw supporting_doc révisé                      ║
║    PATCH-5  : RELATION-RULE parent/enfant + DONE condition 10               ║
║    PATCH-6  : OCR-RULE + BP-21                                             ║
║    MC-1     : gate_value booléen réel + gate_state séparé                   ║
║    MC-2     : GATE-CONFIDENCE 0.6/0.8/1.0 explicite                        ║
║    MC-3     : price_date ABSENT autorisé + fallback pipeline                ║
║    MC-4     : evaluation_report INTERDIT avant M15 — verrouillé             ║
╚══════════════════════════════════════════════════════════════════════════════╝
```
