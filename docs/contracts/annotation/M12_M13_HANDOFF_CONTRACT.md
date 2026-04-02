# M12 → M13 Handoff Contract

**Version:** 1.1.0
**Emis par:** M12 Pass 1C (conformity + handoffs)
**Consomme par:** M13 — Regulatory Profile Engine (Pass 2A)
**Autorite:** Plan Directeur DMS V4.1 — CONTEXT_ANCHOR.md — ADR-M13-001

---

## Principe

M12 PRÉPARE. M13 APPLIQUE.

M12 détecte les signaux réglementaires présents dans le document (framework, clauses, seuils) et les emballe dans `RegulatoryProfileSkeleton`. M13 reçoit ce squelette et applique les règles complètes depuis **YAML** (seuils, procédures, documents requis, validité, principes). M12 n'évalue jamais la conformité réglementaire : il signale, il ne juge pas.

---

## Payload de sortie M12 — H1

**Modèle Pydantic :** `RegulatoryProfileSkeleton` (`src/procurement/procedure_models.py`)
**Champ dans `M12Handoffs` :** `regulatory_profile_skeleton`
**Produit par :** `src/procurement/handoff_builder.py` → `_build_h1_regulatory()`
**Accessible via :** `Pass1COutput.output_data["m12_handoffs"]["regulatory_profile_skeleton"]`

### Champs

| Champ | Type | Description | Source M12 |
|-------|------|-------------|------------|
| `framework_detected` | `ProcurementFramework` | SCI / DGMP / MIXED / UNKNOWN | Pass 1A L1 |
| `framework_confidence` | float [0.0, 1.0] | Confiance du framework détecté | Pass 1A |
| `sci_signals_detected` | list[str] | Signaux SCI présents (ex. `general_conditions_referenced`) | regex text |
| `sci_conditions_referenced` | bool | Conditions générales d'achat SCI mentionnées | regex |
| `sci_sustainability_pct_detected` | float \| None | Pourcentage durabilité détecté (ex. 10.0) | regex |
| `sci_iapg_referenced` | bool | Clause IAPG / intolerable acts présente | regex |
| `sci_sanctions_clause_present` | bool | Clause sanctions mentionnée | regex |
| `dgmp_signals_detected` | list[str] | Signaux DGMP présents (ex. `threshold_referenced`) | regex |
| `dgmp_procedure_type_detected` | str \| None | Type procédure DGMP (ex. `ouvert`, `restreint`) | regex |
| `dgmp_threshold_tier_detected` | str \| None | Palier seuil DGMP détecté | regex (peut être None) |
| `other_framework_signals` | dict[str, list[str]] | Autres frameworks détectés (MIXED) | extension |
| `m13_todo` | str | Message de délégation M13 | constante |

### Condition de production

H1 est produit **uniquement** si `document_kind in SOURCE_RULES_KINDS` (DAO, RFQ, TDR, cahier des charges). Pour les offres et documents administratifs, `regulatory_profile_skeleton = None`.

---

## Entrée agrégée M13 — `M12Output`

M13 consomme le **`M12Output` complet** (`src/procurement/procedure_models.py`) reconstruit après Pass 1A–1D :

- `procedure_recognition` (Pass 1A)
- `document_validity` (Pass 1B)
- `document_conformity_signal` (Pass 1C) — inclut `gates` et `eligibility_gates_extracted`
- `process_linking` (Pass 1D)
- `handoffs` (Pass 1C) — H1/H2/H3
- `m12_meta`

---

## Payload de sortie M13

### Rapport moteur V5 (canonique)

**Modèle :** `M13RegulatoryComplianceReport` — `src/procurement/compliance_models_m13.py`

Contient : régime résolu (R1), exigences procédurales (R2), gates assemblées (R3), dérogations (R4), `PrinciplesComplianceMap` (9 principes), `OCDSProcessCoverage`, `M13Meta`.

### Résumé legacy (compatibilité)

**Modèle :** `RegulatoryComplianceReport` — `src/procurement/compliance_models.py`

Résumé verdict + checks éliminatoires. Dérivé du rapport V5 via **`legacy_compliance_report_from_m13()`** (`compliance_models_m13.py`).

### Handoffs M14

- **RH1** : `ComplianceChecklist` — `compliance_models_m13.py`
- **RH2** : `EvaluationBlueprint` — cadrage uniquement ; voir [M13_M14_HANDOFF_CONTRACT.md](./M13_M14_HANDOFF_CONTRACT.md)

**Bundle :** `M13Output` (`report`, `compliance_checklist`, `evaluation_blueprint`).

---

## Ce que M13 doit faire avec H1

1. Résoudre le régime (framework M12 + YAML) sans redétecter le framework (M12 est source de vérité détection).
2. Instancier documents requis, délais, organes, garanties, seuils depuis YAML.
3. Réconcilier gates document (M12) et exigences réglementaires (4 phases dont validité).
4. Produire la carte des 9 principes et la couverture OCDS déclarative.
5. **Ne pas** scorer les offres ni produire de verdict d’attribution (M14).

---

## Invariants de passage

- `framework_confidence < 0.60` → `review_required` au niveau legacy et métadonnées M13.
- `framework_detected = UNKNOWN` → sortie dégradée + `not_assessable` / revue selon ADR-M13-001 (mapping confiance).
- H1 `None` sur un document `source_rules` attendu → anomalie pipeline.

---

## Ce que M13 N'EST PAS autorisé à faire

- Appeler un LLM (moteur 100 % déterministe).
- Modifier les données M12.
- Dupliquer `regulatory_index` comme source de seuils parallèle (consultation audit OK).

---

## Dépendances

- `src/procurement/procedure_models.py` : `M12Output`, `RegulatoryProfileSkeleton`
- `src/procurement/compliance_models.py` : `RegulatoryComplianceReport` (legacy)
- `src/procurement/compliance_models_m13.py` : modèles V5 + pont legacy
- `docs/adr/ADR-M13-001_regulatory_profile_engine.md`
- `docs/contracts/annotation/PASS_2A_REGULATORY_PROFILE_CONTRACT.md`

---

## Milestone

M13 : implémenté — Pass 2A sous feature flag `ANNOTATION_USE_PASS_2A`.
