# P2-A-bis — Découverte : chemin canonique Mistral OCR (vérité code)

**Mandat** : DMS-MANDAT-P2A-BIS-DISCOVERY-MISTRAL-CANONIQUE-V1  
**Date** : 2026-04-24  
**Chantier** : P3.4-INFRA-STABILIZATION — Phase 2 I-DEBT-1 — mission de découverte ciblée  
**Branche** : `chore/p3-4-infra-stabilization`

---

### 1. Contexte et périmètre

- **Mission** : identifier **dans le code et la configuration existants** où et comment DMS enchaîne vers **Mistral OCR** (modèle / API OCR Mistral), sans architecture ni correctif.
- **Interdit** : aucune vérité parallèle ; tout ce qui suit est **observé** dans les fichiers listés en section 2.
- **Prérequis mandat** : `MISTRAL_API_KEY` est supposée injectable en prod ; le rapport décrit **comment** le code la lit (différences selon fichier).

---

### 2. Fichiers inspectés

Chemins relatifs à la racine du dépôt :

- `src/assembler/ocr_mistral.py`
- `src/assembler/graph.py`
- `src/extraction/engine.py`
- `src/couche_a/llm_router.py`
- `src/core/config.py`
- `src/core/api_keys.py`
- `src/api/routes/extractions.py`
- `src/couche_a/extraction/text_extraction.py`
- `src/couche_a/extraction/offer_pipeline.py`
- `scripts/ingest_to_annotation_bridge.py`
- `services/annotation-backend/backend.py`
- `src/workers/arq_tasks.py`

---

### 3. Chemin canonique Mistral OCR identifié

Le dépôt contient **deux** implémentations distinctes qui appellent une capacité OCR Mistral (`mistral-ocr-latest`), sans fusion en un seul module. Les deux sont « canoniques » au sens où elles sont présentes et enchaînées dans des flux réels ; elles ne sont **pas** interchangeables (API HTTP JSON vs SDK fichiers).

#### 3.A — Pass -1 (ZIP → documents, LangGraph)

- **Fichier** : `src/assembler/ocr_mistral.py`
- **Fonction** : `ocr_with_mistral(file_path: str | Path) -> dict`
- **Appelant direct observé** : `extract_node` dans `src/assembler/graph.py` — pour `FileType.SCAN` ou `FileType.IMAGE` après `detect_file_type` ; en cas d’`error` sur le dict retourné, enchaînement vers `ocr_with_azure` (hors Mistral, non détaillé ici).
- **Enchaînement amont** : `build_pass_minus_one_graph()` → nœud `extract` ; graphe invoqué depuis `run_pass_minus_1` dans `src/workers/arq_tasks.py` (constat grep : import `build_pass_minus_one_graph`).

#### 3.B — Moteur d’extraction SLA-B (documents base + bridge)

- **Fichier** : `src/extraction/engine.py`
- **Fonction** : `_extract_mistral_ocr(storage_uri: str) -> tuple[str, dict]`
- **Appel observé** :
  - Via `_dispatch_extraction` lorsque `method == "mistral_ocr"` ou `method == "tesseract"` (commentaire code : alias legacy → `mistral_ocr`), avec `_retry_cloud_ocr(_extract_mistral_ocr, ...)`.
  - **Import direct** depuis `scripts/ingest_to_annotation_bridge.py` : `extract_with_route` appelle `_cloud_ocr_with_retry(_extract_mistral_ocr, real, "mistral_ocr")`.
- **Point d’entrée API** : `src/api/routes/extractions.py` importe `extract_async` / `extract_sync` depuis `src/extraction/engine.py` ; pour SLA-B, `trigger_extraction` appelle `extract_async(document_id, method)` lorsque la méthode du document est dans `SLA_B_METHODS`.

#### 3.C — Modèle OCR configuré (nom)

- **Fichier** : `src/couche_a/llm_router.py` — constantes `TIER_1_OCR_MODEL` synchronisées depuis `get_settings().TIER_1_OCR_MODEL`.
- **Fichier** : `src/core/config.py` — défaut `TIER_1_OCR_MODEL: str = "mistral-ocr-latest"`.
- **Fichier** : `src/assembler/ocr_mistral.py` — constante module `MISTRAL_OCR_MODEL = "mistral-ocr-latest"`.

