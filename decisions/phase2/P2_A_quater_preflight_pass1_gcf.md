# P2-A-quater — Preflight Pass -1 GCF

**Mandat** : DMS-MANDAT-P2-A-QUATER-PREFLIGHT-PASS1-GCF-V1  
**Autorité** : CTO principal DMS  
**Date** : 2026-04-24  
**Statut** : ✅ COMPLÉTÉ — Rapport preflight établi

---

## 1. Environnement d'exécution Pass -1

### 1.1 Architecture identifiée

**Point d'entrée** : Tâche ARQ async `run_pass_minus_1()`  
**Fichier** : `src/workers/arq_tasks.py` (ligne 114-297)  
**Worker ARQ** : `src/workers/arq_config.py` → `WorkerSettings.functions`

**Invocation** :
```bash
arq src.workers.arq_config.WorkerSettings
```

**Graphe LangGraph** : `src/assembler/graph.py` → `build_pass_minus_one_graph()`

**Pipeline** : `extract_node` → `classify_node` → `bundle_node` → `hitl_check_node` → `finalize_node`

### 1.2 Déploiement actuel

**Local** : ✅ Importable (test import réussi)  
**Railway worker** : ❓ Non vérifié — service `worker-railway` existe mais ne déploie que FastAPI DB proxy (pas ARQ)  
**Dépendance langgraph** : ✅ Importable sans erreur

**Conclusion environnement** : Pass -1 **exécutable localement** via ARQ worker Python.

---

## 2. Sources d'entrée ZIP supportées

### 2.1 Modes d'entrée

**Mode 1 — Filesystem local** :  
- Paramètre `zip_path` : chemin fichier local existant  
- Usage : Tests, scripts locaux, repli sans R2  
- Condition : Fichier `.zip` accessible lecture

**Mode 2 — R2 Object Storage** :  
- Paramètre `zip_r2_key` ou lecture `process_workspaces.zip_r2_key`  
- Téléchargement temporaire R2 → filesystem → exécution  
- Condition : R2 configuré (R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME)

**Mode 3 — UPLOADS_DIR** :  
- Variable env `UPLOADS_DIR` (défaut `/data/uploads`)  
- Repli filesystem si R2 non configuré  
- Worker ARQ vérifie accessibilité au démarrage (`arq_worker_on_startup`)

### 2.2 Documents GCF — Faisabilité

**Documents disponibles** : `data/imports/annotation/SUPPLIERS BUNDLE TEST OFFRES COMPLETE/GCF`

**3 PDFs ciblés** :
1. `ITT Baseline GCF_vf_vf.pdf` (477 KB)
2. `OFFE AZ/Offre Technique.pdf` (11 MB)
3. `OFFRE ATMOST/Offre technique.pdf` (2.1 MB)

**ZIP requis** : Créer archive ZIP contenant les 3 PDFs (structure : 1 dossier par fournisseur ou flat)

**Faisabilité** : ✅ GCF peut passer dans Pass -1 **sans modification code** — ZIP standard attendu.

---

## 3. Dépendances techniques

### 3.1 Variables environnement

**Obligatoires** :
- `DATABASE_URL` : Connexion PostgreSQL Railway production (✅ disponible)
- `MISTRAL_API_KEY` : Clé API Mistral OCR (✅ `.env.example` ligne 34)
- `REDIS_URL` : Redis pour ARQ (❓ requis pour ARQ worker, non vérifié disponibilité Railway)

**Optionnelles** :
- `UPLOADS_DIR` : Répertoire uploads (défaut `/data/uploads`, utilisable local Windows via chemin absolu)
- `DMS_PASS1_HEADLESS` : Pass -1 mode headless (CI/E2E, contourne HITL interrupt) — **ne pas activer en prod**
- `MISTRAL_SSL_VERIFY` : SSL verify Mistral API (défaut 1)
- R2 Object Storage (R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, etc.) : Non requis si ZIP fourni en filesystem local

### 3.2 Dépendances Python

**Vérifiées importables** :
- `langgraph` : ✅ Import réussi
- `src.assembler.graph` : ✅ Import réussi
- `src.assembler.ocr_mistral` : ✅ Présent
- `arq` : ✅ Import conditionnel réussi dans `arq_config.py`
- `httpx` : Requis par `ocr_with_mistral()` (client async Mistral API)
- `pypdf` : Requis par `ocr_native_pdf()` (PDF natif gratuit)

**Conclusion dépendances** : Environnement local complet.

---

## 4. Chaîne canonique Pass -1 (prouvée)

### 4.1 Déclenchement API → ARQ

**Point d'entrée API** : `POST /api/workspaces/{id}/upload-zip`  
**Fichier** : `src/api/routers/workspaces.py` (ligne 892-928)

**Séquence** :
1. Upload ZIP → R2 Object Storage (`zip_r2_key` persisté `process_workspaces`)
2. Enqueue job ARQ : `pool.enqueue_job("run_pass_minus_1", workspace_id, tenant_id, zip_path, zip_r2_key)`
3. Log : `[W1] Pass-1 enqueued workspace=...`

**Dépendance** : `REDIS_URL` (ligne 916)

### 4.2 Worker ARQ Railway

