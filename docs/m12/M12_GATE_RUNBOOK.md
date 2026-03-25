# M12 Gate Runbook — 15 × `annotated_validated`

**Référence** : [DMS_M12_CORPUS_GATE_EXECUTION.md](./DMS_M12_CORPUS_GATE_EXECUTION.md)  
**Objectif** : preuve binaire **≥ 15** enregistrements au statut **`annotated_validated`**.

**État terrain (2026-03-24)** : **22** documents `annotated_validated` ; corpus stocké sur **Cloudflare R2**. Gate **franchi** — ce runbook reste la référence procédurale pour les prochains lots.

---

## Prérequis

- Label Studio + ML backend déployé ([M12_INFRA_SMOKE.md](./M12_INFRA_SMOKE.md)).
- `PIPELINE_REFONTE_FREEZE` : bugs E-66 / E-67 / gates appliqués sur `backend.py`.
- Jeu de tâches importé ([M12_AO_WORKFLOW.md](./M12_AO_WORKFLOW.md)).

---

## Checklist opérateur (copier / cocher)

Pour chaque slot **1 à 15** :

| # | Task LS ID | Famille doc | Predict OK | JSON revu | `annotated_validated` | Notes |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | | | ☐ | ☐ | ☐ | |
| 2 | | | ☐ | ☐ | ☐ | |
| 3 | | | ☐ | ☐ | ☐ | |
| 4 | | | ☐ | ☐ | ☐ | |
| 5 | | | ☐ | ☐ | ☐ | |
| 6 | | | ☐ | ☐ | ☐ | |
| 7 | | | ☐ | ☐ | ☐ | |
| 8 | | | ☐ | ☐ | ☐ | |
| 9 | | | ☐ | ☐ | ☐ | |
| 10 | | | ☐ | ☐ | ☐ | |
| 11 | | | ☐ | ☐ | ☐ | |
| 12 | | | ☐ | ☐ | ☐ | |
| 13 | | | ☐ | ☐ | ☐ | |
| 14 | | | ☐ | ☐ | ☐ | |
| 15 | | | ☐ | ☐ | ☐ | |

**Train / test (BP-12)** : 12 train / 3 test — documenter les IDs test dans `data/annotations/M12_TRAIN_TEST_SPLIT.md` (voir template).

---

## Preuve de clôture (à archiver)

1. Export JSONL conforme [M12_EXPORT.md](./M12_EXPORT.md) / ADR-M12-EXPORT-V2.
2. Commande de comptage (exemple — adapter au champ exporté) :
   - filtrer les lignes où `_meta.annotation_status` ou champ équivalent = `annotated_validated`.
3. Date / signature AO : _______________

---

## Après le gate

Enclencher [DMS_ANNOTATION_MULTIPASS_POST_M12.md](./DMS_ANNOTATION_MULTIPASS_POST_M12.md) (contrats passes, FSM, migration).
