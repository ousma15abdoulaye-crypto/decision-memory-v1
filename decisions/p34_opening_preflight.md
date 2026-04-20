# DMS — P3.4 opening preflight (document autonome)

**Phase** : P3.4 — MatrixRow Builder / Summary  
**Baseline** : `main` aligné `origin/main` après merge P3.3 (PR #428)  
**Branche** : `feat/p3-4-matrixrow-builder-summary`  
**HEAD matériel vérifié** : `417f1149`  
**Auteur contenu CTO (blocs P1–P8 source)** : CTO Senior DMS — mandat 2026-04-18  
**Date exécution agent (git + P1)** : 2026-04-19  
**Révision** : 2026-04-19 — intégralité P2–P7, réserves CTO Senior, rectification Q1 `technical_threshold_mode`, notes Étape 0 (E0.1–E0.5 partielles)

---

## Rapport d'exécution matériel (séquence Git + vérifs P1)


| Étape           | Commande / action                                                                                    | Résultat                                                    |
| --------------- | ---------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Sync            | `git checkout main` ; `git fetch origin` ; `git pull --ff-only origin main`                          | Fast-forward `f4bc3920` → `417f1149` (`feat(P3.3): … #428`) |
| Alembic         | `alembic heads`                                                                                      | **1 head** : `101_p32_dao_criteria_scoring_schema (head)`   |
| Fichiers suivis | `git status --porcelain` filtré (hors `??`)                                                          | **Aucune modification** sur fichiers indexés                |
| Non suivis      | `git status -sb`                                                                                     | **Nombreux** `??` — voir §Réserves CTO #1                   |
| Branche P3.4    | `git checkout -b feat/p3-4-matrixrow-builder-summary`                                                | Créée depuis `417f1149`                                     |
| HEAD récent     | `git log --oneline -5`                                                                               | `417f1149` feat(P3.3) #428 ; `682e8ee7` … `685b2139`        |
| P1 grep         | `MatrixRow`, `matrix_row_builder`, `MatrixSummary`, `matrix_summary` dans `*.py`                     | **Aucune occurrence**                                       |
| P1 grep         | `build_matrix_participants_and_excluded`, `populate_assessments_from_m14`, `out.matrix_participants` | **Présents** (voir P1.3)                                    |


**Interprétation** : index et fichiers **suivis** propres ; `git status` complet non « clean » à cause des `??` massifs (hygiène locale).

---

## INTÉGRATION DES ARBITRAGES CTO (verrouillés)


| Arbitrage                                               | Décision          | Impact P3.4                                                                                |
| ------------------------------------------------------- | ----------------- | ------------------------------------------------------------------------------------------ |
| Q1 — bascule globale `INFORMATIVE` par défaut           | **NON**           | `technical_threshold_mode` **modélisé** dans `MatrixRow` ; défaut final = arbitrage séparé |
| Q2 — P3.4 / P3.4B / P3.4C                               | **OUI**           | Décomposition gravée ; P3.4 = MatrixRow + Summary + Explainability                         |
| Q3 — `*_system` / `*_override` / `*_effective` dès P3.4 | **OUI** (contrat) | Champs définis, non actifs ; `*_effective = *_system` tant que P3.4B absent                |
| Q4 — Committee Review Agent P4                          | Trajectoire       | Non ouvert tant que P3.4B non cadré                                                        |
| Q5 — Manifeste avant preflight                          | **NON**           | Preflight direct                                                                           |
| **G1**                                                  | Gravé             | Édition directe de `*_effective` **interdite** (UI future incluse)                         |
| **G2**                                                  | Gravé             | Taxonomie `correction_nature` obligatoire dans le contrat override                         |
| **P6ter**                                               | Exigé             | Revue comité / corrections — voir bloc P6ter                                               |


### Rectification CTO Senior (2026-04-19) — Q1 valeur technique transitoire

En l’absence d’arbitrage formel sur le défaut final de `technical_threshold_mode` :

- **Lecture** : `process_workspaces.technical_threshold_mode` **si** la colonne existe à l’avenir ; sinon pas de valeur DB.
- **Défaut transitoire P3.4** : `**MANDATORY`** (conservation doctrine P3.2 §6.4 stricte — pas de renversement implicite vers `INFORMATIVE`).
- **Transparence** : si le défaut transitoire est appliqué (pas de colonne / pas de valeur explicite résolue), ajouter à `MatrixRow.warning_flags` le code `**TECHNICAL_THRESHOLD_MODE_DEFAULT_APPLIED`**.

`INFORMATIVE` comme défaut **ne** s’applique **que** sur arbitrage explicite CTO principal documenté.

---

## Réserves CTO Senior (2026-04-19) — actables avant code métier


| #      | Réserve                                                  | Action opposable                                                                                                                                                                                                                                                              |
| ------ | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **#1** | `??` massifs — `git add .` interdit (Context Anchor §13) | Chaque `git add` **explicite** ; PR P3.4 **uniquement** mandat (service builder, patch minimal pipeline, tests, amendement `PipelineV5Result`) ; pas de `data/`, rapports, scripts opportunistes ; enrichissement `.gitignore` = **chantier séparé**, pas glissé dans PR P3.4 |
| **#2** | Extension `PipelineV5Result`                             | **Avant** `build_matrix_rows` : localiser modèle, ajouter `matrix_rows` / `matrix_summary`, valider sérialisation, `grep` usages — voir §E0.2                                                                                                                                 |
| **#3** | `technical_threshold_mode`                               | Règle transitoire §Rectification Q1 ci-dessus                                                                                                                                                                                                                                 |
| **#4** | Document autonome                                        | **Le présent fichier** contient P2–P7 intégraux (sections suivantes)                                                                                                                                                                                                          |
| **#5** | Ligne d’insertion exacte                                 | **Après** l’appel `populate_assessments_from_m14` et gestion d’erreurs associée sur **HEAD courant** — voir §E0.3 ; sur `417f1149`, l’appel occupe **L1453–L1457**                                                                                                            |


---

## Étape 0 — Notes d’investigation (agent, HEAD `417f1149`)

**Clôture E0.2 / E0.5 / E0.6 / E0.7** (notes courtes opposables, 2026-04-19) : voir `**decisions/p34_e0_investigation_closure.md`**.


| Tâche    | Livrable                                                                                                                                                                                                                                                                                           |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **E0.1** | Présent fichier complété (P2–P7 intégraux) — **fait** (cette révision)                                                                                                                                                                                                                             |
| **E0.2** | `PipelineV5Result` : classe `**BaseModel`** dans `src/services/pipeline_v5_service.py` **L212–L241** ; `extra="forbid"` — tout nouveau champ doit être nommé explicitement ; usages : `grep PipelineV5Result` (principalement `run_pipeline_v5` et tests)                                          |
| **E0.3** | Fin d’appel bridge : bloc `try:` **L1452–L1457** ; insertion P3.4 **après** succès bridge et **avant** `out.completed = True` (**L1471**), en respectant le flux d’erreurs existant                                                                                                                |
| **E0.4** | Colonne `process_workspaces.technical_threshold_mode` : **absente** du schéma connu à date ; migration **101** ajoute `technical_qualification_threshold` **uniquement** (`alembic/versions/101_p32_dao_criteria_scoring_schema.py`). Le builder appliquera la règle transitoire §Rectification Q1 |
| **E0.5** | Audit `??` / `.gitignore` : **hors PR P3.4** ; documenter séparément si besoin                                                                                                                                                                                                                     |
| **E0.6** | `run_id` / `pipeline_run_id` dans `run_pipeline_v5` : **absents** → décision `**uuid4()`** une fois par invocation ; détail dans `p34_e0_investigation_closure.md`                                                                                                                                 |
| **E0.7** | Convention chemins modèles : `**src/procurement/matrix_models.py`** (aligné `m14_evaluation_models.py`) ; détail dans `p34_e0_investigation_closure.md`                                                                                                                                            |


---

## BLOC P1 — POINT D'ENTRÉE ACTUEL DE LA MATRICE

### P1.1 — Objectif

Identifier où, dans la base de code post-P3.3, la matrice est construite et par quel chemin. Pas d'hypothèse — preuves fichier:ligne.

### P1.2 — Hypothèses → statut post-grep (HEAD `417f1149`)


| Hypothèse                                                                          | Statut       | Preuve                                                          |
| ---------------------------------------------------------------------------------- | ------------ | --------------------------------------------------------------- |
| `build_matrix_participants_and_excluded` construit `mp_list` / `ex_list`           | **CONFIRMÉ** | `src/services/pipeline_v5_service.py` L630–L722                 |
| `out.matrix_participants = mp_list` (+ payload)                                    | **CONFIRMÉ** | L1427–L1430                                                     |
| `save_evaluation` persiste le payload                                              | **CONFIRMÉ** | L1431–L1432                                                     |
| `populate_assessments_from_m14(strict_matrix_participants=True, strict_uuid=True)` | **CONFIRMÉ** | L1453–L1457 ; définition `src/services/m14_bridge.py` L414–L445 |
| Absence builder `MatrixRow` canonique                                              | **CONFIRMÉ** | grep `*.py`                                                     |
| Absence `MatrixSummary` / `matrix_summary`                                         | **CONFIRMÉ** | grep `*.py`                                                     |


### P1.3 — Tableau d'entrée de chantier (Étape 0)


| Fichier                  | Fonction                                 | Ligne     | Appelant          | Objet entrant                                                         | Objet sortant        | Rôle                                             |
| ------------------------ | ---------------------------------------- | --------- | ----------------- | --------------------------------------------------------------------- | -------------------- | ------------------------------------------------ |
| `pipeline_v5_service.py` | `build_matrix_participants_and_excluded` | 630–722   | `run_pipeline_v5` | `report`, `bundle_roles`, …                                           | `mp_list`, `ex_list` | participants matrice (liste flat, pas MatrixRow) |
| `pipeline_v5_service.py` | `save_evaluation` (repo)                 | 1431–1432 | `run_pipeline_v5` | payload                                                               | id eval doc          | persistance `scores_matrix` brut                 |
| `m14_bridge.py`          | `populate_assessments_from_m14`          | 414–445   | `run_pipeline_v5` | `workspace_id`                                                        | `BridgeResult`       | persistance cellules `criterion_assessments`     |
| **À trouver / à créer**  | `build_matrix_rows` (ou équivalent)      | N/A       | —                 | `criterion_assessments`, `process_workspaces`, `SupplierEvaluation[]` | `MatrixRow[]`        | **composant P3.4**                               |


### P1.4 — Conclusion P1

Le pipeline V5 post-P3.3 produit :

- une liste de participants matrice (`matrix_participants`)
- des cellules persistées (`criterion_assessments`)
- des scores agrégés (`scores_matrix` dans `evaluation_documents`)

Il **ne produit pas** aujourd'hui :

- un objet canonique `MatrixRow` par vendor avec tous ses attributs d'affichage et d'auditabilité
- un objet canonique `MatrixSummary` consolidé

**P3.4 crée ces deux objets.** Il **ne remplace pas** les composants existants, il **projette** leur contenu en forme canonique lisible.

---

## BLOC P2 — ÉTATS MÉTIER RÉELLEMENT DISPONIBLES

### P2.1 — Sources de statuts et flags (post-P3.3)


| Source                                                 | Champ                                       | Valeurs possibles                                               | Consommable `MatrixRow` ?                                                                              |
| ------------------------------------------------------ | ------------------------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| P3.1B `EligibilityVerdict`                             | `status`                                    | `ELIGIBLE`, `INELIGIBLE`, `PENDING`                             | OUI — `eligibility_status`                                                                             |
| P3.1B `GateOutput`                                     | `excluded_vendor_ids`, `pending_vendor_ids` | listes UUID                                                     | OUI — croisement pour traçage                                                                          |
| P3.1B `GateOutput`                                     | `failed_gates[]`, motifs                    | liste                                                           | OUI — `exclusion_reason_codes`                                                                         |
| P3.2 `SupplierEvaluation`                              | `eliminated`                                | bool                                                            | OUI — fusionné avec `eligibility_status`                                                               |
| P3.2 `SupplierEvaluation`                              | `elimination_reason`                        | str (ex: `UNQUALIFIED_TECHNICAL:score=42<threshold=50`)         | OUI — `exclusion_reason_codes` + motif                                                                 |
| P3.2 `FamilyScore.qualified`                           | bool / NULL                                 | TECH uniquement                                                 | OUI — flag `TECH_QUALIFIED` / `TECH_UNQUALIFIED`                                                       |
| P3.2 `FamilyScore.null_reason`                         | str                                         | `UNQUALIFIED_TECHNICAL`, `NO_OFFER`, autres                     | Oui — enrichit `exclusion_reason_codes`                                                                |
| P3.2 `FamilyScore.family_score`                        | float / NULL                                | 0–100 / NULL                                                    | Oui — `technical_score_system`, etc.                                                                   |
| P3.2 `FamilyScore.family_weighted_score`               | float / NULL                                | 0–50 / 0–40 / 0–10 / NULL                                       | Oui — composantes du total                                                                             |
| P3.2 `SupplierEvaluation.total_weighted_score`         | float / NULL                                | 0–100 / NULL                                                    | Oui — `total_score_system`                                                                             |
| P3.2 `SupplierEvaluation.flags[]`                      | liste str                                   | `BELOW_TECHNICAL_THRESHOLD`, autres                             | Oui — `warning_flags`                                                                                  |
| P3.3 `QualifiedPrice.flags[]`                          | liste str                                   | `PRICE_AMBIGUOUS`, `PRICE_NEGATIVE`, `CURRENCY_MISSING`, autres | Oui — `warning_flags`                                                                                  |
| P3.3 `QualifiedPrice.human_review_required`            | bool                                        | true / false                                                    | Oui — `MatrixRow.human_review_required`                                                                |
| P3.3 `PriceAmbiguousError` propagée                    | événement                                   | erreur levée                                                    | Oui — devient `rank_status = NOT_COMPARABLE` + flag                                                    |
| `criterion_assessments.flags[]`                        | liste str                                   | divers                                                          | Oui — agrégé par vendor                                                                                |
| `process_workspaces.technical_qualification_threshold` | float                                       | 0–100                                                           | Oui — affiché pour transparence                                                                        |
| **Non encore disponible**                              | `technical_threshold_mode`                  | `INFORMATIVE` / `MANDATORY`                                     | à modéliser P3.4 ; défaut transitoire = `MANDATORY` + flag si défaut appliqué (voir §Rectification Q1) |


### P2.2 — Sources de preuves documentaires


| Source                                   | Champ  | Usage `MatrixRow`                         |
| ---------------------------------------- | ------ | ----------------------------------------- |
| P3.2 `SubCriterionScore.evidence_refs[]` | UUID[] | agrégation dans `MatrixRow.evidence_refs` |
| P3.3 `QualifiedPrice.evidence_refs[]`    | UUID[] | inclus dans `MatrixRow.evidence_refs`     |
| `bundle_documents.id`                    | UUID   | traçabilité documentaire                  |


### P2.3 — Ce qui manque (à créer en P3.4)

- statut de **comparabilité** au niveau ligne (`total_comparability_status`)
- statut de **rang** au niveau ligne (`rank_status`)
- statut de **cohorte** au niveau summary (`cohort_comparability_status`)
- champs override placeholders (`*_score_override`, `*_score_effective`, `has_any_override`)
- référence `pipeline_run_id` par ligne
- référence `matrix_revision_id` par ligne (préparatoire P3.4B)

---

## BLOC P3 — MENSONGES ACTUELS POTENTIELS

### P3.1 — Catalogue des risques de sortie trompeuse


| #   | Risque                                                                                             | Localisation potentielle                         | Criticité             | Règle P3.4 qui l'élimine                                                                                            |
| --- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------ | --------------------- | ------------------------------------------------------------------------------------------------------------------- |
| M1  | Vendor exclu avec `total_score` non-NULL affiché                                                   | `scores_matrix` brut dans `evaluation_documents` | HAUTE                 | `MatrixRow.total_score_system = NULL` si `eliminated = True` — règle assertive dans builder                         |
| M2  | Rang numérique sur cohorte asymétrique (certains vendors avec `commercial = NULL`, d'autres non)   | projection naive `sort by total DESC`            | HAUTE                 | Règle de rang §P5 : si cohorte asymétrique détectée → `rank = NULL, rank_status = NOT_COMPARABLE` pour tous         |
| M3  | `NULL` converti en `0` par sérialisation JSON / cast SQL / default UI                              | couche serialization, frontend                   | HAUTE                 | `MatrixRow` en Pydantic v2 strict avec `Optional[float]` explicites, sérialisation `None` → `null` JSON, jamais `0` |
| M4  | `INCOMPLETE` et `EXCLUDED` confondus dans l'affichage                                              | enum mal conçu, flag unique pour deux réalités   | HAUTE                 | Enum séparé `rank_status` avec `EXCLUDED` et `INCOMPLETE` distincts, documenté en §P5                               |
| M5  | Flag P3.3 (`PRICE_AMBIGUOUS`, `human_review_required`) écrasé par un agrégat                       | fusion `flags[]` non-idempotente                 | MOYENNE               | `MatrixRow.warning_flags` en `list[str]` append-only, union non-destructive de toutes les sources                   |
| M6  | Gagnant implicite émergeant par tri alphabétique / ordre insertion                                 | pas de `rank` explicite, ordre UI trompeur       | MOYENNE               | Toute `MatrixRow` porte `rank` explicite (même NULL), pas de "1er par défaut"                                       |
| M7  | Override affiché comme valeur système (pas de distinction visuelle)                                | pas de champs `*_system` vs `*_effective`        | HAUTE (futur P3.4B)   | Contrat `MatrixRow` prévoit les 3 niveaux (`system`, `override`, `effective`) dès P3.4                              |
| M8  | Régularisation non signalée (vendor régularisé affiché comme "PASS" sans marque de régularisation) | pas de champ `regularization_history`            | MOYENNE (futur P3.4C) | `MatrixRow.regularization_summary` prévu dès P3.4, rempli par P3.4C                                                 |
| M9  | Total partiel "pour information" affiché pour un vendor sous seuil technique mandatory             | bug de conversion si mode bascule                | HAUTE                 | Convention P3.2 §6.4 maintenue en mode `MANDATORY` : `total_score_system = NULL` strict                             |
| M10 | Confusion entre éligibilité P3.1B et qualification technique P3.2 dans le motif d'exclusion        | fusion hâtive de `elimination_reason`            | MOYENNE               | `exclusion_reason_codes: list[str]` ordonnée par source : `[eligibility.*, technical.*, commercial.*]`              |


### P3.2 — Principe directeur gravé

> **Un score non affichable est `NULL`. Un rang non calculable est `NULL`. Un statut sans base est explicitement `EXCLUDED` ou `INCOMPLETE` ou `NOT_COMPARABLE`, jamais `0` et jamais absent.**

---

## BLOC P4 — CONTRAT CIBLE `MatrixRow` ET `MatrixSummary`

### P4.1 — Contrat `MatrixRow` V1 (contrat opposable P3.4, champs override préparatoires inactifs)

```
MatrixRow {
  // --- IDENTITÉ ---
  workspace_id              : UUID
  bundle_id                 : UUID                 // clé technique — traçabilité bijective
  supplier_name             : str                  // source : bundle.vendor_name_raw normalisé
  pipeline_run_id           : UUID                 // trace run pipeline
  matrix_revision_id        : UUID                 // trace revision matrice (P3.4B utile)
  computed_at               : timestamp

  // --- STATUT ÉLIGIBILITÉ (de P3.1B) ---
  eligibility_status        : enum(ELIGIBLE, INELIGIBLE, PENDING, REGULARIZATION_PENDING)
  eligibility_reason_codes  : list[str]            // ex: ["INELIGIBLE:NIF_EXPIRED"]

  // --- SCORES SYSTÈME (de P3.2 / P3.3) ---
  technical_score_system    : float | NULL         // 0–50, pondéré famille
  commercial_score_system   : float | NULL         // 0–40, pondéré famille
  sustainability_score_system : float | NULL       // 0–10, pondéré famille
  total_score_system        : float | NULL         // 0–100

  // --- SCORES OVERRIDE (P3.4B préparatoire, inactif en P3.4) ---
  technical_score_override  : float | NULL         // NULL tant que P3.4B absent
  commercial_score_override : float | NULL         // idem
  sustainability_score_override : float | NULL     // idem
  total_score_override      : float | NULL         // idem

  // --- SCORES EFFECTIFS (vue publiée) ---
  technical_score_effective : float | NULL         // = override ?? system  — en P3.4 = system
  commercial_score_effective : float | NULL        // idem
  sustainability_score_effective : float | NULL    // idem
  total_score_effective     : float | NULL         // idem

  // --- COMPARABILITÉ ---
  total_comparability_status : enum(COMPARABLE, NON_COMPARABLE, INCOMPLETE)
  technical_threshold_mode  : enum(INFORMATIVE, MANDATORY)
                                                   // modélisé, défaut transitoire MANDATORY + flag si défaut appliqué
  technical_threshold_value : float | NULL         // copié de process_workspaces
  technical_qualified       : bool | NULL          // miroir FamilyScore.qualified, TECH

  // --- RANG ---
  rank                      : int | NULL           // rang global dans la cohorte comparable
  rank_status               : enum(RANKED, EXCLUDED, PENDING, NOT_COMPARABLE, INCOMPLETE)

  // --- MOTIFS ET FLAGS ---
  exclusion_reason_codes    : list[str]            // ordonné, source-tagged
  warning_flags             : list[str]            // union append-only des flags amont
  human_review_required     : bool                 // OR logique de toutes sources

  // --- OVERRIDE PLACEHOLDERS (P3.4B préparatoire) ---
  has_any_override          : bool                 // false par construction en P3.4
  override_summary          : list[OverrideRef] | []  // vide en P3.4
  last_override_at          : timestamp | NULL     // NULL en P3.4

  // --- RÉGULARISATION PLACEHOLDERS (P3.4C préparatoire) ---
  regularization_summary    : list[RegularizationRef] | []  // vide en P3.4
  has_regularization_history : bool                // false par construction en P3.4

  // --- PREUVES ---
  evidence_refs             : list[UUID]           // agrégation preuves critères + prix
}
```

### P4.2 — Contrat `MatrixSummary`

```
MatrixSummary {
  workspace_id              : UUID
  pipeline_run_id           : UUID
  matrix_revision_id        : UUID
  computed_at               : timestamp

  // --- COMPTAGES ÉLIGIBILITÉ ---
  total_bundles             : int
  count_eligible            : int
  count_ineligible          : int
  count_pending             : int
  count_regularization_pending : int   // 0 en P3.4, utile P3.4C

  // --- COMPTAGES COMPARABILITÉ ---
  count_comparable          : int
  count_non_comparable      : int
  count_incomplete          : int

  // --- COMPTAGES RANG ---
  count_ranked              : int
  count_excluded            : int
  count_pending_rank        : int
  count_not_comparable_rank : int
  count_incomplete_rank     : int

  // --- STATUT COHORTE ---
  cohort_comparability_status : enum(FULLY_COMPARABLE, PARTIALLY_COMPARABLE, NOT_COMPARABLE)

  // --- FLAGS GLOBAUX ---
  has_any_critical_flag     : bool                 // OR sur warning_flags criticité haute
  critical_flags_overview   : dict[str, int]       // ex: {"PRICE_AMBIGUOUS": 2, ...}
  human_review_required_count : int

  // --- COMPTAGES OVERRIDE (préparatoires) ---
  count_rows_with_override  : int                  // 0 en P3.4
  override_summary_by_reason : dict[str, int] | {} // vide en P3.4

  // --- CRITÈRES ESSENTIELS (gates) ---
  essential_criteria_total  : int
  essential_criteria_passed : int
  essential_criteria_failed : int
  essential_criteria_pending : int

  // --- INTERDITS (principe directeur §P6) ---
  // PAS de champ `recommended_winner`
  // PAS de champ `average_total_score`
  // PAS de champ `suggested_rank_order`
}
```

### P4.3 — Justification de chaque champ par le critère dur

Critère : *le consommateur aval en a-t-il besoin pour comprendre la ligne sans mentir ?*


| Champ                                                        | Justification                                                              | IN / OUT                     |
| ------------------------------------------------------------ | -------------------------------------------------------------------------- | ---------------------------- |
| `bundle_id`                                                  | traçabilité bijective avec `criterion_assessments` et `SupplierEvaluation` | **IN**                       |
| `supplier_name`                                              | identification humaine, lecture comité                                     | **IN**                       |
| `pipeline_run_id`                                            | traçabilité run, préparation P3.4B recompute                               | **IN**                       |
| `matrix_revision_id`                                         | préparation P3.4B matrix_revisions (Section 4 archi)                       | **IN**                       |
| `eligibility_status` + `REGULARIZATION_PENDING`              | couvre P3.1B + préparation P3.4C                                           | **IN**                       |
| `*_score_system` × 4                                         | reflet exact de `FamilyScore` + `SupplierEvaluation` P3.2                  | **IN**                       |
| `*_score_override` × 4                                       | contrat futur-compatible, NULL en P3.4 (Q3 validée)                        | **IN contrat, OUT activité** |
| `*_score_effective` × 4                                      | vue publiée, = system en P3.4 (Q3 + G1 gravés)                             | **IN**                       |
| `total_comparability_status`                                 | évite mensonge M2, cohérence cohorte                                       | **IN**                       |
| `technical_threshold_mode`                                   | modélisé ; défaut transitoire MANDATORY (rectification CTO 2026-04-19)     | **IN**                       |
| `technical_threshold_value`                                  | transparence comité                                                        | **IN**                       |
| `technical_qualified`                                        | miroir `FamilyScore.qualified` P3.2                                        | **IN**                       |
| `rank` + `rank_status`                                       | règle explicite §P5, évite M6                                              | **IN**                       |
| `exclusion_reason_codes`                                     | source-tagged, évite M10                                                   | **IN**                       |
| `warning_flags`                                              | agrégation append-only des flags amont, évite M5                           | **IN**                       |
| `human_review_required`                                      | OR logique, propagation fidèle P3.3                                        | **IN**                       |
| `has_any_override` + `override_summary` + `last_override_at` | contrat P3.4B (Q3)                                                         | **IN contrat**               |
| `regularization_summary` + `has_regularization_history`      | contrat P3.4C                                                              | **IN contrat**               |
| `evidence_refs`                                              | auditabilité                                                               | **IN**                       |


---

## BLOC P5 — POLITIQUE DE RANG

### P5.1 — Règles opposables (alignées Context Anchor + arbitrages CTO)


| #   | Cas d'entrée                                                                                    | `rank`                    | `rank_status`                                                                    | Commentaire                                                       |
| --- | ----------------------------------------------------------------------------------------------- | ------------------------- | -------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| R1  | `eligibility_status = INELIGIBLE`                                                               | NULL                      | `EXCLUDED`                                                                       | P3.1B éligibilité — pas de scoring                                |
| R2  | `eligibility_status = PENDING`                                                                  | NULL                      | `PENDING`                                                                        | P3.1B en attente                                                  |
| R3  | `eligibility_status = REGULARIZATION_PENDING`                                                   | NULL                      | `PENDING`                                                                        | P3.4C préparé, traité comme PENDING                               |
| R4  | Éligible, `technical_threshold_mode = MANDATORY`, `technical_qualified = False`                 | NULL                      | `EXCLUDED`                                                                       | Convention P3.2 §6.4 stricte                                      |
| R5  | Éligible, `technical_threshold_mode = INFORMATIVE`, `technical_qualified = False`               | dépend de R6–R9           | dépend                                                                           | Le vendor participe au rang si les autres scores sont calculables |
| R6  | Éligible, tous scores système calculés (pas de NULL dans `*_score_system`)                      | rang entier ≥ 1           | `RANKED`                                                                         | Cas normal                                                        |
| R7  | Éligible, `commercial_score_system = NULL` pour cause `PriceAmbiguousError` non-résolue         | NULL                      | `NOT_COMPARABLE`                                                                 | Le vendor est non-comparable                                      |
| R8  | Éligible, `sustainability_score_system = NULL` mais commercial et technique calculés            | NULL                      | `INCOMPLETE`                                                                     | Distinction claire vs `NOT_COMPARABLE` (M4)                       |
| R9  | Cohorte asymétrique : au moins un vendor qualifié a `commercial_score_system = NULL` non-résolu | **tous** les rangs = NULL | **tous** `rank_status = NOT_COMPARABLE` avec flag `COHORT_ASYMMETRIC_COMMERCIAL` | Décision bloquante tranchée : pas de classement partiel mensonger |


### P5.2 — Justification R9

Cas : cohorte de 5 vendors, 4 avec commercial calculé, 1 avec `PriceAmbiguousError` non résolue.

**Option rejetée** : classer les 4 qui sont calculables, laisser le 5e en `NOT_COMPARABLE`.  
**Raison du rejet** : le comité lirait "1er, 2e, 3e, 4e" et penserait qu'il y a un gagnant, alors qu'une offre potentiellement meilleure est juste en attente de qualification. Mensonge M6.

**Option retenue** : toute la cohorte passe en `NOT_COMPARABLE` avec flag `COHORT_ASYMMETRIC_COMMERCIAL`. Le comité doit d'abord résoudre l'ambiguïté (via régularisation ou override) avant qu'un rang soit calculable.

**Exception** : si le vendor non-comparable est lui-même en `eligibility_status = INELIGIBLE` (règle R1), il est retiré de la cohorte "vendors potentiellement classables" **avant** le calcul. La cohorte restante est alors symétrique. Ce n'est pas une asymétrie.

### P5.3 — Algorithme de calcul de rang (spec, non-code)

```
ENTRÉE : liste de MatrixRow avec *_score_system calculés
SORTIE : même liste avec rank et rank_status peuplés

1. Partitionnement :
   - RANKABLE = rows où eligibility_status = ELIGIBLE ET (en mode MANDATORY) technical_qualified = True
   - EXCLUDED = rows où eligibility_status = INELIGIBLE
   - PENDING_SET = rows où eligibility_status ∈ {PENDING, REGULARIZATION_PENDING}

2. Détection asymétrie commerciale dans RANKABLE :
   - a_commercial_null = ∃ row ∈ RANKABLE : row.commercial_score_system = NULL
   
3. Détection incomplétude :
   - a_sustainability_null = ∃ row ∈ RANKABLE : row.sustainability_score_system = NULL

4. Assignation :
   - Si a_commercial_null : 
       ∀ row ∈ RANKABLE → rank = NULL, rank_status = NOT_COMPARABLE
       warning_flag ajouté : "COHORT_ASYMMETRIC_COMMERCIAL"
   - Sinon si a_sustainability_null pour certains rows :
       rows avec tous scores → RANKED
       rows avec sustainability NULL → rank = NULL, rank_status = INCOMPLETE
       (cohorte classable : les RANKED sont classés entre eux, les INCOMPLETE en dehors)
       warning_flag ajouté : "COHORT_PARTIAL_SUSTAINABILITY"
   - Sinon :
       rows RANKABLE triés par total_score_system DESC
       rank = 1, 2, 3, ... attribués
       rank_status = RANKED pour tous

5. Pour EXCLUDED et PENDING_SET :
   - rank = NULL
   - rank_status selon R1–R3
```

### P5.4 — Convention de recompute (préparation P3.4B)

Quand un override sera saisi (P3.4B), le recompute suivra :

1. `effective_score` recalculé pour la cellule concernée (override ?? system)
2. `FamilyScore.family_score` recalculé pour la famille affectée (sur effective)
3. `total_score_effective` recalculé pour le vendor
4. `rank` recalculé pour **toute la cohorte** (le rang est relatif)
5. `matrix_revision_id` incrémenté, snapshot enregistré

**Le `*_score_system` n'est JAMAIS recalculé** — il est immuable (G1 gravé).

---

## BLOC P6 — POLITIQUE DE SUMMARY

### P6.1 — Ce que le summary AFFICHE


| Catégorie                | Champ / Information                                                                                          | Justification               |
| ------------------------ | ------------------------------------------------------------------------------------------------------------ | --------------------------- |
| Comptages éligibilité    | `count_eligible`, `count_ineligible`, `count_pending`, `count_regularization_pending`                        | État objectif de la cohorte |
| Comptages comparabilité  | `count_comparable`, `count_non_comparable`, `count_incomplete`                                               | Distinction explicite M4    |
| Comptages rang           | `count_ranked`, `count_excluded`, `count_pending_rank`, `count_not_comparable_rank`, `count_incomplete_rank` | Granularité fidèle          |
| Statut cohorte           | `cohort_comparability_status` (`FULLY_COMPARABLE` / `PARTIALLY_COMPARABLE` / `NOT_COMPARABLE`)               | Vue synthétique honnête     |
| Flags critiques          | `critical_flags_overview: dict[str, int]`                                                                    | Visibilité anomalies        |
| Revue humaine            | `human_review_required_count`                                                                                | Priorisation comité         |
| Critères essentiels      | `essential_criteria_total / passed / failed / pending`                                                       | État des gates              |
| Traces                   | `pipeline_run_id`, `matrix_revision_id`, `computed_at`                                                       | Auditabilité                |
| Overrides (préparatoire) | `count_rows_with_override`, `override_summary_by_reason`                                                     | 0 / vide en P3.4            |


### P6.2 — Ce que le summary N'AFFICHE PAS


| Interdit                                        | Raison                                                               |
| ----------------------------------------------- | -------------------------------------------------------------------- |
| `recommended_winner`                            | Jamais. Le pipeline est témoin, pas juge (Section 1 archi).          |
| `suggested_rank_order`                          | Pas de suggestion implicite au comité.                               |
| `average_total_score`                           | Moyenne sur cohorte partiellement comparable = mensonge statistique. |
| Prédiction, jugement, pondération non-canonique | Hors mandat P3.4 (Article 2 doctrine).                               |
| Conversion `NULL` → `0` dans les agrégats       | Invariant I3.                                                        |
| Classement partiel tronqué sans le signaler     | Invariant I1, M2.                                                    |


### P6.3 — Principe directeur

> **Le summary est un compte-rendu, pas un conseil. Il décrit l'état, il ne suggère rien.**

### P6.4 — Règle de calcul `cohort_comparability_status`

```
SI count_comparable = total_bundles_rankable ET count_non_comparable = 0 ET count_incomplete = 0 
    → FULLY_COMPARABLE
SINON SI count_comparable ≥ 1 ET (count_non_comparable > 0 OU count_incomplete > 0)
    → PARTIALLY_COMPARABLE
SINON SI count_comparable = 0 ET count_non_comparable ≥ 1
    → NOT_COMPARABLE
SINON (dégénéré, tous PENDING/EXCLUDED) 
    → NOT_COMPARABLE avec flag "NO_COMPARABLE_CANDIDATE"
```

---

## BLOC P6 BIS — EXPLICABILITÉ

### P6bis.1 — Objectif

Chaque `MatrixRow` doit permettre à un reviewer de comprendre **pourquoi** elle a le statut qu'elle a, sans relire le code.

### P6bis.2 — Structure d'explicabilité minimale

Chaque `MatrixRow` porte, en plus des champs déjà listés :

```
explainability: {
  status_chain: list[str]          // ordre de détermination : 
                                   // ["eligibility.P3.1B", "technical.P3.2", 
                                   //  "commercial.P3.3", "sustainability.P3.2", 
                                   //  "rank.P3.4"]
  primary_status_source: str       // la source dominante ayant produit 
                                   // l'état actuel (ex: "P3.1B:INELIGIBLE")
  score_breakdown: dict            // {technical: {...}, commercial: {...}, ...}
                                   // copie légère des SubCriterionScore agrégés
  exclusion_path: list[str] | NULL // si exclu : enchainement des raisons, 
                                   // de la plus décisive à la plus contextuelle
}
```

### P6bis.3 — Règle d'explicabilité

Toute ligne exclue ou non-classable doit pouvoir répondre à :

- *pourquoi n'est-elle pas classée ?* → via `exclusion_path`
- *quelle source a produit ce verdict ?* → via `primary_status_source`
- *quels scores ont été calculés ?* → via `score_breakdown`

Sans cela, le comité ne peut pas arbitrer en connaissance de cause (et P3.4B / P4 n'ont pas matière à travailler).

### P6bis.4 — Pas de narration libre

`explainability` est une **structure déterministe**, pas un texte généré par LLM. Le texte libre viendra avec le Committee Review Agent (P4), et restera grounded sur cette structure.

---

## BLOC P6 TER — POLITIQUE DE REVUE COMITÉ / CORRECTIONS (exigé CTO)

### P6ter.1 — Éléments futurs-overridables


| Champ `MatrixRow`                              | Overridable ?        | Par quelle couche        | Taxonomie `correction_nature` applicable                                              |
| ---------------------------------------------- | -------------------- | ------------------------ | ------------------------------------------------------------------------------------- |
| `technical_score_system`                       | NON, jamais          | —                        | —                                                                                     |
| `commercial_score_system`                      | NON, jamais          | —                        | —                                                                                     |
| `sustainability_score_system`                  | NON, jamais          | —                        | —                                                                                     |
| `total_score_system`                           | NON, dérivé immuable | —                        | —                                                                                     |
| `technical_score_override`                     | OUI                  | P3.4B                    | `SCORING_OVERRIDE`, `EVIDENCE_MISINTERPRETED`, `READING_ERROR`                        |
| `commercial_score_override`                    | OUI                  | P3.4B                    | `SCORING_OVERRIDE`, `LATE_DOCUMENT_ACCEPTED`                                          |
| `sustainability_score_override`                | OUI                  | P3.4B                    | `SCORING_OVERRIDE`, `EVIDENCE_MISINTERPRETED`                                         |
| `eligibility_status`                           | INDIRECTEMENT        | P3.4C via régularisation | `REGULARIZATION_ACCEPTED`, `REGULARIZATION_REJECTED`, `PROCEDURAL_EXCEPTION_APPROVED` |
| `rank`, `rank_status`, `total_score_effective` | NON directement (G1) | —                        | Recalculés par Recompute Engine                                                       |
| `exclusion_reason_codes`                       | INDIRECTEMENT        | P3.4B                    | Ajouté par override, pas édité                                                        |
| `warning_flags`                                | INDIRECTEMENT        | P3.4B / P3.4C            | Enrichi, pas effacé                                                                   |
| `human_review_required`                        | INDIRECTEMENT        | P3.4B                    | Transition false ↔ true via override motivé                                           |
| `evidence_refs`                                | AJOUT uniquement     | P3.4B                    | Preuves additionnelles attachables à l'override                                       |


### P6ter.2 — Cohabitation `system` / `override` / `effective`

**Règle invariante (G1 gravé)** :

> `***_score_effective` n'est JAMAIS éditable directement par un humain. C'est une vue dérivée calculée par le Recompute Engine à partir de `*_score_system` (immuable) et de `*_score_override` (saisi motivé en P3.4B).**

Pseudo-code de résolution (exécuté par le Recompute Engine P3.4B, pas par P3.4) :

```
effective = override if (override is not NULL and override_is_active) else system
```

En P3.4 :

- `*_score_override = NULL` par construction
- donc `*_score_effective = *_score_system` par construction
- `has_any_override = False` par construction
- `override_summary = []` par construction

### P6ter.3 — Champs prévus dès P3.4 (contrat préparatoire Q3 validé)

Déjà intégrés au contrat `MatrixRow` §P4.1 :

- `technical_score_override`, `commercial_score_override`, `sustainability_score_override`, `total_score_override`
- `technical_score_effective`, `commercial_score_effective`, `sustainability_score_effective`, `total_score_effective`
- `has_any_override`, `override_summary`, `last_override_at`
- `regularization_summary`, `has_regularization_history`

### P6ter.4 — Taxonomie `correction_nature` obligatoire (G2 gravé)

Toute correction future (P3.4B ou P3.4C) devra déclarer sa nature dans l'un des codes suivants :


| Code                            | Définition                                            | Couche        |
| ------------------------------- | ----------------------------------------------------- | ------------- |
| `READING_ERROR`                 | le pipeline a mal lu un document                      | P3.4B         |
| `EVIDENCE_MISINTERPRETED`       | la pièce a été comprise mais mal notée                | P3.4B         |
| `LATE_DOCUMENT_ACCEPTED`        | un document tardif a été accepté par le comité        | P3.4B + P3.4C |
| `REGULARIZATION_ACCEPTED`       | un document régularisé a été accepté                  | P3.4C         |
| `REGULARIZATION_REJECTED`       | une régularisation a été refusée                      | P3.4C         |
| `SCORING_OVERRIDE`              | désaccord du comité sur une note, sans erreur lecture | P3.4B         |
| `PROCEDURAL_EXCEPTION_APPROVED` | dérogation procédurale validée                        | P3.4B / P5    |


**Aucun override sans `correction_nature` valide.** Règle opposable dès P3.4B.

### P6ter.5 — Ce qui relève de P3.4B (non-implémenté en P3.4)

- saisie d'override (API + UI)
- Recompute Engine
- tables `assessment_overrides`, `matrix_revisions`, `committee_override_log`
- transitions d'état override (ACTIVE / SUPERSEDED / CANCELLED)
- logs append-only

### P6ter.6 — Ce qui relève de P3.4C (non-implémenté en P3.4)

- table `regularization_requests`
- re-ingestion de documents tardifs
- re-run partiel du pipeline sur bundle affecté
- chaîne `supersedes` / `superseded_by` sur `criterion_assessments`
- workflow demande → dépôt → re-run → nouvel assessment

### P6ter.7 — Ce qui relève de P4 (non-implémenté, non ouvert)

- Committee Review Agent
- observations chat contextuelles
- propositions d'actions structurées
- mode "propose but never dispose"

### P6ter.8 — Résumé P6ter

P3.4 ne fait **rien** d'actif sur le comité. Mais P3.4 **prépare** opposablement tout :

- contrat de champs (Q3)
- invariants d'immutabilité (G1)
- taxonomie de corrections (G2)
- structures d'explicabilité (P6bis)
- cascade de phases (P3.4B → P3.4C → P4)

---

## BLOC P7 — POINT D'INSERTION EXACT

### P7.1 — Décision

**P3.4 s'insère après** `populate_assessments_from_m14(strict_matrix_participants=True, strict_uuid=True)` (`pipeline_v5_service.py` **L1453–L1457** sur HEAD `417f1149`), **dans un nouveau service dédié** `matrix_builder_service.py`, appelé par `run_pipeline_v5` après la persistance des assessments et le succès du bridge.

### P7.2 — Entrées

- lecture depuis DB : `criterion_assessments` (vérité de matrice, Context Anchor §3)
- lecture depuis DB : `process_workspaces` (pour `technical_qualification_threshold` et `technical_threshold_mode` lorsque disponible)
- lecture depuis DB : `dao_criteria` (pour famille, pondération, mode)
- lecture en mémoire : `SupplierEvaluation[]` du run en cours (pour `elimination_reason` et flags riches)
- lecture en mémoire : `GateOutput` du run en cours (pour cohorte éligibilité)

**Principe** : `criterion_assessments` est la source de vérité persistée. Les objets mémoire fournissent les flags riches non persistés.

### P7.3 — Sorties

- `list[MatrixRow]` construite et validée par invariants
- `MatrixSummary` construit par agrégation sur la liste

### P7.4 — Persistance P3.4

**Décision** : P3.4 **calcule à la demande** (pas de persistance en table dédiée).

Justification par le critère dur :

- le consommateur aval (UI, PV, exports) a-t-il besoin de persistance pour fonctionner ? **NON**, la reconstruction est déterministe depuis `criterion_assessments`.
- avantage non-persistance : une seule source de vérité, pas de désynchro possible
- avantage non-persistance : idempotence gratuite
- inconvénient : recalcul à chaque demande (acceptable sur pilote, à optimiser post-P3.4 si besoin prouvé)

**Exception** : si P3.4B introduit `matrix_revisions` (snapshots), alors `MatrixRow[]` est persisté comme snapshot JSON dans cette table. C'est **P3.4B**, pas P3.4.

### P7.5 — Ce que P3.4 NE touche PAS

- `pipeline_v5_service.py` hors ajout minimal : champs `PipelineV5Result` + appel au nouveau service
- `m14_engine.py` — intact
- `m14_bridge.py` — intact
- `eligibility_gate` — intact
- `commercial_normalizer` P3.3 — intact
- `dao_criteria` schéma — intact (P3.2 terminé)

**Aucune migration Alembic en P3.4.** Les tables futures (`assessment_overrides`, `matrix_revisions`, `regularization_requests`) sont P3.4B et P3.4C.

### P7.6 — Point d'insertion exact (pseudo-diff, pour spec)

```python
# pipeline_v5_service.py — run_pipeline_v5 (après succès bridge)

  populate_assessments_from_m14(workspace_id, strict_matrix_participants=True, strict_uuid=True)
  # ↑ existant, intact — L1453–L1457 sur HEAD 417f1149

+ # P3.4 — MatrixRow + Summary (après ce bloc try/except bridge, avant out.completed)
+ matrix_rows = build_matrix_rows(
+     workspace_id=workspace_id,
+     pipeline_run_id=run_id,
+     supplier_evaluations=report.offer_evaluations,
+     gate_output=gate_out,
+ )
+ matrix_summary = build_matrix_summary(matrix_rows, workspace_id=workspace_id)
+ out.matrix_rows = matrix_rows
+ out.matrix_summary = matrix_summary
```

**Extension `PipelineV5Result`** (L212–L241, `extra="forbid"`) : ajouter explicitement `matrix_rows` et `matrix_summary` **avant** toute implémentation du builder — voir §E0.2.

**Minimal. Non-intrusif. Idempotent.**

---

## BLOC P8 — VERDICT

### P8.1 — État de chaque bloc


| Bloc                                       | Statut                           | Commentaire    |
| ------------------------------------------ | -------------------------------- | -------------- |
| P1 — Point d'entrée actuel                 | **CONFIRMÉ** sur HEAD `417f1149` | grep + lecture |
| P2 — États métier disponibles              | **INTÉGRAL**                     | §BLOC P2       |
| P3 — Mensonges potentiels                  | **INTÉGRAL**                     | §BLOC P3       |
| P4 — Contrat `MatrixRow` + `MatrixSummary` | **INTÉGRAL**                     | §BLOC P4       |
| P5 — Politique de rang                     | **INTÉGRAL**                     | §BLOC P5       |
| P6 — Politique de summary                  | **INTÉGRAL**                     | §BLOC P6       |
| P6bis — Explicabilité                      | **INTÉGRAL**                     | §BLOC P6 BIS   |
| P6ter — Revue comité / corrections         | **INTÉGRAL**                     | §BLOC P6 TER   |
| P7 — Point d'insertion                     | **INTÉGRAL**                     | §BLOC P7       |


### P8.2 — Verdict

`**READY TO OPEN`** — sous conditions :

1. Séquence git exécutée (§Rapport d'exécution matériel).
2. Single-head Alembic.
3. Fichiers suivis propres ; `??` gérés par règle §Réserve #1.
4. P1 confirmé sur HEAD.
5. **Réserves CTO Senior #1–#5** actées en Étape 0 avant code métier (investigation / doc — E0.1 **clos** avec cette révision).
6. Validation CTO principal (gouvernance) — **Q-clôture** du message revue 2026-04-19.

### P8.3 — Blocage exact éventuel

**Aucun blocage logique.** Dépendances : validation humaine ; arbitrage séparé défaut final `technical_threshold_mode` (hors renversement implicite — §Rectification Q1).

---

## Rapport de clôture de tour (format imposé)


| #   | Item                                                  | Statut                                                                   |
| --- | ----------------------------------------------------- | ------------------------------------------------------------------------ |
| 1   | Branche créée : `feat/p3-4-matrixrow-builder-summary` | **Exécutée** (`417f1149`)                                                |
| 2   | Point d'entrée matrice identifié                      | **Confirmé** fichier:ligne                                               |
| 3   | Contrat `MatrixRow` esquissé                          | **Intégral** §P4                                                         |
| 4   | Verdict preflight                                     | `**READY TO OPEN`** avec réserves acternables + validation CTO principal |
| 5   | Blocage exact éventuel                                | **Aucun blocage logique**                                                |
| 6   | Fichier preflight autonome (P2–P7)                    | **OUI** (révision 2026-04-19)                                            |


---

## Réponses indicatives aux Q-clôture (CTO principal)

*Ces lignes sont des **propositions d’alignement** pour le décideur humain ; elles ne substituent pas une validation écrite CTO principal.*


| Question                                    | Proposition                                                                                         |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Q-clôture 1 — Étape 0 bloquante ?           | **OUI** — investigation + doc (E0.1–E0.5) avant premier commit de types/builder                     |
| Q-clôture 2 — Défaut `MANDATORY` + flag ?   | **OUI** — aligné rectification §Rectification Q1                                                    |
| Q-clôture 3 — Plan E0→E5 ?                  | **OUI** — ordre cohérent (contrat → builder → intégration → validation → PR)                        |
| Q-clôture 4 — Fichier autonome ?            | **OUI** — satisfait par cette révision                                                              |
| Q-clôture 5 — Revue intermédiaire post-E0 ? | **Au choix CTO principal** ; matériellement, E0 peut se clore par commit doc seul puis revue légère |


