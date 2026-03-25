# PASS_0_INGESTION_CONTRACT

**Passe** : `pass_0_ingestion`  
**Version** : `1.0.0`  
**Enveloppe** : [PASS_OUTPUT_STANDARD.md](./PASS_OUTPUT_STANDARD.md)

---

## Rôle

- Normaliser le texte (espaces, unicode de base) — **sans** invention de contenu.
- Produire une `page_map` (structure minimale : liste de segments `{page_index, char_start, char_end}` ou équivalent documenté).
- Extraire des **features documentaires** non décisionnelles : longueur, détection PDF natif vs scan (signal depuis métadonnées amont si disponibles), ratio caractères non alphanumériques, etc.
- **Interdit** : toute décision métier (taxonomie, rôle document, gates).

---

## `output_data` (schéma minimal v1)

```json
{
  "normalized_text": "<str>",
  "normalization_notes": ["<str>"],
  "page_map": [
    {"page_index": 0, "char_start": 0, "char_end": 1200}
  ],
  "features": {
    "char_count": 0,
    "line_count": 0,
    "non_alnum_ratio": 0.0,
    "extraction_method_hint": "native_pdf | tesseract | unknown"
  }
}
```

---

## `status`

- `success` : texte normalisé non vide exploitable pour Pass 0.5.
- `failed` : entrée vide ou corruption ; `errors` obligatoire.

---

## Dépendances

- Entrée : texte brut + optionnellement métadonnées fichier (mime, `document_id`).
