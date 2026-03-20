# HANDOVER — M-INGEST-TO-ANNOTATION-BRIDGE-00

**Statut : DONE partiel — mergeable**  
**Date clôture session : 2026-03-20**  
**Branche typique :** `feat/ingest-to-annotation-bridge-00` (ou équivalent local)

---

## 1. Verdict mandat

Le bridge **livre** : découverte PDF, extraction (Couche A + fallback engine), `ls_tasks.json` / `skipped.json` / `run_manifest.json` / `ingest_report.json`, CLI `--limit`, dossier `data/ingest/test_mistral`.

**Partiel** : une partie du corpus reste **sans texte exploitable** côté poste local (voir métriques et causes résiduelles). **Aucun contournement SSL** — pas de chantier ouvert là-dessus.

---

## 2. Métriques run de référence (`run_id: test-mistral-run`)

| Indicateur | Valeur |
|------------|--------|
| **pdf_files_seen** | **221** |
| **tasks_emitted** | **137** |
| **tasks_skipped** | **84** |

**Sorties** : `data/ingest/test_mistral_output/`  
**Manifest** : `run_manifest.json`  
**Skips** : `skipped.json` — les 84 entrées sont **toutes** `classification: scanned_pdf`, `reason: no_text_all_extractors`, `engine_route: blocked`.

---

## 3. Cause résiduelle (documentée, non « corrigée » dans ce mandat)

- **Scans** : texte natif insuffisant ; chaîne prévue = **Mistral OCR** / **LlamaParse** cloud.
- **Poste local** : **OCR cloud bloqué** (problème **SSL/TLS** côté environnement) + **absence de clé Llama utilisable localement** dans le même contexte.
- **Décision** : ne pas bloquer le plan global sur ce sous-lot ; merger le bridge ; traiter les scans dans un **sprint / environnement** où clés + TLS sont valides (ex. CI, Railway, poste corrigé).

---

## 4. Liste exploitable des PDFs scannés non faits

Fichier généré à partir de `skipped.json` :

- [`docs/freeze/M_INGEST_BRIDGE_00_SKIPPED_SCANNED_PDFS.md`](../freeze/M_INGEST_BRIDGE_00_SKIPPED_SCANNED_PDFS.md)

Pour régénérer après un nouveau run :

```powershell
python scripts/ingest_to_annotation_bridge.py `
  --source-root "data/ingest/test_mistral" `
  --output-root "data/ingest/test_mistral_output" `
  --run-id test-mistral-run
```

Puis réexécuter le script de génération de liste (voir historique commit ou régénérer manuellement depuis `skipped.json`).

---

## 5. Fichiers périmètre mandat (rappel)

- `scripts/ingest_to_annotation_bridge.py`
- `tests/test_ingest_to_annotation_bridge.py`
- Dossiers données : `data/ingest/test_mistral/` (PDFs locaux, gitignore ciblé), `data/ingest/test_mistral_output/`
- Docs : ce handover, `docs/freeze/M_INGEST_BRIDGE_00_SKIPPED_SCANNED_PDFS.md`, complément CONTEXT_ANCHOR

**Hors mandat explicite (mais présents sur la branche PR)** : merge `main` + correctifs CI (backend `/predict`, Ruff/Black, `extraction` containment + **`extract_pdf_text_local_only`** pour classification bridge sans biais LlamaParse). Ne pas les attribuer au seul script bridge sans relecture git.

---

## 6. STOP

Pas de réouverture d’architecture, pas de workaround SSL dans ce handover.
