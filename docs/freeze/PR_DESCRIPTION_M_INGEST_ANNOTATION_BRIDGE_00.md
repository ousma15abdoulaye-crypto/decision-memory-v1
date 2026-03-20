# PR — M-INGEST-TO-ANNOTATION-BRIDGE-00

**Titre proposé :**  
`feat(ingest): M-INGEST-TO-ANNOTATION-BRIDGE-00 — bridge local PDF → ls_tasks.json (DONE partiel mergeable)`

**Base :** `main` (ou branche cible équivalente)  
**Source :** `feat/ingest-to-annotation-bridge-00`

---

## Contenu de la PR (périmètre fermé)

| Livrable | Chemin |
|----------|--------|
| Script bridge | `scripts/ingest_to_annotation_bridge.py` |
| Tests bridge | `tests/test_ingest_to_annotation_bridge.py` |
| Context anchor (ajout mandat) | `docs/freeze/CONTEXT_ANCHOR.md` |
| Handover | `docs/milestones/HANDOVER_M_INGEST_ANNOTATION_BRIDGE_00.md` |
| Liste PDFs scannés non traités | `docs/freeze/M_INGEST_BRIDGE_00_SKIPPED_SCANNED_PDFS.md` |
| Texte PR (copier-coller forge) | `docs/freeze/PR_DESCRIPTION_M_INGEST_ANNOTATION_BRIDGE_00.md` |
| Ignore PDFs corpus local | `.gitignore` (ligne `data/ingest/test_mistral/**/*.pdf` uniquement si pas déjà sur `main`) |
| Marqueur dossier corpus (optionnel) | `data/ingest/test_mistral/.gitkeep` |

**Hors PR (ne pas mélanger) :** autres fichiers modifiés dans le working tree (backend, `extraction.py`, `engine.py`, `api_keys`, tests M11, etc.) — autre(s) PR ou mandat.

**Ne pas committer :** PDFs sous `data/ingest/test_mistral/`, ni `*_output/*.json` (déjà couverts par `.gitignore` / politique données).

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
- **`by_engine` : `{"local": 137}`** — toutes les tâches émises passent par l’extraction locale (pypdf/pdfminer / `extract_text_any`) ; **aucune** tâche via `mistral_ocr` / `llamaparse` sur ce run.

---

## Scans non traités dans ce mandat

Les **84** skips correspondent à des PDFs **non convertis en tâche** avec texte exploitable : classification **`scanned_pdf`**, raison **`no_text_all_extractors`**, route **`blocked`**.

Liste exploitable (chemins relatifs logiques + noms de fichier) : **`docs/freeze/M_INGEST_BRIDGE_00_SKIPPED_SCANNED_PDFS.md`** (dérivée de `skipped.json` au moment du run).

---

## Cause résiduelle (hors périmètre correctif de cette PR)

- **OCR cloud** (Mistral / Llama) **non effectif** sur l’environnement local du run : blocage **SSL / trust store** et/ou **clé Llama** non utilisable localement.  
- **Pas de contournement SSL** et **pas de réouverture d’architecture** dans ce mandat — le bridge reste mergeable ; le sous-lot scans sera repris dans un contexte où clés + TLS sont valides.

---

## Checklist merge

- [ ] `pytest tests/test_ingest_to_annotation_bridge.py -q`  
- [ ] Revue limitée au périmètre tableau ci-dessus  
- [ ] Aucun débat d’architecture dans les commentaires de PR — suite tracée au handover / prochain mandat  

---

**STOP** — description PR prête ; ouvrir la PR sur la forge avec ce corps (copier-coller).