---

### 4. Contrat technique observé

**Réponses directes aux six questions du mandat (synthèse)** :

1. **Fichiers d’entrée** : `src/assembler/ocr_mistral.py` (Pass -1) **et** `src/extraction/engine.py` (SLA-B / bridge) — deux points d’entrée code distincts.
2. **Fonctions / routes / jobs** : `ocr_with_mistral` ; `_extract_mistral_ocr` ; déclenchement API `POST /api/extractions/documents/{document_id}/extract` (`extractions.py`) pour méthodes SLA-B ; job worker `run_pass_minus_1` → graphe → `extract_node`. **Route** `/predict` : **pas** OCR Mistral.
3. **Input** : **fichier local** (chemin) dont le contenu est lu en **octets** (base64 dans JSON pour `ocr_with_mistral` ; upload stream pour `_extract_mistral_ocr`). Pas d’URL HTTP distante passée comme input dans le code de ces deux fonctions. **Pas** de « texte déjà extrait » en entrée de ces fonctions OCR.
4. **Output** : **texte** (`raw_text`, markdown pages) ; pour `ocr_with_mistral` un **dict** avec métadonnées moteur ; pour `_extract_mistral_ocr` un **tuple** `(str, dict)` avec dict vide structuré côté extraction.
5. **Persistance / transmission** : état Pass -1 / graphe puis chaîne bundles ; pour le moteur `_store_extraction` et statuts document via `extract_async` / `extract_sync` (détail des INSERT non rejoué ici). Bridge : texte consommé en aval du script hors fichier lu en entier.
6. **GCF sans modification code** : **partiellement, avec blocage précis** — double implémentation, clé **MISTRAL_API_KEY** requise selon voie (env brut vs Settings), et flux offre `extract_text_any` **sans** Mistral OCR.

#### 4.A — `ocr_with_mistral` (`src/assembler/ocr_mistral.py`)

| Élément | Fait observé |
|--------|----------------|
| **Entrée** | Chemin **fichier local** (`str` / `Path`). Le fichier est lu en octets, encodé **base64**, embarqué dans un JSON : `document` = `image_url` (data URI image/jpeg, png, tiff) ou `document_url` (data URI `application/pdf`) selon l’extension. |
| **Clé API** | `os.environ.get("MISTRAL_API_KEY", "")` — **pas** `get_mistral_api_key()` / Settings. |
| **Appel Mistral** | `httpx.AsyncClient.post("https://api.mistral.ai/v1/ocr", ...)` avec `json={"model": MISTRAL_OCR_MODEL, "document": document}`. |
| **Sortie** | `dict` : `raw_text` (concaténation des `page.get("markdown", "")` pour chaque entrée de `data["pages"]`), `confidence` fixé à `0.85` en succès, `ocr_engine` = `"mistral_ocr_3"`, `structured_json` = `None` ; en erreur : `raw_text` vide, `error` présent. |
| **Persistance / suite** | Le résultat est placé dans l’état LangGraph (`raw_documents` / `ocr_result` dans `extract_node` de `graph.py`) puis traité par les nœuds suivants du Pass -1 (hors périmètre lecture détaillée ici). |
| **GCF sans changement code** | **Partiellement, avec blocage précis** : ce chemin n’est emprunté que pour types **SCAN / IMAGE** dans Pass -1. La clé doit être dans **`MISTRAL_API_KEY`** côté **process** ; les alias `DMS_API_MISTRAL` documentés pour `annotation-backend` **ne sont pas** lus par `ocr_mistral.py`. Le flux « baseline extraction offre » GCF via `extract_offer_content` **n’utilise pas** cette fonction (voir 5). |

#### 4.B — `_extract_mistral_ocr` (`src/extraction/engine.py`)