**Déploiement Railway** : Service séparé (référence `railway.worker.toml` ligne 16)  
**Commande démarrage** : `python -m arq src.workers.arq_config.WorkerSettings`  
**Config worker** : `src/workers/arq_config.py` ligne 81-98

**Tâches enregistrées** (ligne 85-92) :
- `index_event`
- `detect_patterns`
- `generate_candidate_rules`
- **`run_pass_minus_1`** (ligne 89)
- `project_workspace_events_to_couche_b`
- `project_sealed_workspace`

**Variables requises** :
- `DATABASE_URL`
- `REDIS_URL`
- `UPLOADS_DIR` ou R2 config (si R2 : R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME)
- `MISTRAL_API_KEY`

### 4.3 Exécution ARQ → Graphe LangGraph

**Tâche** : `src/workers/arq_tasks.py` ligne 114-297 (`run_pass_minus_1`)

**Flux** :
1. Récupère ZIP depuis R2 (`zip_r2_key`) ou filesystem local (`zip_path`)
2. Construit graphe LangGraph : `build_pass_minus_one_graph()`
3. Exécute pipeline : `extract` → `classify` → `bundle` → `hitl_check` → `finalize`
4. Persistance : `finalize_node()` → `bundle_writer.write_bundle()` → DB `supplier_bundles` + `bundle_documents`

**RLS tenant** : Posé ligne 144 (`set_db_tenant_id(tenant_id)`)

**Log** : `[PASS-1] Terminé workspace=... bundles=...`

### 4.4 État déploiement Railway (non prouvé)

**Prouvé par code** :
- ✅ Worker ARQ défini (`railway.worker.toml`, `arq_config.py`)
- ✅ Tâche `run_pass_minus_1` enregistrée
- ✅ API enqueue job via `pool.enqueue_job`
- ✅ Pipeline Pass -1 complet (`graph.py`, `ocr_mistral.py`, `bundle_writer.py`)

**Non prouvé** :
- ❓ Service ARQ worker déployé Railway production (pas de logs Railway visibles, pas d'accès dashboard)
- ❓ Redis déployé Railway production (`REDIS_URL` configuré)
- ❓ R2 Object Storage configuré (`R2_ENDPOINT_URL`, clés, bucket)

**Manque de visibilité** : Infrastructure Railway non radiographiée (pas d'accès CLI/dashboard, pas de logs fournis).

---

## 5. Obstacles identifiés

### O1 — ZIP GCF non préparé

**Statut** : ⚠️ BLOQUANT (préparation manuelle requise)  
**Description** : Documents GCF disponibles filesystem mais **pas archivés en ZIP**.  
**Action** : Créer `gcf_baseline.zip` contenant 3 PDFs avant upload API.

**Structure recommandée ZIP** :
```
gcf_baseline.zip
├── ITT/
│   └── ITT Baseline GCF_vf_vf.pdf
├── AZ/
│   └── Offre Technique.pdf
└── ATMOST/
    └── Offre technique.pdf
```

### O2 — État déploiement Railway non verified

**Statut** : ❓ MANQUE VISIBILITÉ  
**Description** : Chaîne canonique **prouvée par code** mais **déploiement Railway non verified**.  
**Impact** : Impossible confirmer si worker ARQ + Redis + R2 sont opérationnels en production.

**Prérequis vérification** :
- Accès Railway CLI : `railway logs --service arq-worker` (ou nom service exact)
- Accès Railway dashboard : Variables `REDIS_URL`, `R2_ENDPOINT_URL`, état services
- Ou logs API Railway après tentative upload ZIP : présence `[W1] Pass-1 enqueued`

**Pas d'autorité pour contourner** : Chaîne canonique existante doit être radiographiée, pas remplacée.

---

---

## 6. Verdict preflight

**FAISABILITÉ PASS -1 GCF** : ✅ **CONFIRMÉE** — aucune modification code requise.

**CHAÎNE CANONIQUE** : ✅ **PROUVÉE PAR CODE** — `API upload-zip` → `ARQ enqueue` → `Worker run_pass_minus_1` → `LangGraph extract/OCR/bundle` → `DB persistence`.

**OBSTACLES IDENTIFIÉS** :
1. ⚠️ ZIP GCF non préparé (bloquant mineur, 5 min travail)
2. ❓ État déploiement Railway non vérifié (manque visibilité infrastructure production)

**MANQUE VISIBILITÉ** : Worker ARQ + Redis + R2 déployés Railway production **non prouvés** — pas d'accès logs/dashboard Railway, pas de screenshots services, pas de variables env visibles.

**BASELINE OCR DÉBLOCABLE** : Conditionnel à vérification infrastructure Railway opérationnelle.

**PROCHAIN ACTE** :
- **Si Railway opérationnel** : Création ZIP + upload API `POST /api/workspaces/{id}/upload-zip` → chaîne canonique
- **Si Railway incomplet** : Escalade CTO pour radiographie infrastructure + décision déblocage
- **Aucun contournement autorisé** sans GO CTO explicite

---

**Statut final** : ✅ PREFLIGHT COMPLÉTÉ — Chaîne canonique radiographiée, manque visibilité déploiement  
**Dernière révision** : 2026-04-24 (correctif recadrage CTO)  
**Budget consommé** : 45 min (lecture code + rapport + correctif)
