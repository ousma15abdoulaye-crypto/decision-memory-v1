# PASS_0_5_EMPIRICAL_THRESHOLDS — Seuils quality gate

**Version** : `1.0.0`  
**Date** : 2026-03-24

---

## 1. Méthode

1. Exporter les tâches Label Studio (JSONL) avec le champ texte source (`data.text` ou équivalent export).
2. Lancer [`scripts/derive_pass_0_5_thresholds.py`](../../../scripts/derive_pass_0_5_thresholds.py) sur les fichiers :
   ```bash
   python scripts/derive_pass_0_5_thresholds.py path/to/export1.jsonl path/to/export2.jsonl
   ```
3. Noter dans ce document : **N**, percentiles `char_count`, `non_alnum_ratio`, distribution `replacement_char_hits` ().
4. Ajuster les classes `good | degraded | poor | ocr_failed` quand **N ≥ 15** documents terrain.

Tant que le corpus exportable &lt; 15 : utiliser les **seuils provisoires** §2 (alignés code existant).

---

## 2. Seuils provisoires (alignement code actuel)

Références :

- [`src/extraction/engine.py`](../../../src/extraction/engine.py) : `INSUFFICIENT_TEXT_THRESHOLD = 100`
- [`services/annotation-backend/backend.py`](../../../services/annotation-backend/backend.py) : `MIN_LLM_CONTEXT_CHARS = 100`, `MIN_PREDICT_TEXT_CHARS = 200`

| Métrique | `ocr_failed` | `poor` | `degraded` | `good` |
| --- | --- | --- | --- | --- |
| `char_count` (normalisé) | &lt; 100 | 100–199 | 200–999 | ≥ 1000 |
| `non_alnum_ratio` | — | &gt; 0.45 | 0.25–0.45 | &lt; 0.25 |
| `replacement_char_hits` () | &gt; 50 | 20–50 | 5–19 | ≤ 4 |

- **`block_llm`** : `true` si `ocr_failed` **ou** (`poor` **et** politique stricte mandatée).

---

## 3. Résultats empiriques (à remplir AO)

| Date | Fichiers source | N docs | Notes |
| --- | --- | ---: | --- |
| _à remplir_ | | | |

---

## 4. Révision

Tout changement de seuil = bump `pass_version` Pass 0.5 + entrée tableau §3 + tests unitaires seuils.
