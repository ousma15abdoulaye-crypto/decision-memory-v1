# Annotation backend (Label Studio ML)

## Endpoints

| Méthode | Chemin | Rôle |
| --- | --- | --- |
| GET | `/health` | Santé + version schéma / modèle |
| POST | `/setup` | Appelé par LS au branchement du modèle |
| POST | `/predict` | Prédictions ML (JSON dans le textarea LS) |
| POST | `/webhook` | Événements LS (robuste, toujours 200 si possible) |

## Contrat `/predict` (tâche Label Studio)

- **Entrée** : `{"tasks": [{"id": …, "data": {…}}], …}`
- **`data.text`** ou **`data.content`** : texte source (obligatoire pour inférence).
- **`data.document_role`** (optionnel) : contexte LOI 1bis pour Mistral ; sinon repli sur `document_role` à la racine du body si présent.
- **Sortie** (JSON valide, schéma minimal) :

```json
{
  "results": [
    {
      "id": 1,
      "score": 0.9,
      "result": [
        {
          "from_name": "extracted_json",
          "to_name": "document_text",
          "type": "textarea",
          "value": {
            "text": ["{\"_meta\": {\"review_required\": false}}"]
          }
        }
      ]
    }
  ]
}
```

Alignement XML : `label_studio_config.xml` — `toName="document_text"`.

## Variables d’environnement (rappel)

- `MISTRAL_API_KEY`, `MISTRAL_MODEL`, `CORS_ORIGINS`, `PSEUDONYM_SALT` (voir `backend.py`).

Réf. gouvernance : `docs/freeze/PIPELINE_REFONTE_FREEZE.md`, `CLAUDE.md`.

**M12 (engagement annotation)** : [`docs/m12/README.md`](../../docs/m12/README.md).
