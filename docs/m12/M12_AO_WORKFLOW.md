# M12 — Flux AO : 15 × `annotated_validated` (Phase B)

Réf. gel : [ANNOTATION_FRAMEWORK_DMS_v3.0.1.md](../freeze/ANNOTATION_FRAMEWORK_DMS_v3.0.1.md) (BP-07, BP-12), [DMS_V4.1.0_FREEZE.md](../freeze/DMS_V4.1.0_FREEZE.md) (RÈGLE-23).

## 1. Corpus 15 documents

- Couvrir **familles A + B + C** (pas PV / rapports d’évaluation comme matière M12 — voir framework).
- Mélange **PDF natifs** exploitables ; PDF scan sans texte → OCR hors scope beta (M10A) : éviter ou marquer `review_required`.

## 2. Découpage train / test (BP-12)

| Ensemble | Nombre | Règle |
|----------|--------|--------|
| **Train** | 12 | Ne pas utiliser pour évaluation finale recognizer |
| **Test** | 3 | Isolés dès l’import (tag LS, préfixe id, ou liste séparée) |

Documenter la liste des **3** IDs de tâches test dans `data/annotations/M12_TRAIN_TEST_SPLIT.md` (à créer par AO lors du premier batch).

## 3. Import Label Studio

Chaque tâche doit avoir au minimum :

- `data.text` : contenu (extrait PDF/Excel/texte).
- Optionnel : `data.document_role` : rôle DMS pour LOI 1bis / Mistral (ex. `dao`, `rfq`, `tdr_consultance_audit`).

### Script d’aide

[`scripts/extract_for_ls.py`](../../scripts/extract_for_ls.py) génère :

- `scripts/ls_import.json` — métadonnées brutes (rétrocompat).
- `scripts/ls_tasks_labelstudio.json` — **format import LS** : `[{ "data": { "text", "document_role", "source" } }]`.

Importer via Label Studio : **Import** → JSON.

## 4. Boucle annotateur

Pour chaque tâche :

1. Lancer **Predict** (ML backend).
2. Vérifier / corriger le JSON dans **extracted_json**.
3. Remplir **routing_ok**, **financial_ok**, **annotation_notes** si besoin.
4. **annotation_status** : choisir **annotated_validated** uniquement si le JSON et les choix sont validés — **seul ce statut compte pour M12**.

## 5. Critère de sortie Phase B

**15** tâches avec **annotation_status = annotated_validated** (comptage manuel ou export LS).
