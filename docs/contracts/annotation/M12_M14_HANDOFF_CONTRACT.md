# M12 → M14 Handoff Contract

**Version:** 1.1.0
**Emis par:** M12 Pass 1C (conformity + handoffs)
**Consomme par:** M14 — Evaluation Engine V1 (implémenté — ADR-M14-001, `m14_engine.py`)
**Autorite:** Plan Directeur DMS V4.1 — CONTEXT_ANCHOR.md

---

## Principe

M12 STRUCTURE. M14 ÉVALUE.

M12 produit deux squelettes d'évaluation : H2 (`AtomicCapabilitySkeleton`) qui définit ce qu'une offre doit contenir pour être recevable, et H3 (`MarketContextSignal`) qui fournit le contexte marché pour le scoring prix. M14 reçoit ces squelettes et exécute l'évaluation comparative des offres. M12 ne score jamais : il prépare le terrain.

---

## Payload de sortie M12 — H2

**Modèle Pydantic :** `AtomicCapabilitySkeleton` (`src/procurement/procedure_models.py`)
**Champ dans `M12Handoffs` :** `atomic_capability_skeleton`
**Produit par :** `src/procurement/handoff_builder.py` → `_build_h2_capability()`
**Accessible via :** `Pass1COutput.output_data["m12_handoffs"]["atomic_capability_skeleton"]`

### Champs H2

| Champ | Type | Description | Source M12 |
|-------|------|-------------|------------|
| `procurement_family` | `ProcurementFamily` | GOODS / SERVICES / CONSULTANCY / WORKS | Pass 1A L2 |
| `procurement_family_sub` | `ProcurementFamilySub` | Sous-famille détaillée | Pass 1A L2 |
| `active_capability_sections` | list[str] | Sections attendues dans l'offre (ex. `methodology`, `delivery_schedule`) | logique famille |
| `inactive_capability_sections` | list[str] | Sections non pertinentes pour cette famille | logique famille |
| `eligibility_checklist` | list[EligibilityGateExtracted] | Gates éliminatoires extraites du document source | Pass 1C |
| `scoring_structure` | `ScoringStructureDetected` \| None | Critères de notation et pondérations extraits | Pass 1C |
| `m14_todo` | str | "Evaluate each offer against this skeleton" | constante |

### Sections actives par famille

| Famille | Sections actives |
|---------|-----------------|
| `CONSULTANCY` | methodology, team_composition, qa_plan, workplan, experience_references |
| `GOODS` | delivery_schedule, experience_references, financial_capacity |
| `WORKS` | methodology, equipment_list, workplan, experience_references, financial_capacity |
| `SERVICES` | methodology, experience_references, financial_capacity |
| Autre/UNKNOWN | Toutes les sections |

### Condition de production

