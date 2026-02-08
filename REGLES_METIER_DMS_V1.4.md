📐 RÈGLES MÉTIER DMS V1.4 — DOCUMENT FINAL
Version : 1.4
Statut : PRODUCTION-READY (à freezer GitHub)
Date : 8 février 2026
Sources : Code des Marchés Publics Mali 2015 + Manuel SCI v3.2
Auteurs : Abdoulaye Ousmane + Affinement CTO/Product Lead

STRUCTURE DU DOCUMENT
Ce document contient 3 sections critiques pour le développement :

RÈGLES MÉTIER (M1-M9) → logique business du système

LEXIQUE CANONIQUE → objets et schémas de données

GRAMMAIRE PROCUREMENT → workflow et séquence d'exécution

I. RÈGLES MÉTIER COUCHE A (9 règles fondamentales)
RÈGLE M1 — Structure du processus (UN PROCESSUS = UN BESOIN HOMOGÈNE)
Source : Mali Code art. 9-10 + SCI §4

Principe :
Un Case = un besoin homogène avec une seule catégorie, un seul cadre procédural, N lots possibles.

Règle technique :

javascript
Case {
  procedure_type : enum [DAO | RFQ | RFP],  // UN SEUL type
  category : enum [TRAVAUX | FOURNITURES | SERVICES | PI],  // UNE SEULE catégorie
  lots : Array<Lot>,  // Minimum 1, même si marché simple
  estimated_value : Float  // Somme des lots
}

// Validation obligatoire
ASSERT sum(lots.estimated_value) == Case.estimated_value
Interdit :

Fragmenter artificiellement pour contourner les seuils

Mixer plusieurs catégories dans un même Case