| Élément | Fait observé |
|--------|----------------|
| **Entrée** | **`storage_uri`** : chaîne chemin fichier local ; ouverture `open(storage_uri, "rb")` ; validation taille (`_MISTRAL_OCR_MAX_BYTES`) et MIME par entête (`_MISTRAL_OCR_SUPPORTED_MIMES` = `image/`, `application/pdf`). |
| **Clé API** | `get_mistral_api_key()` → `src/core/api_keys.py` lit **`get_settings().MISTRAL_API_KEY`** uniquement (lève `APIKeyMissingError` si absent). |
| **Appel Mistral** | Client SDK `Mistral` avec `httpx.Client(verify=...)` ; `client.files.upload(..., purpose="ocr")` puis `client.ocr.process(model=TIER_1_OCR_MODEL, document={"type": "file", "file_id": uploaded_id})` ; `files.delete` en `finally`. |
| **Sortie** | Tuple `(raw_text: str, dict)` — `raw_text` via `_ocr_pages_to_text(response)` (markdown / texte des pages) ; second membre = `dict(STRUCTURED_DATA_EMPTY)` observé dans le code lu. |
| **Persistance / suite** | Chaînée depuis `extract_async` / `extract_sync` : le moteur appelle `_store_extraction` / statuts document (logique dans `engine.py` hors extrait détaillé ligne par ligne dans ce mandat). |
| **GCF sans changement code** | **Partiellement, avec blocage précis** : utilisé par le **bridge** et par l’API extractions si `extraction_method` est `mistral_ocr` (ou alias `tesseract`). Indépendant du dossier « GCF » nommé en data ; dépend des **méthodes d’extraction** et de la présence de **`MISTRAL_API_KEY`** dans Settings du service principal. |

#### 4.C — `/predict` (annotation-backend)

- **Entrée** : JSON Label Studio avec **texte déjà extrait** (`data.text` ou `data.content`).
- **Appel Mistral observé** : **chat** JSON (`_call_mistral`), **pas** `ocr.process` ni `/v1/ocr`.
- **Sortie** : JSON Label Studio `results` avec champs annotation (textarea JSON), **pas** `raw_text` OCR.

---

### 5. Ce que ce chemin n’est pas

- **`POST /predict`** (`services/annotation-backend/backend.py`) **n’est pas** le flux **Mistral OCR canonique** : c’est un flux **LLM sur texte** déjà fourni (`tasks[].data.text` ou `data.content`) ; `_call_mistral` utilise `client.chat.complete` avec `MISTRAL_MODEL` et `response_format={"type": "json_object"}` — **pas** `ocr.process` ni endpoint `/v1/ocr`.
- **`extract_text_any`** (`src/couche_a/extraction/text_extraction.py`) **n’appelle pas** Mistral OCR : la docstring indique explicitement « OCR (Mistral / Tesseract) = M10A — hors scope ici » ; PDF → pypdf/pdfminer (+ voie LlamaParse si clés Llama présentes, dans la suite du même fichier non entièrement re-lue pour ce mandat).
- **`extract_offer_content` / `extract_offer_content_async`** (`offer_pipeline.py`) : point d’entrée pipeline offre observé → **`extract_text_any`** puis appel **annotation backend** pour structuration — **pas** `_extract_mistral_ocr` ni `ocr_with_mistral` dans le fragment lu.
- **Aucune technologie OCR non nommée** dans les extraits lus n’est étiquetée « Mistral OCR » autrement que **Mistral OCR 3** / **`mistral-ocr-latest`** / endpoint **`/v1/ocr`** ou **`ocr.process`**.

---

### 6. Conclusion factuelle

**chemin canonique identifié mais non appelable en l'état, avec blocage précis**

**Motifs (factuels)** : (1) **deux** implémentations Mistral OCR coexistent (`ocr_with_mistral` httpx `/v1/ocr` vs `_extract_mistral_ocr` SDK fichiers) ; (2) **résolution de clé divergente** — Pass -1 lit seulement `MISTRAL_API_KEY` dans `os.environ`, le moteur SLA-B lit `MISTRAL_API_KEY` via **Settings** ; (3) le flux **offre / `extract_text_any`** pertinent pour une partie des scénarios « GCF » en extraction couche A **n’inclut pas** Mistral OCR dans le code inspecté ; (4) **`/predict`** est un flux **LLM texte → JSON**, pas OCR.