H2 est produit **uniquement** si `document_kind in SOURCE_RULES_KINDS`. Pour les offres soumises, H2 = None (l'offre est évaluée **contre** le squelette, elle ne le produit pas).

---

## Payload de sortie M12 — H3

**Modèle Pydantic :** `MarketContextSignal` (`src/procurement/procedure_models.py`)
**Champ dans `M12Handoffs` :** `market_context_signal`
**Produit par :** `src/procurement/handoff_builder.py` → `_build_h3_market()`
**Accessible via :** `Pass1COutput.output_data["m12_handoffs"]["market_context_signal"]`

### Champs H3

| Champ | Type | Description | Source M12 |
|-------|------|-------------|------------|
| `prices_detected` | bool | Des prix ont été trouvés dans le document | regex |
| `currency_detected` | str \| None | Devise (FCFA, XOF, USD, EUR) | regex |
| `price_basis_detected` | `"HT"` \| `"TTC"` \| None | Base prix hors/toutes taxes | regex |
| `material_price_index_applicable` | bool | Matériaux à index mercuriale détectés | regex |
| `material_categories_detected` | list[str] | Catégories matériaux (ciment, fer, etc.) | regex |
| `zone_for_price_reference` | list[str] | Zones géographiques pour référence prix | regex |
| `mercuriale_link_hint` | str \| None | Lien potentiel vers mercuriale Couche B | None en V6 |
| `market_survey_linked` | bool | Survey marché lié détecté | False en V6 |
| `market_survey_document_id` | str \| None | ID du document survey lié | None en V6 |

### Condition de production

H3 est produit pour **tous les types** de documents. Il est **supprimé** (= None) si `prices_detected=False` ET `material_categories_detected=[]` ET `zone_for_price_reference=[]`. H3 non-None signifie qu'il y a un contexte marché exploitable.

---

## Ce que M14 doit faire avec H2 + H3

### Avec H2

1. **Vérifier la complétude de l'offre** : chaque section de `active_capability_sections` doit être présente dans l'offre technique (croisement avec Pass 1B de l'offre)
2. **Appliquer la checklist éliminatoire** : `eligibility_checklist` — tout gate `is_eliminatory=True` non fourni = rejet immédiat
3. **Calculer le score technique** : utiliser `scoring_structure.criteria` avec leurs `weight_percent` pour noter chaque offre
4. **Vérifier la cohérence pondération** : `scoring_structure.ponderation_coherence` doit être `OK` — sinon signaler `review_required`

### Avec H3

1. **Identifier la devise de référence** : `currency_detected` — alerter si offre en devise différente
2. **Appliquer l'index mercuriale** : si `material_price_index_applicable=True` → croiser `material_categories_detected` avec Couche B mercuriale pour détecter les prix anormaux
3. **Calibrer le scoring prix par zone** : `zone_for_price_reference` → coûts logistiques différents par zone Mali

---

## Invariants de passage

- `scoring_structure = None` sur un document `source_rules` → M14 ne peut pas calculer de score pondéré → `evaluation_method = "lowest_price"` par défaut
- `ponderation_coherence != "OK"` → M14 flag `scoring_review_required` avant scoring
- H2 `None` sur une offre soumise = normal — M14 doit récupérer H2 du document `source_rules` associé via ProcessLinking
- H3 `None` = pas de contexte marché → M14 scoring prix sans référence mercuriale

---

## Lien ProcessLinking → évaluation comparative

M14 utilise `ProcessLinking` (Pass 1D) pour regrouper les offres d'un même dossier :

```
source_rules (DAO/RFQ) → H2 squelette
    ↓ via LinkedParentHint (RESPONDS_TO)
offer_technical  → évalué contre H2
offer_financial  → scoré via H3 + mercuriale
    ↓ agrégation
evaluation_report (M14 output)
```

Le `process_role` de chaque document (Pass 1D) détermine son rôle dans l'évaluation.

---

## Ce que M14 N'EST PAS autorisé à faire

- Produire `winner`, `rank`, `recommendation`, `best_offer` (RÈGLE-09 V4.1.0 — KILL LIST)
- Modifier les données M12 (append-only, RÈGLE-05)
- Décider seul — tout résultat M14 est soumis au comité humain (RÈGLE-ORG-04)

---

## Dépendances

- `src/procurement/procedure_models.py` : `AtomicCapabilitySkeleton`, `MarketContextSignal`, `M12Handoffs`, `ScoringStructureDetected`, `EligibilityGateExtracted`
- `src/procurement/handoff_builder.py` : `build_handoffs()`, `_build_h2_capability()`, `_build_h3_market()`
- `src/annotation/passes/pass_1c_conformity_and_handoffs.py` : producteur H2 + H3
- `src/annotation/passes/pass_1d_process_linking.py` : producteur liens offre↔DAO
- `docs/freeze/DMS_V4.1.0_FREEZE.md` : critères SCI §5.2, composition comité §5.4 (autorité)
- Couche B mercuriale (`mercurials`, `mercuriale_sources`) : référence prix

---

## Milestone

M14 : **DONE** — moteur + API `/api/m14/` + persistance (`evaluation_documents`, audit `059` — `score_history` / `elimination_log`). Réf. `docs/adr/ADR-M14-001_evaluation_engine.md`, `docs/adr/DMS-M14-ARCH-RECONCILIATION.md`.
