# Pass 2A — Regulatory Profile (M13)

**Version :** 1.0.0  
**Date :** 2026-04-02  
**Référence :** ADR-M13-001, DMS-M13-V5-FREEZE

---

## Rôle

Pass **2A** exécute le **Regulatory Compliance Engine** (M13) : résolution de régime, instanciation des exigences, assemblage des gates (4 phases), dérogations, carte des 9 principes, couverture OCDS, handoffs **RH1** (ComplianceChecklist) et **RH2** (EvaluationBlueprint — cadrage uniquement).

---

## Préconditions

| Précondition | Vérification |
|--------------|--------------|
| Pass 1D terminé avec succès pour le document / run | État pipeline `pass_1d_done` (ou équivalent checkpoint) |
| `M12Output` reconstituable | Sorties `pass_1a` … `pass_1d` présentes dans le run |
| H1 présent si `source_rules` | `handoffs.regulatory_profile_skeleton` non null pour kinds source_rules |

Si H1 est absent alors que le document exige un profil réglementaire, Pass 2A est ignoré (`PassRunStatus.SKIPPED`) et aucun rapport M13 n’est produit.

---

## Entrées

- **`document_id`** : identifiant document courant.
- **`case_id`** : identifiant dossier (persistance RLS).
- **`m12_output`** : modèle [`M12Output`](../../../src/procurement/procedure_models.py) (JSON sérialisé acceptable).
- **`run_id`** : corrélation logs.

---

## Sorties

- **`AnnotationPassOutput`** conforme à [PASS_OUTPUT_STANDARD](./PASS_OUTPUT_STANDARD.md) avec `output_data` contenant au minimum :
  - `m13_output` : objet sérialisé [`M13Output`](../../../src/procurement/compliance_models_m13.py) (`report`, `compliance_checklist`, `evaluation_blueprint`)
  - `legacy_compliance_report` : [`RegulatoryComplianceReport`](../../../src/procurement/compliance_models.py) pour compatibilité M12→M13 historique

---

## Feature flag

- **`ANNOTATION_USE_PASS_2A`** : `0` (défaut) = Pass 2A non exécuté ; `1` = enchaînement après Pass 1D.

---

## Erreurs

- Échec YAML critique : sortie **dégradée** documentée dans `m13_meta.review_required` + raisons (pas d’exception non gérée vers l’orchestrateur).
- Données M12 corrompues : `PassRunStatus.FAILED` + code erreur dans `errors`.
