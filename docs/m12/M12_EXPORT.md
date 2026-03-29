# M12 — Export JSONL ground truth (Phase C)

**Pipeline industrialisé (nouveau projet LS, backups, anti-perte)** : [`M12_PIPELINE_INDUSTRIAL.md`](./M12_PIPELINE_INDUSTRIAL.md) — script `scripts/m12_corpus_backup.ps1`.

Scripts :

- Export **depuis le corpus R2/S3** (vérité de stockage en prod : **un objet = un fichier JSON** sous `m12-v2/…/*.json`, pas de JSONL dans le bucket) : [`scripts/export_r2_corpus_to_jsonl.py`](../../scripts/export_r2_corpus_to_jsonl.py) agrège ces JSON en **JSONL** local pour calibration (N≥50) ; Label Studio reste l’interface de correction, pas la source batch. Le script requiert `--output` pour définir le chemin du JSONL de sortie (aucune sortie par défaut, pas de variables d’environnement `M12_R2_EXPORT_JSONL` / `R2_EXPORT_JSONL`). Filtre statut : `--status` (une valeur) ou `--accepted-statuses annotated_validated,annotated`.
- Export **depuis l’API Label Studio** (historique / audits sans R2) : [`scripts/export_ls_to_dms_jsonl.py`](../../scripts/export_ls_to_dms_jsonl.py)
- **Consolidation local + R2** : [`scripts/consolidate_m12_corpus.py`](../../scripts/consolidate_m12_corpus.py) fusionne un ou plusieurs JSONL locaux avec le flux R2 (dédup par `stable_m12_corpus_line_id`, politique par défaut **R2 gagne** sur les doublons). Voir [Consolidation corpus](#consolidation-corpus-local--r2).
- **Delta R2 → local** (compléter un export partiel) : [`scripts/m12_r2_delta_vs_local.py`](../../scripts/m12_r2_delta_vs_local.py) n’écrit que les objets R2 **absents** des JSONL locaux (ex. 57 lignes locales vs 73 sur R2). Voir [Alignement laptop local &lt; R2](#alignement-laptop-local--r2).
- Validation : [`scripts/validate_annotation.py`](../../scripts/validate_annotation.py)
- Inventaire (lignes, IDs stables, `export_ok`, statuts LS) : [`scripts/inventory_m12_corpus_jsonl.py`](../../scripts/inventory_m12_corpus_jsonl.py) — ex. `data/annotations/m12_corpus_from_ls.jsonl` (gitignoré).

Réf. : [ADR-M12-EXPORT-V2](../adr/ADR-M12-EXPORT-V2.md)

## Dépôt temps réel (webhook)

Le backend [`services/annotation-backend/backend.py`](../../services/annotation-backend/backend.py) expose `POST /webhook`. Lorsque `CORPUS_WEBHOOK_ENABLED` est activé et que `LABEL_STUDIO_URL` / `LABEL_STUDIO_API_KEY` sont définis, chaque événement autorisé (voir `CORPUS_WEBHOOK_ACTIONS`) déclenche en arrière-plan la construction d’une **ligne m12-v2** (même logique que le script ci-dessous) et une écriture vers le sink configuré (`CORPUS_SINK`, S3 recommandé en prod). Le payload webhook est souvent incomplet : le service **re-fetch** la tâche via l’API LS si besoin. Optionnel : `WEBHOOK_CORPUS_SECRET` + header `X-Webhook-Secret`. Variables : [`services/annotation-backend/ENVIRONMENT.md`](../../services/annotation-backend/ENVIRONMENT.md).

L’export **batch** par script reste utile pour rejouer l’historique, audits et fichiers JSONL figés.

## Prérequis (export API)

- `LABEL_STUDIO_URL` — URL publique (ex. `https://label-studio-dms.up.railway.app`)
- `LABEL_STUDIO_API_KEY` — token API LS
- Projet aligné sur [`services/annotation-backend/label_studio_config.xml`](../../services/annotation-backend/label_studio_config.xml) (`extracted_json`, `document_text`)

**Secrets en local (sans les coller dans le chat ni les committer)** : placez ces variables dans **`.env.local`** à la racine du dépôt (gitignoré ; modèles `.env.local.example` / `.env.example`). Les scripts `export_ls_to_dms_jsonl.py`, `ls_local_autosave.py`, `backfill_corpus_from_label_studio.py` chargent **`.env`** puis **`.env.local`** au démarrage. Le script PowerShell [`scripts/run_m12_corpus_resync.ps1`](../../scripts/run_m12_corpus_resync.ps1) importe les mêmes fichiers avant d’appeler Python. Repli optionnel non versionné : `data/annotations/.ls_export_env` (voir l’en-tête du script).

## Commande type (format m12-v2, défaut)

```powershell
$env:LABEL_STUDIO_URL="https://<votre-instance>.up.railway.app"
$env:LABEL_STUDIO_API_KEY="<token>"
python scripts/export_ls_to_dms_jsonl.py --project-id 1 --output data/annotations/m12_batch_001.jsonl
```

Si les annotations sont **validées dans LS** mais l’export remonte `validated_but_evidence` (preuve non retrouvable dans le texte source / OCR), le JSON DMS peut quand même être valide : pour un corpus intermédiaire (calibration, inventaire), ajouter **`--no-enforce-validated-qa`** évite de mettre `export_ok=false` uniquement à cause de ce contrôle spot — le schéma Pydantic reste appliqué.

## Export hors API (fichier JSON Label Studio)

```powershell
python scripts/export_ls_to_dms_jsonl.py --from-export-json export_ls.json --output out.jsonl
```

## Ancien format (doc_type / ao_ref)

Si le projet LS utilise encore les champs mandat historiques :

```powershell
python scripts/export_ls_to_dms_jsonl.py --project-id 1 --output legacy.jsonl --legacy-mandat-fields
```

## Validation JSONL

Schéma seul (ligne = JSON DMS complet) :

```powershell
python scripts/validate_annotation.py data/annotations/m12_batch_001.jsonl
```

Lignes « wrapped » (clé `dms_annotation`, ex. copie d’export m12-v2) :

```powershell
python scripts/validate_annotation.py export.jsonl --wrapped --strict-financial
```

## Après export

1. Vérifier `export_ok` et `export_errors` sur chaque ligne (m12-v2).
2. SHA256 du fichier pour traçabilité :

   ```powershell
   Get-FileHash data/annotations/m12_batch_001.jsonl -Algorithm SHA256
   ```

3. Ne **pas** committer de données sensibles : voir [`data/annotations/README.md`](../../data/annotations/README.md).

## Backend ML — `STRICT_PREDICT`

Si `STRICT_PREDICT=1`, le service [`services/annotation-backend/backend.py`](../../services/annotation-backend/backend.py) refuse d’envoyer un JSON de pré-annotation lorsque schéma / finances / evidence échouent. Santé : `GET /health` expose `strict_predict`. Détail : [`services/annotation-backend/ENVIRONMENT.md`](../../services/annotation-backend/ENVIRONMENT.md).

## Attestations Label Studio (export)

Le XML inclut deux choix obligatoires (**evidence_attestation**, **no_invented_numbers**) avant correction du JSON. Pour exiger ces champs lorsque le statut est « VALIDÉ » :

```powershell
python scripts/export_ls_to_dms_jsonl.py --project-id 1 --output out.jsonl --require-ls-attestations
```

## Adoption downstream (Python)

Lire uniquement les lignes **m12-v2** validées :

```python
from pathlib import Path
from src.annotation.m12_export_io import iter_ok_dms_annotations

for dms in iter_ok_dms_annotations(Path("data/annotations/batch.jsonl")):
    taxonomy = dms["couche_1_routing"]["taxonomy_core"]
    ...
```

Détection du format : `export_line_kind(line)` / `dms_annotation_from_line(line)` dans [`src/annotation/m12_export_io.py`](../../src/annotation/m12_export_io.py).

Dédup entre sources : `stable_m12_corpus_line_id(line)` (même logique que les clés objet S3 : `content_hash` puis `(project_id, task_id, annotation_id)`).

## Alignement laptop (local &lt; R2)

Objectif typique : le disque local a un export **incomplet** (ex. 57 lignes) alors que le bucket R2 en a **davantage** (ex. 73), sans tout ré-exporter depuis l’API Label Studio.

1. **Vérité de qualité** : en cas de doublon, **R2 prime** sur un JSONL local obsolète (même schéma que la consolidation). Les statuts LS `annotated_validated` et `annotated` (libellé court ou export ancien) sont traités comme **candidats acceptés** pour l’inclusion depuis R2 ; le projet LS canonique n’expose que `annotated_validated` dans le XML actuel, mais l’historique R2 peut contenir l’autre libellé.
2. **Ne tirer que le manquant** (JSONL, une ligne = un JSON m12-v2) :

   ```powershell
   python scripts/m12_r2_delta_vs_local.py `
     --local-jsonl data/annotations/m12_local.jsonl `
     --output data/annotations/m12_r2_only_missing.jsonl `
     --only-export-ok
   ```

   Défaut `--accepted-statuses` : `annotated_validated,annotated`. Pour **strictement** validés : `--accepted-statuses annotated_validated`.

3. **Corpus unique pour M12** : fusionner local + delta + overlay R2 (R2 gagne encore une fois sur toute ligne déjà présente deux fois) :

   ```powershell
   python scripts/consolidate_m12_corpus.py `
     -i data/annotations/m12_local.jsonl `
     -i data/annotations/m12_r2_only_missing.jsonl `
     --from-r2 `
     --r2-accepted-statuses annotated_validated,annotated `
     -o data/annotations/m12_consolidated.jsonl `
     --only-m12-v2 --only-export-ok `
     --manifest data/annotations/m12_consolidate_manifest.json
   ```

4. **Contrôle qualité** : `python scripts/validate_annotation.py data/annotations/m12_consolidated.jsonl --wrapped --strict-financial` ; dans Label Studio, ouvrir **deux tâches** au hasard parmi celles ajoutées par le delta et vérifier cohérence avec le JSON exporté.
5. **Export LS complet** (si besoin d’historique hors R2) : [`scripts/export_ls_to_dms_jsonl.py`](../../scripts/export_ls_to_dms_jsonl.py) — voir [Commande type](#commande-type-format-m12-v2-défaut).

## Consolidation corpus (local + R2)

Objectif : un **seul JSONL** pour calibration ou audit, en unissant les exports LS locaux et le corpus déjà poussé sur R2, **sans doublons** (une ligne par identité d’annotation).

- **Défaut (`--from-r2` sans `--r2-first`)** : lire tous les `--input` dans l’ordre, puis le flux R2. En cas de même clé stable, **la version R2 remplace** la version locale (aligné ADR : R2 = vérité de stockage).
- **`--r2-first`** : lire R2 d’abord, puis les `--input` : **le local remplace** R2 pour les doublons (utile si vous réinjectez une correction offline avant ré-upload).

Filtres optionnels (comme l’export R2) : `--r2-status`, `--r2-accepted-statuses` (liste CSV, remplace `--r2-status` si défini), `--r2-no-status-filter`, `--r2-project-id`, `--r2-limit`. Filtres sur le JSONL fusionné : `--only-m12-v2`, `--only-export-ok`. `--manifest` écrit un JSON de comptage par source.

Exemple (PowerShell, mêmes variables `S3_*` que [`export_r2_corpus_to_jsonl.py`](../../scripts/export_r2_corpus_to_jsonl.py)) :

```powershell
python scripts/consolidate_m12_corpus.py `
  --input data/annotations/m12_batch_local.jsonl `
  --from-r2 `
  --output data/annotations/m12_consolidated.jsonl `
  --manifest data/annotations/m12_consolidate_manifest.json `
  --only-export-ok
```

## Perte session Label Studio — réparation locale / R2

Les objets R2 peuvent avoir ``dms_annotation`` null si ``extracted_json`` était vide ou invalide au moment du webhook (déconnexion LS, payload incomplet, etc.). **Le contenu annoté disparu ne peut pas être magiquement reconstruit** depuis R2 seul sans re-saisie, re-prédiction ML (``/predict`` sur ``source_text``) ou export LS rechargé.

**Formule DMS valide (références du dépôt, sans modifier ``schema_validator.py`` gelé) :**

- Objet JSON complet **v3.0.1d** versionné pour la CI : ``data/annotations/fixtures/golden_dms_line.jsonl`` (une ligne = un document DMS).
- Variante minimale en Python (tests) : ``_minimal_valid()`` dans ``services/annotation-backend/tests/test_schema_validator.py``.
- Squelette « tout ABSENT / AMBIGUOUS » côté backend : ``_build_fallback_response()`` dans ``services/annotation-backend/backend.py`` (import lourd — réservé contexte serveur).

**Script de backfill structurel** (injecte le golden + ``AMBIG-R2_LS_SESSION_LOSS``, statut ``review_required``, puis recalcule la ligne via ``ls_annotation_to_m12_v2_line``) :

```powershell
.\.venv\Scripts\python.exe scripts\repair_m12_jsonl_golden_backfill.py `
  -i data\annotations\m12_corpus_authoritative.jsonl `
  -o data\annotations\m12_corpus_authoritative_repaired.jsonl
```

Ensuite : dédoublonner si besoin (mêmes ``task_id`` / ``annotation_id``), **ré-uploader** les JSON vers R2 (mêmes clés S3 ou politique CTO), puis enrichir le JSON document par document (humain ou LLM) avant de repasser en ``annotated_validated``.

## Ingestion bridge — `structured_preview`

Chaque tâche émise par [`scripts/ingest_to_annotation_bridge.py`](../../scripts/ingest_to_annotation_bridge.py) contient `data.structured_preview` (tables détectées sur les N premières pages, métadonnées pdfplumber). Désactiver : `--structured-preview-pages 0`.
