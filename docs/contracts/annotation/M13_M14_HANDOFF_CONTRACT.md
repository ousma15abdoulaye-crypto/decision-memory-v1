# M13 → M14 Handoff Contract

**Version :** 1.0.0  
**Date :** 2026-04-02  
**Émis par :** M13 — Regulatory Profile Engine (Pass 2A)  
**Consommé par :** M14 — Evaluation Pipeline (plan)  
**Autorité :** ADR-M13-001 — CONTEXT_ANCHOR.md

---

## Principe

M13 **prépare** ; M14 **exécute** l’évaluation comparative des offres et les scores.

- **RH1 — `ComplianceChecklist`** : liste de contrôles exécutables par M14 (par offre ou dossier).
- **RH2 — `EvaluationBlueprint`** : **cadrage uniquement** (méthode, pondérations de principe, OCDS, règles de validité documentaire). M14 **doit** relire `procedure_requirements` dans le rapport M13 pour tout détail opérationnel (grilles, montants, compositions de commissions).

Violation du principe (STOP S18) : traiter RH2 comme spécification d’exécution autonome sans relire les exigences procédurales complètes.

---

## Payload RH1

**Modèle :** `ComplianceChecklist` — [`src/procurement/compliance_models_m13.py`](../../../src/procurement/compliance_models_m13.py)

| Champ | Usage M14 |
|-------|-----------|
| `per_offer_checks` | À rejouer pour chaque offre candidate |
| `case_level_checks` | Une fois par dossier |
| `expiry_checks` / règles liées | Si date document absente → statut **INDETERMINATE**, pas FAILED (instruction métier) |

---

## Payload RH2

**Modèle :** `EvaluationBlueprint` — même module.

| Champ | Usage M14 |
|-------|-----------|
| `evaluation_method` | Orientation méthode (ex. `lowest_price`, `mieux_disant`) |
| `procedure_requirements_ref` | Référence logique vers le snapshot persisté (case + version) |
| `m14_instruction` | Rappel : cadrage seul |
| `document_validity_rules` | Entrées pour contrôles de validité temporelle |

---

## Invariants

- Aucun score d’offre, aucun classement, aucun verdict de attribution dans les sorties M13.
- Les 9 principes sont présents dans `principles_compliance_map` (validation stricte côté moteur).

---

## Dépendances modules

- [`compliance_models_m13.py`](../../../src/procurement/compliance_models_m13.py)
- [`m13_engine.py`](../../../src/procurement/m13_engine.py) (orchestration pure)
