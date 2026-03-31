# M12 → M13 Handoff Contract

**Version:** 1.0.0
**Emis par:** M12 Pass 1C (conformity + handoffs)
**Consomme par:** M13 — Regulatory Compliance Engine (PLAN — non implémenté)
**Autorite:** Plan Directeur DMS V4.1 — CONTEXT_ANCHOR.md

---

## Principe

M12 PRÉPARE. M13 APPLIQUE.

M12 détecte les signaux réglementaires présents dans le document (framework, clauses, seuils) et les emballe dans `RegulatoryProfileSkeleton`. M13 reçoit ce squelette et applique les règles de conformité complètes (SCI §5.2, DGMP, seuils procédure). M12 n'évalue jamais la conformité réglementaire : il signale, il ne juge pas.

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
| `dgmp_threshold_tier_detected` | str \| None | Palier seuil DGMP détecté | regex (non implémenté M12 — None) |
| `other_framework_signals` | dict[str, list[str]] | Autres frameworks détectés | vide en V6 |
| `m13_todo` | str | "Apply full regulatory profile based on these signals" | constante |

### Condition de production

H1 est produit **uniquement** si `document_kind in SOURCE_RULES_KINDS` (DAO, RFQ, TDR, cahier des charges). Pour les offres et documents administratifs, `regulatory_profile_skeleton = None`.

---

## Ce que M13 doit faire avec H1

1. **Vérifier la cohérence framework** : si `framework_detected=SCI` et `sci_conditions_referenced=False` → non-conformité signalable
2. **Appliquer les seuils procédure SCI §4.2** : croiser `framework_detected` + `dgmp_procedure_type_detected` avec les seuils du Plan Directeur V4.1 (100$, 1k$, 10k$, 100k$)
3. **Checker les critères éliminatoires SCI §5.2** : NIF, RCCM, conditions SCI, sanctions, RIB — croisement avec `eligibility_gates_extracted` de Pass 1C
4. **Valider la pondération durabilité** : SCI impose ≥ 10% — croiser `sci_sustainability_pct_detected` avec `scoring_structure_extracted`
5. **Produire un `RegulatoryComplianceReport`** (M13 output — non spécifié ici)

---

## Invariants de passage

- `framework_confidence < 0.60` → M13 doit marquer le rapport `review_required`
- `framework_detected = UNKNOWN` → M13 ne peut pas appliquer les règles SCI/DGMP — `not_assessable`
- H1 `None` sur un document `source_rules` → anomalie pipeline — M13 signale `pipeline_error`

---

## Ce que M13 N'EST PAS autorisé à faire

- Modifier les données M12 (append-only, RÈGLE-05)
- Supposer un framework non détecté par M12
- Créer des entrées `annotated_validated` (RÈGLE-25 — travail humain uniquement)

---

## Dépendances

- `src/procurement/procedure_models.py` : `RegulatoryProfileSkeleton`, `M12Handoffs`
- `src/procurement/handoff_builder.py` : `build_handoffs()`, `_build_h1_regulatory()`
- `src/annotation/passes/pass_1c_conformity_and_handoffs.py` : producteur
- `docs/freeze/DMS_V4.1.0_FREEZE.md` : seuils SCI §4.2 et §5.2 (autorité)

---

## Milestone

M13 : PLAN — implémentation après M12 DoD validé (RÈGLE-01).