RÈGLE M2 — Le seuil détermine la procédure (JAMAIS L'INVERSE)
Source : Mali Code art. 9.1 + SCI §4.2

Principe :
La valeur estimée déclenche automatiquement le type de procédure et les exigences minimales.

Grilles de référence :

GRILLE MALI (État/Donateurs exigeant conformité Mali)
text
┌─────────────────────────┬──────────────────┬────────────────────────┐
│ Catégorie               │ Seuil (FCFA)     │ Procédure              │
├─────────────────────────┼──────────────────┼────────────────────────┤
│ Travaux                 │ ≥ 100 000 000    │ DAO (Appel d'offres)   │
│ Fournitures/Services    │ ≥  80 000 000    │ DAO (Appel d'offres)   │
│ Prestations intellect.  │ ≥  70 000 000    │ RFP (Appel à proposit.)│
│ Tous                    │ < seuils         │ RFQ (Demande de devis) │
└─────────────────────────┴──────────────────┴────────────────────────┘
GRILLE SCI (Save the Children International)
text
┌─────────────────────────┬──────────────────┬─────────────┬──────────┐
│ Valeur estimée (USD)    │ Procédure SCI    │ Offres min  │ Comité   │
├─────────────────────────┼──────────────────┼─────────────┼──────────┤
│ ≥ 100 000               │ Open Tender      │ 5           │ Oui      │
│ 10 000 - 99 999         │ Formal Quote     │ 3           │ Oui      │
│ 1 000 - 9 999           │ Simple Quote     │ 2           │ Non      │
│ 100 - 999               │ Single Quote     │ 1           │ Non      │
│ < 100                   │ Petty Cash       │ 0           │ Non      │
└─────────────────────────┴──────────────────┴─────────────┴──────────┘
Règle d'application :

javascript
function determineProcedure(case) {
  if (case.authority == "MALI_STATE" || case.requires_mali_compliance) {
    return applyMaliGrid(case.estimated_value, case.category);
  } else if (case.authority == "SCI") {
    return applySCIGrid(case.estimated_value);
  } else {
    throw Error("Authority not supported");
  }
}

// L'outil instancie automatiquement :
Case.procedure_type  // DAO | RFQ | RFP | Open Tender | Formal Quote...
Case.min_submissions_required  // 1, 2, 3, 5
Case.evaluation_committee_required  // bool
Important :

L'outil affiche la procédure applicable

L'utilisateur peut override avec justification (eWaiver)

Tout override est loggé (append-only)

RÈGLE M3 — L'unité d'analyse est l'OFFRE, pas le fournisseur
Source : Mali Code + SCI §5 (critères d'évaluation des offres)

Principe fondamental :
La Couche A travaille UNIQUEMENT sur des Submissions (offres déposées), jamais sur des Suppliers (fournisseurs abstraits).

Modèle de données strict :

javascript
Submission {
  submission_id : UUID,  // Identifiant unique de l'offre
  case_id : UUID,
  supplier_id : UUID,  // Lien vers Supplier, mais PAS utilisé pour scoring
  lot_ids : Array<UUID>,
  documents : Array<Document>,
  submission_datetime : Timestamp,
  submission_mode : enum [PHYSIQUE_URNE | EMAIL_DEDIE | ARIBA_NETWORK | PLATEFORME_ETAT],
  conformity_status : enum [CONFORME | NON_CONFORME | EN_ATTENTE],
  evaluation_scores : {
    essential_criteria : Object,  // Pass/Fail par critère
    capacity_criteria : Object,   // Note par critère
    commercial_criteria : Object, // Note par critère
    sustainability_criteria : Object, // Note par critère
    total_score : Float,
    rank_by_lot : Object  // Classement par lot
  }
}

// INTERDIT :
// ❌ Submission.evaluation_scores NE DOIT PAS référencer :
//    - Supplier.historical_performance
//    - Supplier.past_contracts
//    - Supplier.global_rating
//    - Couche B (mémoire)

// Les scores sont calculés UNIQUEMENT sur les données de la Submission
Conséquence pour le CBA :

text
DOIT afficher :
✅ Nom soumissionnaire (Supplier.legal_name)
✅ Lot(s) concerné(s)
✅ Date/heure dépôt
✅ Conformité (pass/fail)
✅ Notes par critère (calculées sur Submission)
✅ Classement par lot

NE DOIT PAS afficher :
❌ "Score fournisseur global"
❌ "Historique des prix"
❌ "Taux de réussite passé"
❌ "Recommandation système" (sauf constat factuel)
RÈGLE M4 — Les critères essentiels sont éliminatoires
Source : SCI §5.2 + Mali Code (conformité administrative)

Principe :
Critères pass/fail, aucune pondération, évaluation binaire.

Liste des critères essentiels :

javascript
ESSENTIAL_CRITERIA = [
  // Communs Mali + SCI
  "documents_administratifs_requis",  // Liste définie dans DAO/RFQ
  "respect_specifications_minimales",  // Cahier des charges
  "respect_delais_soumission",  // Horodatage
  
  // SCI spécifiques
  "acceptation_conditions_generales",  // T&C SCI
  "engagement_politique_durabilite",  // Supplier Sustainability Policy
  "certification_non_terrorisme"  // Sanctions screening
];
Règle machine :

javascript
function evaluateEssentialCriteria(submission) {
  for (criterion of ESSENTIAL_CRITERIA) {
    if (submission[criterion] == false) {
      submission.conformity_status = "NON_CONFORME";
      submission.conformity_notes = `Critère non satisfait : ${criterion}`;
      submission.evaluation_scores = null;  // Pas de calcul
      return;
    }
  }
  submission.conformity_status = "CONFORME";
  // Procéder à l'évaluation des autres critères
}
Affichage utilisateur :

text
Tableau pré-classement :
┌────────────────┬──────────────────┬────────────────────────┐
│ Soumissionnaire│ Conformité admin │ Motif (si NON CONFORME)│
├────────────────┼──────────────────┼────────────────────────┤
│ Fournisseur A  │ ✅ CONFORME      │                        │
│ Fournisseur B  │ ❌ NON CONFORME  │ Agrément technique     │
│                │                  │ manquant               │
│ Fournisseur C  │ ⏳ EN ATTENTE    │ Documents incomplets,  │
│                │                  │ délai 48h pour complét.│
└────────────────┴──────────────────┴────────────────────────┘
RÈGLE M5 — Nombre minimum d'offres conformes conditionne la suite
Source : SCI §4.3.3 + Mali Code (relance obligatoire)

Principe :
L'outil compte, affiche, alerte. L'outil ne décide jamais (blocage ou continuation).

Grille minimums :

javascript
MIN_CONFORMING_SUBMISSIONS = {
  "Open Tender (SCI)" : 5,
  "Formal Quote (SCI)" : 3,
  "Simple Quote (SCI)" : 2,
  "Single Quote (SCI)" : 1,
  "DAO (Mali)" : 3,
  "RFQ (Mali)" : 3
};
Règle machine :

javascript
function checkMinimumSubmissions(case) {
  const conforming = case.submissions.filter(s => s.conformity_status == "CONFORME");
  const required = MIN_CONFORMING_SUBMISSIONS[case.procedure_type];
  
  if (conforming.length < required) {
    return {
      status : "BELOW_THRESHOLD",
      message : `Nombre minimum non atteint : ${conforming.length}/${required}`,
      options : [
        "Prolonger la période de réponse",
        "Relancer la procédure",
        "Demander eWaiver (si 1-2 offres)"
      ]
    };
  }
  return { status : "OK" };
}

// L'outil affiche l'alerte + options
// L'utilisateur choisit
// L'outil LOG la décision (qui, quand, quoi, pourquoi)
RÈGLE M6 — Typologie universelle des critères d'évaluation
Source : SCI §5.2 + Mali Code (critères techniques, financiers, administratifs)

Les 4 familles :

javascript
CRITERION_TYPES = {
  ESSENTIAL : {
    nature : "Pass/Fail",
    traitement : "Automatique",
    ponderation : 0  // Éliminatoire
  },
  
  CAPACITY : {
    nature : "Qualitatif structurable",
    traitement : "Pré-rempli + champs humains",
    ponderation : "0-50% (facultatif)"
  },
  
  COMMERCIAL : {
    nature : "Quantitatif",
    traitement : "Automatique (formules)",
    ponderation : "≥40% (obligatoire)"
  },
  
  SUSTAINABILITY : {
    nature : "Normatif",
    traitement : "Grille SCI",
    ponderation : "≥10% SCI, facultatif Mali"
  }
};
Détail CRITÈRES DE CAPACITÉ :

javascript
CAPACITY_SUBCRITERIA = [
  {
    name : "Expérience similaire",
    data_source : "submission.documents.experience_certificates",
    scoring : "Nb marchés similaires × coefficient"
  },
  {
    name : "Capacité technique",
    data_source : "submission.documents.technical_capacity",
    scoring : "Équipement + personnel qualifié (grille)"
  },
  {
    name : "Références clients",
    data_source : "submission.documents.references",
    scoring : "Vérifiables, secteur humanitaire (bonus)"
  },
  {
    name : "Visite site fournisseur",
    data_source : "CHAMP HUMAIN (vide par défaut)",
    scoring : "Comité remplit après visite"
  },
  {
    name : "Évaluation échantillon",
    data_source : "CHAMP HUMAIN (vide par défaut)",
    scoring : "Comité remplit après test"
  }
];
Détail CRITÈRES COMMERCIAUX :

javascript
COMMERCIAL_SUBCRITERIA = [
  {
    name : "Prix unitaire",
    data_source : "submission.financial_offer.unit_prices",
    scoring : "Formule : (Prix_min / Prix_offre) × 100",
    weight : "≥35%"
  },
  {
    name : "Coût total",
    data_source : "SUM(unit_price × quantity) + livraison",
    scoring : "Formule idem",
    weight : "10-15%"
  },
  {
    name : "Délais livraison",
    data_source : "submission.delivery_time_days",
    scoring : "Plus court = meilleur (formule inverse)",
    weight : "5%"
  }
];
Validation pondérations :

javascript
function validateWeights(criteria) {
  const commercial = criteria.filter(c => c.type == "COMMERCIAL")
                            .reduce((sum, c) => sum + c.weight, 0);
  const sustainability = criteria.filter(c => c.type == "SUSTAINABILITY")
                                 .reduce((sum, c) => sum + c.weight, 0);
  const total = criteria.filter(c => c.type != "ESSENTIAL")
                        .reduce((sum, c) => sum + c.weight, 0);
  
  ASSERT commercial >= 40, "Critères commerciaux doivent être ≥40%";
  if (case.authority == "SCI") {
    ASSERT sustainability >= 10, "Critères durabilité SCI doivent être ≥10%";
  }
  ASSERT total == 100, "Somme pondérations doit être 100%";
}
RÈGLE M7 — Pondérations fixées AVANT l'ouverture
Source : Mali Code + SCI §5.3

Principe :
Critères + pondérations extraits du DAO/RFQ → figés dans EvaluationGrid → verrouillés au timestamp publication.

Workflow technique :

javascript
// ÉTAPE 1 : INGESTION (Écran 1)
const case = await ingestDAO(dao_document);
const criteria = await extractCriteria(dao_document);  // OCR + parsing
const user_validated_criteria = await validateWithUser(criteria);  // 30 sec max

// ÉTAPE 2 : CRÉATION EVALUATION GRID
const evaluation_grid = {
  grid_id : generateUUID(),
  case_id : case.case_id,
  criteria : user_validated_criteria,
  locked_at : null,  // Pas encore verrouillé
  locked_by : null
};

// ÉTAPE 3 : VERROUILLAGE (au moment de la publication DAO/RFQ)
evaluation_grid.locked_at = Date.now();
evaluation_grid.locked_by = current_user.user_id;

// À partir de ce moment :
// ❌ UI : champs critères + pondérations en lecture seule
// ❌ API : toute tentative de modification → 403 Forbidden
// ✅ LOG : tentative loggée (qui, quand, erreur)

// CORRECTION (si erreur détectée après verrouillage) :
// 1. Annuler la procédure (eWaiver + justification)
// 2. Relancer nouvelle procédure avec critères corrigés
// ❌ Aucune édition rétroactive possible
RÈGLE M8 — Le fait du dépôt prime sur l'interprétation
Source : Mali Code art. 71 + SCI §4.3.2

Principe :
L'outil enregistre le FAIT (qui, quand, comment). L'outil n'interprète jamais la validité. Le Comité juge.

Données capturées :

javascript
Submission {
  supplier_id : UUID,
  submission_datetime : Timestamp,  // Précision : seconde
  submission_mode : enum [
    "PHYSIQUE_URNE",      // Dépôt physique urne verrouillée
    "EMAIL_DEDIE",        // Email dédié procédure
    "ARIBA_NETWORK",      // ProSave (SCI)
    "PLATEFORME_ETAT"     // e-procurement État Mali
  ],
  submission_location : String,  // Lieu physique si applicable
  lot_ids : Array<UUID>,
  documents : Array<Document>,
  received_by : User_id,  // Qui a enregistré
  witness : User_id       // Témoin obligatoire (si physique)
}
Workflow horodatage :

javascript
// DÉPÔT PHYSIQUE (urne)
function recordPhysicalSubmission(envelope) {
  ASSERT committee_members.length >= 2, "2 membres minimum requis";
  
  return {
    submission_datetime : Date.now(),
    submission_mode : "PHYSIQUE_URNE",
    submission_location : office.address,
    received_by : committee_members[0].user_id,
    witness : committee_members[1].user_id,
    photo_envelope : optional_photo  // Recommandé
  };
}

// DÉPÔT EMAIL
function recordEmailSubmission(email) {
  return {
    submission_datetime : email.received_at,  // Timestamp serveur
    submission_mode : "EMAIL_DEDIE",
    received_by : procurement_email,
    witness : null  // Email = preuve automatique
  };
}

// DÉPÔT PLATEFORME
function recordPlatformSubmission(ariba_submission) {
  return {
    submission_datetime : ariba_submission.timestamp,  // Horodatage système
    submission_mode : "ARIBA_NETWORK",
    received_by : "SYSTEM",
    witness : "SYSTEM"
  };
}
Affichage + jugement humain :

text
Tableau pré-classement :
┌────────────────┬──────────────────────┬───────────┬──────────────┐
│ Soumissionnaire│ Date/Heure dépôt     │ Mode      │ Validité     │
├────────────────┼──────────────────────┼───────────┼──────────────┤
│ Fournisseur A  │ 2026-02-05 14:32:18  │ Email     │ ☐ Valide     │
│                │                      │           │ ☐ Hors délai │
│ Fournisseur B  │ 2026-02-05 16:45:02  │ Physique  │ ☐ Valide     │
│                │                      │           │ ☐ Hors délai │
└────────────────┴──────────────────────┴───────────┴──────────────┘

// Comité coche "Valide" ou "Hors délai" + justification
// Si "Hors délai" → conformity_status = NON_CONFORME
Interdiction machine :

javascript
// ❌ L'outil NE PEUT PAS calculer automatiquement "en retard"
// ❌ L'outil NE PEUT PAS éliminer une offre sur critère horaire seul
// ✅ Le Comité décide (avec traçabilité)
RÈGLE M9 — CBA et PV sont les artefacts centraux
Source : Mali Code + SCI §8.2

Principe :
Toute décision doit être traçable, documentée, reproductible via CBA (tableau comparatif) et PV (procès-verbal).

Structure CBA (Comparative Bid Analysis) :

javascript
CBA = {
  artifact_id : UUID,
  case_id : UUID,
  type : "CBA",
  format : "XLSX",  // Excel éditable
  version : Integer,
  status : enum ["DRAFT", "VALIDATED", "FINAL"],
  
  onglets : [
    {
      name : "Onglet 1 - Informations générales",
      fields : {
        titre_marche : case.title,
        reference : case.reference_number,
        date_ouverture : case.opening_date,
        membres_comite : CHAMP_HUMAIN  // Noms, signatures
      }
    },
    {
      name : "Onglet 2 - Liste soumissionnaires",
      fields : {
        soumissionnaires : case.submissions.map(s => ({
          nom : s.supplier.legal_name,
          date_depot : s.submission_datetime,
          heure_depot : s.submission_datetime,
          mode_depot : s.submission_mode,
          lots : s.lot_ids,
          conformite_admin : CHAMP_HUMAIN  // Comité valide
        }))
      }
    },
    {
      name : "Onglet 3 - Analyse technique",
      fields : {
        criteres_capacite : evaluation_grid.criteria.filter(c => c.type == "CAPACITY"),
        scores_par_soumissionnaire : case.submissions.map(s => s.evaluation_scores.capacity_criteria),
        visite_fournisseur : CHAMP_HUMAIN,
        evaluation_echantillon : CHAMP_HUMAIN
      }
    },
    {
      name : "Onglet 4 - Analyse financière",
      fields : {
        prix_unitaires : case.submissions.map(s => s.financial_offer.unit_prices),
        cout_total : case.submissions.map(s => s.financial_offer.total_cost),
        delais : case.submissions.map(s => s.delivery_time_days),
        scores_commerciaux : case.submissions.map(s => s.evaluation_scores.commercial_criteria),
        negociation : CHAMP_HUMAIN  // Si applicable
      }
    },
    {
      name : "Onglet 5 - Synthèse",
      fields : {
        notes_finales : case.submissions.map(s => s.evaluation_scores.total_score),
        classement_par_lot : case.submissions.map(s => s.evaluation_scores.rank_by_lot),
        recommandation : CHAMP_HUMAIN  // Appréciation qualitative Comité
      }
    }
  ],
  
  generated_at : Timestamp,
  generated_by : User_id,
  validated_at : Timestamp,
  validated_by : Array<User_id>  // SOD
};
Structure PV (Procès-Verbal) :

javascript
PV = {
  artifact_id : UUID,
  case_id : UUID,
  type : "PV",
  format : "DOCX",  // Word éditable → PDF final
  version : Integer,
  status : enum ["DRAFT", "FINAL"],
  
  sections : [
    {
      name : "En-tête",
      content : {
        organisation : case.authority,
        titre_marche : case.title,
        reference : case.reference_number
      }
    },
    {
      name : "Informations ouverture",
      content : {
        date : case.opening_date,
        heure : case.opening_time,
        lieu : case.opening_location,
        membres_comite : CHAMP_HUMAIN  // Noms, qualités, signatures
      }
    },
    {
      name : "Liste soumissionnaires",
      content : {
        soumissionnaires : case.submissions.map(s => ({
          nom : s.supplier.legal_name,
          heure_depot : s.submission_datetime,
          lots : s.lot_ids,
          documents_soumis : s.documents.map(d => d.document_type)
        })).sort_by_datetime()  // Ordre chronologique
      }
    },
    {
      name : "Résultat évaluation",
      content : {
        classement_par_lot : extracted_from_CBA_validated,
        fournisseur_retenu : case.decision.awarded_submissions,
        montants : case.decision.awarded_submissions.map(a => a.amount)
      }
    },
    {
      name : "Observations",
      content : CHAMP_HUMAIN  // Observations particulières Comité
    },
    {
      name : "Signatures",
      content : CHAMP_HUMAIN  // Signatures membres Comité
    }
  ],
  
  generated_at : Timestamp,
  generated_by : User_id,
  signed_at : Timestamp,
  digital_signature : String  // Hash cryptographique
};
Workflow export :

javascript
// ÉCRAN 3 : DÉCISION & EXPORTS

// 1. Export CBA
async function exportCBA(case) {
  const cba = generateCBA(case, "DRAFT");
  const excel_file = renderToExcel(cba);
  
  // Utilisateur revoit, corrige, complète champs humains
  await userReview(excel_file);
  
  // Validation
  cba.status = "VALIDATED";
  cba.validated_at = Date.now();
  cba.validated_by = evaluation_committee.members.map(m => m.user_id);
  
  // Export PDF final
  const pdf_file = renderToPDF(excel_file);
  return { cba, pdf_file };
}

// 2. Génération PV
async function generatePV(case, cba_validated) {
  const pv = generatePVFromCBA(case, cba_validated, "DRAFT");
  const word_file = renderToWord(pv);
  
  // Utilisateur complète champs humains (signatures)
  await userReview(word_file);
  
  // Export PDF horodaté et signé numériquement
  pv.status = "FINAL";
  pv.signed_at = Date.now();
  pv.digital_signature = generateHash(word_file);
  
  const pdf_file = renderToPDF(word_file, pv.digital_signature);
  return { pv, pdf_file };
}
Règles append-only :

javascript
// Chaque modification = nouvelle version
function updateCBA(cba_id, changes) {
  const current_cba = getCBA(cba_id);
  const new_cba = {
    ...current_cba,
    version : current_cba.version + 1,
    ...changes,
    updated_at : Date.now(),
    updated_by : current_user.user_id
  };
  
  // Ancienne version conservée
  archive(current_cba);
  
  // Nouvelle version créée
  save(new_cba);
  
  // Log
  log({
    action : "CBA_UPDATED",
    cba_id : cba_id,
    old_version : current_cba.version,
    new_version : new_cba.version,
    user : current_user.user_id,
    timestamp : Date.now(),
    changes : diff(current_cba, new_cba)
  });
}
II. LEXIQUE CANONIQUE (SCHÉMAS JSON PRODUCTION-READY)
Hiérarchie des objets
text
Case (Processus compétitif)
├── Lot[] (Subdivisions marché)
│   └── Item[] (Articles/services spécifiques)
├── Criterion[] (Critères d'évaluation)
├── Submission[] (Offres déposées)
│   ├── Supplier (Fournisseur - lien uniquement)
│   └── Document[] (Documents soumis)
├── EvaluationGrid (Grille figée)
├── Decision (Attribution)
└── Artifact[] (CBA, PV - versions horodatées)
Schémas détaillés
json
{
  "Case": {
    "case_id": "UUID",
    "procedure_type": "enum [DAO | RFQ | RFP | Open_Tender | Formal_Quote | Simple_Quote | Single_Quote]",
    "category": "enum [TRAVAUX | FOURNITURES | SERVICES | PI]",
    "title": "String",
    "reference_number": "String",
    "estimated_value": "Float",
    "currency": "enum [FCFA | USD | EUR]",
    "authority": "enum [MALI_STATE | SCI | UN | OTHER]",
    "funding_source": "String",
    "publication_date": "Timestamp",
    "opening_date": "Timestamp",
    "opening_location": "String",
    "lots": "Array<Lot>",
    "criteria": "Array<Criterion>",
    "submissions": "Array<Submission>",
    "evaluation_grid": "EvaluationGrid",
    "decision": "Decision (nullable)",
    "artifacts": "Array<Artifact>",
    "created_at": "Timestamp",
    "created_by": "User_id"
  },
  
  "Lot": {
    "lot_id": "UUID",
    "case_id": "UUID",
    "lot_number": "Integer",
    "description": "String",
    "estimated_value": "Float",
    "items": "Array<Item>",
    "awarded_to": "UUID (submission_id, nullable)",
    "award_amount": "Float (nullable)"
  },
  
  "Item": {
    "item_id": "UUID",
    "lot_id": "UUID",
    "description": "String",
    "quantity": "Float",
    "unit": "String",
    "unit_price_estimated": "Float (nullable)",
    "specifications": "String"
  },
  
  "Criterion": {
    "criterion_id": "UUID",
    "case_id": "UUID",
    "type": "enum [ESSENTIAL | CAPACITY | COMMERCIAL | SUSTAINABILITY]",
    "name": "String",
    "description": "String",
    "weight": "Float (0-100, 0 si ESSENTIAL)",
    "calculation_method": "String (formule si COMMERCIAL)",
    "sub_criteria": "Array<Criterion> (récursif)"
  },
  
  "Submission": {
    "submission_id": "UUID",
    "case_id": "UUID",
    "supplier_id": "UUID",
    "lot_ids": "Array<UUID>",
    "submission_datetime": "Timestamp",
    "submission_mode": "enum [PHYSIQUE_URNE | EMAIL_DEDIE | ARIBA_NETWORK | PLATEFORME_ETAT]",
    "submission_location": "String (nullable)",
    "documents": "Array<Document>",
    "conformity_status": "enum [CONFORME | NON_CONFORME | EN_ATTENTE]",
    "conformity_notes": "String (nullable)",
    "evaluation_scores": {
      "essential_criteria": "Object {criterion_id: bool}",
      "capacity_criteria": "Object {criterion_id: Float}",
      "commercial_criteria": "Object {criterion_id: Float}",
      "sustainability_criteria": "Object {criterion_id: Float}",
      "total_score": "Float (0-100)",
      "rank_by_lot": "Object {lot_id: Integer}"
    },
    "received_by": "User_id",
    "witness": "User_id (nullable)"
  },
  
  "Supplier": {
    "supplier_id": "UUID",
    "legal_name": "String",
    "commercial_name": "String (nullable)",
    "registration_number": "String",
    "tax_id": "String",
    "address": "String",
    "country": "String",
    "contact_email": "String",
    "contact_phone": "String",
    "verification_status": "enum [PENDING | APPROVED | SUSPENDED | BLOCKED]",
    "verification_reference": "String (VCRN si SCI)",
    "verification_date": "Timestamp (nullable)",
    "created_at": "Timestamp"
  },
  
  "Document": {
    "document_id": "UUID",
    "submission_id": "UUID",
    "document_type": "enum [TECHNIQUE | FINANCIER | ADMINISTRATIF]",
    "filename": "String",
    "file_path": "String",
    "file_size_bytes": "Integer",
    "mime_type": "String",
    "upload_datetime": "Timestamp"
  },
  
  "EvaluationGrid": {
    "grid_id": "UUID",
    "case_id": "UUID",
    "criteria": "Array<Criterion>",
    "locked_at": "Timestamp",
    "locked_by": "User_id",
    "evaluation_committee": "Array<User_id>",
    "evaluation_method": "enum [MOINS_DISANT | MIEUX_DISANT]"
  },
  
  "Decision": {
    "decision_id": "UUID",
    "case_id": "UUID",
    "awarded_submissions": "Array<Object {lot_id: UUID, submission_id: UUID, amount: Float}>",
    "decision_date": "Timestamp",
    "decision_rationale": "String",
    "approved_by": "Array<User_id>",
    "cba_artifact_id": "UUID",
    "pv_artifact_id": "UUID"
  },
  
  "Artifact": {
    "artifact_id": "UUID",
    "case_id": "UUID",
    "type": "enum [CBA | PV]",
    "format": "enum [XLSX | DOCX | PDF]",
    "version": "Integer",
    "file_path": "String",
    "status": "enum [DRAFT | VALIDATED | FINAL]",
    "generated_at": "Timestamp",
    "generated_by": "User_id",
    "validated_at": "Timestamp (nullable)",
    "validated_by": "Array<User_id> (nullable)",
    "digital_signature": "String (nullable)"
  }
}
III. GRAMMAIRE PROCUREMENT (WORKFLOW DÉTAILLÉ)
Séquence canonique V1 (Couche A)
text
┌─────────────────────────────────────────────────────────────────┐
│ ÉCRAN 1 : INGESTION                                             │
│ Temps estimé : 5-10 minutes                                     │
├─────────────────────────────────────────────────────────────────┤
│ INPUT :                                                         │
│ - Document DAO/RFQ/RFP (PDF/Word)                              │
│ - Annexes (cahier des charges, TDR)                            │
│                                                                 │
│ PROCESSUS :                                                     │
│ 1. Upload document                                              │
│ 2. OCR + extraction structure automatique :                     │
│    - Lots                                                       │
│    - Critères d'évaluation                                      │
│    - Pondérations                                               │
│    - Règles d'élimination                                       │
│ 3. Validation humaine (30 sec)                                  │
│    IF extraction_confidence < 90%                               │
│      THEN fallback_manuel (< 2 min)                             │
│ 4. Détection automatique profil d'évaluation                    │
│    IF incertain THEN demande_confirmation (1 clic)              │
│ 5. Création Case + Lots + Criteria                              │
│ 6. Création EvaluationGrid                                      │
│ 7. Verrouillage EvaluationGrid (timestamp + user_id)            │
│                                                                 │
│ OUTPUT :                                                        │
│ ✅ Case créé                                                    │
│ ✅ EvaluationGrid figée                                         │
│ ✅ Système prêt à recevoir soumissions                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ ÉTAPE INTERMÉDIAIRE : ENREGISTREMENT SOUMISSIONS                │
│ (Peut se faire en continu, avant Écran 2)                       │
├─────────────────────────────────────────────────────────────────┤
│ PROCESSUS (par soumission) :                                    │
│ 1. Réception offre (physique/email/plateforme)                  │
│ 2. Enregistrement horodaté :                                    │
│    - Supplier_id                                                │
│    - Submission_datetime (précision seconde)                    │
│    - Submission_mode                                            │
│    - Lot_ids                                                    │
│    - Documents (upload)                                         │
│    - Received_by + Witness (si physique)                        │
│ 3. Création Submission (status = EN_ATTENTE)                    │
│                                                                 │
│ OUTPUT :                                                        │
│ ✅ N Submissions enregistrées                                   │
│ ✅ Horodatage strict                                            │
│ ✅ Documents stockés                                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ ÉCRAN 2 : STRUCTURATION                                        │
│ Temps estimé : 30-60 minutes (selon nb soumissions)             │
├─────────────────────────────────────────────────────────────────┤
│ INPUT :                                                         │
│ - Case avec N Submissions                                       │
│                                                                 │
│ PROCESSUS :                                                     │
│ 1. Vérification conformité essentielle                          │
│    FOR EACH submission :                                        │
│      IF ANY(essential_criteria) == FALSE                        │
│        THEN conformity_status = NON_CONFORME                    │
│      ELSE conformity_status = CONFORME                          │
│                                                                 │
│ 2. Comptage offres conformes                                    │
│    conforming_count = COUNT(conformity_status == CONFORME)      │
│    IF conforming_count < min_required                           │
│      THEN ALERT + options (prolonger/relancer/eWaiver)          │
│                                                                 │
│ 3. Extraction données techniques + financières                  │
│    FOR EACH submission WHERE conformity_status == CONFORME :    │
│      - Capacité : expérience, références, équipement            │
│      - Commercial : prix unitaires, coût total, délais          │
│      - Durabilité : fournisseur local, certifications           │
│                                                                 │
│ 4. Calcul notes automatique                                     │
│    FOR EACH criterion WHERE type IN [COMMERCIAL, SUSTAINABILITY]:│
│      score = apply_formula(criterion, submission)               │
│    FOR EACH criterion WHERE type == CAPACITY :                  │
│      score = pre_fill_from_documents(criterion, submission)     │
│      // Champs humains (visite, échantillon) restent vides      │
│                                                                 │
│ 5. Calcul note finale                                           │
│    total_score = SUM(score × weight) for all criteria           │
│                                                                 │
│ 6. Classement par lot                                           │
│    FOR EACH lot :                                               │
│      rank_submissions_by_total_score DESC                       │
│                                                                 │
│ 7. Affichage tableau consolidé (CBA interne)                    │
│    Colonnes :                                                   │
│    - Soumissionnaire                                            │
│    - Lot                                                        │
│    - Conformité                                                 │
│    - Critères techniques (scores)                               │
│    - Critères financiers (scores)                               │
│    - Critères durabilité (scores)                               │
│    - Note finale                                                │
│    - Classement                                                 │
│    - Visite fournisseur (VIDE)                                  │
│    - Évaluation échantillon (VIDE)                              │
│    - Appréciation comité (VIDE)                                 │
│                                                                 │
│ 8. Corrections manuelles possibles                              │
│    Utilisateur peut :                                           │
│    - Corriger extraction (si erreur)                            │
│    - Compléter champs humains                                   │
│    Toute correction loggée (append-only)                        │
│                                                                 │
│ OUTPUT :                                                        │
│ ✅ Tableau consolidé complet                                    │
│ ✅ Notes calculées                                              │
│ ✅ Classement par lot établi                                    │
│ ✅ Prêt pour export CBA                                         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ ÉCRAN 3 : DÉCISION & EXPORTS                                   │
│ Temps estimé : 15-30 minutes                                    │
├─────────────────────────────────────────────────────────────────┤
│ INPUT :                                                         │
│ - Tableau consolidé validé (Écran 2)                            │
│                                                                 │
│ PROCESSUS :                                                     │
│ 1. Vue synthèse décisionnelle                                   │
│    - Classement final par lot                                   │
│    - Constat factuel : "Offre moins-disante conforme :         │
│      Fournisseur X, Lot Y, Montant Z"                           │
│                                                                 │
│ 2. Export CBA officiel (1 clic)                                 │
│    - Génération Excel pré-rempli (5 onglets)                    │
│    - Format Save the Children ou État Mali                      │
│    - Utilisateur revoit, corrige, complète champs humains       │
│    - Clic "Valider" → CBA.status = VALIDATED (horodaté)         │
│    - Export PDF final                                           │
│                                                                 │
│ 3. Génération PV officielle (1 clic)                            │
│    - Génération Word pré-rempli (à partir CBA validé)           │
│    - Utilisateur complète signatures                            │
│    - Export PDF horodaté + signature numérique                  │
│                                                                 │
│ 4. Création Decision                                            │
│    - Attribution par lot (submission_id + montant)              │
│    - Approbations SOD (selon montant)                           │
│    - Timestamp décision                                         │
│                                                                 │
│ 5. Archivage automatique Couche B                               │
│    Emit to MARKET_INTEL :                                       │
│    - source_type = "procurement"                                │
│    - fournisseur = awarded_supplier.legal_name                  │
│    - categorie = case.category                                  │
│    - items = awarded_lots.items                                 │
│    - prix = awarded_submissions.unit_prices                     │
│    - zone = case.location                                       │
│    - delais = awarded_submissions.delivery_time                 │
│    - date = case.decision_date                                  │
│    - lien_cas = case.case_id                                    │
│                                                                 │
│ OUTPUT :                                                        │
│ ✅ CBA validé (Excel + PDF)                                     │
│ ✅ PV généré (Word + PDF signé)                                 │
│ ✅ Decision créée                                               │
│ ✅ Couche B alimentée automatiquement                           │
│ ✅ Processus terminé                                            │
└─────────────────────────────────────────────────────────────────┘
IV. RÈGLE D'OR (inchangée)
text
┌────────────────────────────────────────────────────┐
│                                                    │
│  LA MACHINE PRÉPARE                                │
│  L'HUMAIN ARBITRE                                  │
│  LE SYSTÈME SE SOUVIENT                            │
│                                                    │
└────────────────────────────────────────────────────┘
