# PASS_0_5_QUALITY_GATE_CONTRACT

**Passe** : `pass_0_5_quality_gate`  
**Version** : `1.0.0`  
**Enveloppe** : [PASS_OUTPUT_STANDARD.md](./PASS_OUTPUT_STANDARD.md)

---

## Rôle

Classer la matière textuelle en vue de la suite du pipeline :

| Classe | Signification |
| --- | --- |
| `good` | Texte exploitable pour LLM / extraction structurée |
| `degraded` | Exploitable avec prudence (bruit modéré) |
| `poor` | Forte dégradation — LLM déconseillé ou prompt allégé |
| `ocr_failed` | Matière inexploitable — **stop** LLM, rescan / autre source |

Seuils numériques : voir [PASS_0_5_EMPIRICAL_THRESHOLDS.md](./PASS_0_5_EMPIRICAL_THRESHOLDS.md) (calibrés sur corpus).

---

## `output_data`

```json
{
  "quality_class": "good | degraded | poor | ocr_failed",
  "metrics": {
    "char_count": 0,
    "word_count": 0,
    "non_alnum_ratio": 0.0,
    "replacement_char_hits": 0
  },
  "block_llm": true,
  "operator_hints": ["rescan", "alt_source"]
}
```

- **`block_llm`** : si `true`, l’orchestrateur **ne** déclenche pas d’appel LLM sur ce document (sauf mandat d’exception explicite).

---

## `status`

- `success` : classification posée.
- `degraded` : classification posée mais métriques partielles (ex. page_map incomplète).
- `failed` : impossible de classer ; `errors` rempli.
