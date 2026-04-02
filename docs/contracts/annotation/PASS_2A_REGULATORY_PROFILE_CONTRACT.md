# Pass 2A — Regulatory Profile (M13)

**Version :** 1.0.1  
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

Si H1 est absent (`regulatory_profile_skeleton` null) alors que le document exige un profil réglementaire, Pass 2A retourne **`PassRunStatus.SKIPPED`** avec `m13_skip_reason` — aucun rapport M13 complet n’est produit.

---

## Entrées

- **`document_id`** : identifiant document courant.
- **`case_id`** : identifiant dossier (persistance RLS). Avec **`ANNOTATION_USE_PASS_2A=1`**, l’orchestrateur **exige** un `case_id` réel : sinon Pass 2A est **ignoré** (`SKIPPED`, raison `case_id_required_when_annotation_use_pass_2a`) et l’état reste `pass_1d_done` — **pas** de repli sur `document_id` comme `case_id`.
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

- **Données M12 invalides (Pydantic)** : `PassRunStatus.FAILED` + code `PASS_2A_M12_INVALID` dans `errors`, `output_data` vide — pas d’exception non gérée vers l’orchestrateur.
- **Échec moteur / YAML / runtime hors validation M12** : `PassRunStatus.DEGRADED` avec `output_data` **non vide** (`pass_2a_degraded`, `m13_review_required`, `degraded_reason`) + erreur `PASS_2A_DEGRADED` — pas d’exception non gérée vers l’orchestrateur. Ce cas **n’est pas** traité comme `FAILED` binaire pour la passe.
- **SKIPPED** : absence H1 ou absence `case_id` lorsque Pass 2A est exigé côté orchestrateur — voir préconditions ci-dessus.
