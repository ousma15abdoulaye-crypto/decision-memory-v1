# PR — M-INGEST-TO-ANNOTATION-BRIDGE-00

**Titre proposé :**  
`feat(ingest): M-INGEST-TO-ANNOTATION-BRIDGE-00 — bridge local PDF → ls_tasks.json (DONE partiel mergeable)`

**Base :** `main` (ou branche cible équivalente)  
**Source :** `feat/ingest-to-annotation-bridge-00`

---

## Contenu réel de la PR (branche = mandat bridge + merge main + garde-fous CI)

Cette branche **dépasse** le périmètre minimal du mandat initial (un seul script + tests) : elle intègre les **résolutions de conflit** avec `main` et les **correctifs lint** nécessaires pour faire passer la CI. Le tableau ci-dessous reflète **ce qui est effectivement modifié** dans la PR — à utiliser pour la revue.

| Zone | Fichiers typiques |
|------|-------------------|
| Bridge ingest | `scripts/ingest_to_annotation_bridge.py` — PDF → `ls_tasks.json` / `skipped.json` ; classification sur **sonde locale** (`extract_pdf_text_local_only`) ; `source_roots` non vide ; pas d’`IndexError` si racines absentes pour `STORAGE_BASE_PATH`. |
| Tests bridge | `tests/test_ingest_to_annotation_bridge.py` |
| Couche A extraction | `src/couche_a/extraction.py` — `_extract_pdf_text(..., skip_llamaparse=)` ; **`extract_pdf_text_local_only`** pour heuristiques sans LlamaParse ; imports / containment (merge main). |
| Annotation backend | `services/annotation-backend/backend.py` , `services/annotation-backend/tests/test_predict.py` — garde-fous `/predict`, Ruff/Black. |
| Autres (merge main) | Ex. `src/couche_a/routers.py`, `tests/couche_a/test_extract_text_any.py`, `tests/couche_a/test_annotation_backend_predict_payload.py`, `tests/test_annotation_containment_01.py`, `tests/test_annotation_backend_validation.py` selon historique de merge. |
| Docs mandat | `docs/freeze/CONTEXT_ANCHOR.md`, `docs/milestones/HANDOVER_M_INGEST_ANNOTATION_BRIDGE_00.md`, `docs/freeze/M_INGEST_BRIDGE_00_SKIPPED_SCANNED_PDFS.md`, ce fichier |
| Données / ignore | `.gitignore` / `data/ingest/test_mistral/.gitkeep` si présents sur la branche |

**Ne pas committer :** PDFs sous `data/ingest/test_mistral/`, ni `*_output/*.json` (gitignore / politique données).

---

## État prouvé (run `test-mistral-run`)

Extrait de `data/ingest/test_mistral_output/ingest_report.json` (généré localement, non versionné) :

```json
{
  "run_id": "test-mistral-run",
  "pdf_files_discovered": 221,
  "pdf_files_seen": 221,
  "tasks_emitted": 137,
  "tasks_skipped": 84,
  "by_engine": {
    "local": 137
  }
}
```

Résumé :

- **221** PDFs vus  
- **137** tâches émises (`ls_tasks.json`)  
- **84** skippés (`skipped.json`)  
- **`by_engine` : `{"local": 137}`** — tâches émises avec texte suffisant issu de la **voie locale (pypdf/pdfminer)** après classification ; OCR cloud (Mistral / Llama) **non effectif** sur le run de référence (voir ci-dessous).

---

## Scans non traités dans ce mandat

Les **84** skips correspondent à des PDFs **non convertis en tâche** avec texte exploitable : classification **`scanned_pdf`**, raison **`no_text_all_extractors`**, route **`blocked`**.

Liste exploitable : **`docs/freeze/M_INGEST_BRIDGE_00_SKIPPED_SCANNED_PDFS.md`** (dérivée de `skipped.json` au moment du run).

---

## Cause résiduelle (hors périmètre correctif de cette PR)

- **OCR cloud** (Mistral / Llama) **non effectif** sur l’environnement local du run : blocage **SSL / trust store** et/ou **clé Llama** non utilisable localement.  
- **Pas de contournement SSL** et **pas de réouverture d’architecture** dans ce mandat — le bridge reste mergeable ; le sous-lot scans sera repris dans un contexte où clés + TLS sont valides.

---

## Checklist merge

- [ ] `pytest tests/test_ingest_to_annotation_bridge.py -q`  
- [ ] `ruff check src tests` et `ruff check src/ services/` (gate milestones)  
- [ ] `black --check src tests` et `black --check src/ services/`  
- [ ] Revue : tableau « Contenu réel » ci-dessus  
- [ ] Aucun débat d’architecture hors scope — suite au handover  

---

**STOP** — description PR alignée sur le diff réel ; copier-coller sur la forge.
