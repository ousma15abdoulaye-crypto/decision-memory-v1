# PASS_OUTPUT_STANDARD — Enveloppe commune des sorties de passe

**Statut** : contrat normatif — version **1.0**  
**Date** : 2026-03-24  
**Implémentation** : [`src/annotation/pass_output.py`](../../../src/annotation/pass_output.py)

---

## 1. Objet

Toute passe du pipeline d’annotation (Pass 0, 0.5, 1, …) **doit** produire un objet sérialisable conforme au modèle **`AnnotationPassOutput`** (Pydantic v2).

C’est le **seul** contrat entre passes et orchestrateur. Les champs métier spécifiques à une passe vivent dans `output_data` (JSON object) avec schéma documenté par le contrat de la passe.

---

## 2. Champs obligatoires (enveloppe)

| Champ | Type | Description |
| --- | --- | --- |
| `pass_name` | `str` | Identifiant stable : `pass_0_ingestion`, `pass_0_5_quality_gate`, `pass_1_router`, … |
| `pass_version` | `str` | SemVer de la passe (ex. `1.0.0`) |
| `document_id` | `str` | Identifiant document DMS ou placeholder LS (`ls_task:<id>`) |
| `run_id` | `UUID` | Identifiant d’exécution pipeline (une run peut contenir plusieurs passes) |
| `started_at` | `datetime` | UTC |
| `completed_at` | `datetime` | UTC |
| `status` | enum | `success` \| `degraded` \| `failed` \| `skipped` |
| `output_data` | `dict` | Charge utile — schéma défini par le contrat de la passe |
| `errors` | liste | `PassError` (code, message, detail optionnel) |
| `metadata` | `dict` | `model_used`, `token_count_prompt`, `token_count_completion`, `cost_estimate_usd`, `duration_ms`, … |

---

## 3. Statuts

- **`success`** : la passe a terminé dans les limites du contrat ; `output_data` complet.
- **`degraded`** : résultat partiel utilisable en aval avec prudence (ex. OCR faible mais texte non vide).
- **`failed`** : pas de garantie sur `output_data` ; l’orchestrateur décide (retry, DLQ, halt).
- **`skipped`** : passe non applicable (ex. document déjà qualifié `ocr_failed` en amont).

---

## 4. Sérialisation

- **JSON** : ISO-8601 pour datetimes, UUID en string.
- **Hash d’audit (recommandé)** : `sha256(json.dumps(output.model_dump(mode="json"), sort_keys=True))` pour append-only / traçabilité (mandat séparé).

---

## 5. Validation

- Tests : [`tests/annotation/test_pass_output.py`](../../../tests/annotation/test_pass_output.py)
- Toute nouvelle passe : PR jointe mise à jour du contrat markdown + tests golden si `output_data` structuré.
