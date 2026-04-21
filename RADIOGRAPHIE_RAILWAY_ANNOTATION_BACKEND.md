# RADIOGRAPHIE RAILWAY — annotation-backend vs extraction DMS

**Date** : 2026-04-20  
**URL testée** : `https://annotation-backend-production-5513.up.railway.app`  
**Verdict** : ⚠️ **MAUVAISE IMAGE DÉPLOYÉE** — Railway sert `dms-api` (Dockerfile racine) au lieu de `dms-annotation-backend` (services/annotation-backend/).

---

## 1. COURTE VÉRITÉ

Le service Railway nommé "annotation-backend" **répond avec l'identité `dms-api`** au lieu de `dms-annotation-backend`. Les endpoints **`/predict`** et **`/setup`** renvoient **404 Not Found**, ce qui **bloque les chemins ML offres** (`call_annotation_backend`), le **pipeline V5** sur bundles qui en dépendent, et le **handshake Label Studio** — pas l’ingestion DAO critères (`extract_dao_content`, hors `/predict`).

**Cause confirmée** : Railway build le **mauvais Dockerfile** (racine au lieu de `services/annotation-backend/Dockerfile`).

---

## 2. PREUVES CODE — Deux images Docker distinctes

### 2.1. Dockerfile RACINE → `main:app` → service `dms-api`

**Fichier** : `Dockerfile` (racine monorepo)  
**App uvicorn** : `main:app` (ligne 18 de `start.sh`)  
**Payload GET /health** :

```python
# src/api/app_factory.py:619
@app.get("/health")
def health_probe() -> dict[str, str]:
    return {"status": "ok", "service": "dms-api", "version": APP_VERSION}
```

**Endpoints disponibles** :

- GET `/` → UI HTML MVP DMS (DAO/RFQ/CBA/PV)
- GET `/health` → `{"status":"ok","service":"dms-api","version":"1.0.0"}`
- POST `/api/cases`, `/api/analyze`, `/api/decide`, etc.

**Aucun** `/predict` ni `/setup`.

---

### 2.2. Dockerfile ANNOTATION → `backend:app` → service `dms-annotation-backend`

**Fichier** : `services/annotation-backend/Dockerfile`  
**App uvicorn** : `backend:app` (ligne 62 de `services/annotation-backend/start.sh`)  
**Payload GET /health** :

```python
# services/annotation-backend/backend.py:1257-1270
def _health_payload() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "dms-annotation-backend",
        "schema": SCHEMA_VERSION,         # "v3.0.1d"
        "framework": FRAMEWORK_VERSION,   # "annotation-framework-v3.0.1d"
        "model": MISTRAL_MODEL,
        "mistral_configured": bool(MISTRAL_API_KEY),
        "strict_predict": STRICT_PREDICT,
        "pass_orchestrator_enabled": use_pass_orchestrator(),
        "m12_subpasses_enabled": use_m12_subpasses(),
        "orchestrator_runs_dir_hint": _runs_dir_health_hint(),
    }
```

**Payload GET /** :

```python
# services/annotation-backend/backend.py:1273-1281
@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "dms-annotation-backend",
        "health": "/health",
        "setup": "/setup",
        "predict": "/predict",
    }
```

**Endpoints disponibles** :

- GET `/` → JSON avec `"service":"dms-annotation-backend"` + liste endpoints
- GET `/health` → payload complet (schema, framework, model, flags M12)
- POST `/setup` → Label Studio ML backend handshake
- POST `/predict` → extraction structurée (DAO/offre → DMSAnnotation)

**Sanity check au boot** (ligne 9-12 de `start.sh`) :

```sh
if [ ! -f ./backend.py ]; then
  echo "[start.sh] ERROR: backend.py absent — ce conteneur n'est pas l'image annotation-backend." >&2
  exit 1
fi
```

---

## 3. PIPELINE DMS — Appel extraction

**Fichier client** : `src/couche_a/extraction/backend_client.py`

```python
# backend_client.py:34-55
async def call_annotation_backend(
    document_id: str,
    text: str,
    document_role: str,
) -> TDRExtractionResult:
    """Appel HTTP annotation-backend /predict."""
    r = _get_router()  # LLMRouter singleton
    async with httpx.AsyncClient(timeout=r.timeout) as client:
        response = await client.post(
            f"{r.backend_url}/predict",  # ← ENDPOINT CRITIQUE
            json=payload,
        )
        response.raise_for_status()
        raw = response.json()
    ...
```

**Routeur** : `src/couche_a/llm_router.py:70-113`

```python
class LLMRouter:
    def __init__(self) -> None:
        s = get_settings()
        self._backend_url = s.ANNOTATION_BACKEND_URL  # ← Variable config
        self._timeout = s.ANNOTATION_TIMEOUT
    
    @property
    def backend_url(self) -> str:
        return self._backend_url
```

**Variable d'environnement** : `src/core/config.py:106-107`

```python
ANNOTATION_BACKEND_URL: str = "http://localhost:8001"
ANNOTATION_TIMEOUT: int = 120
```

**Chemin attendu** : `{ANNOTATION_BACKEND_URL}/predict`  
→ Si Railway sert `dms-api` (pas de route `/predict`) : **404** → extraction échoue → pipeline bloqué.

---

## 4. CAUSES RAILWAY PLAUSIBLES — avec tests concrets


| Cause                                  | Symptôme                                                         | Test Railway                                                                                 | Test HTTP                                                    |
| -------------------------------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **Mauvais Dockerfile Path**            | Build racine au lieu de `services/annotation-backend/Dockerfile` | Settings → Dockerfile Path ≠ `services/annotation-backend/Dockerfile`                        | ✅ `GET /` renvoie HTML UI DMS (main:app)                     |
| **Root Directory erroné**              | Build context ne voit pas `services/`                            | Settings → Root Directory = `services/annotation-backend` au lieu de `.` (racine)            | ❌ Logs build : `COPY services/… → no such file`              |
| **Start Command override**             | Railway UI écrase `CMD ./start.sh` du Dockerfile                 | Settings → Start Command présent (ex. `uvicorn main:app…`)                                   | ✅ Logs runtime : `uvicorn main:app` au lieu de `backend:app` |
| **Domaine attaché au mauvais service** | Service "dms-api" déployé, mais domaine pointe vers lui          | Railway Dashboard : vérifier quel service a le domaine `annotation-backend-production-5513…` | ✅ Service ID ≠ nom service                                   |
| **Service dupliqué / legacy**          | Ancien service "annotation-backend" non mis à jour               | Railway Dashboard : plusieurs services nommés "annotation-*"                                 | N/A                                                          |
| **Image cache stale**                  | Redéploiement sans rebuild (ancien layer)                        | Logs build : Docker layer `CACHED` pour COPY scripts critiques                               | Manual redeploy → Rebuild without cache                      |


**Test HTTP effectué 2026-04-20 18:52 UTC** :

```bash
$ curl https://annotation-backend-production-5513.up.railway.app/health
{"status":"ok","service":"dms-api","version":"1.0.0"}  # ❌ dms-api

$ curl https://annotation-backend-production-5513.up.railway.app/
<!doctype html>  # ❌ UI HTML MVP (main:app)

$ curl https://annotation-backend-production-5513.up.railway.app/predict
{"detail":"Not Found"}  # ❌ 404

$ curl https://annotation-backend-production-5513.up.railway.app/setup
{"detail":"Not Found"}  # ❌ 404
```

**Verdict** : cause **1** confirmée (mauvais Dockerfile Path).

---

## 5. CHECKLIST VALIDATION — Preuves `dms-annotation-backend`

### 5.1. Champs JSON GET /health attendus


| Champ                         | Valeur attendue                     | Preuve image annotation           |
| ----------------------------- | ----------------------------------- | --------------------------------- |
| `"service"`                   | `"dms-annotation-backend"`          | ✅ Attend `dms-annotation-backend` |
| `"schema"`                    | `"v3.0.1d"` (ou version courante)   | ✅ Champ absent dans dms-api       |
| `"framework"`                 | `"annotation-framework-v3.0.1d"`    | ✅ Champ absent dans dms-api       |
| `"model"`                     | `"mistral-small-latest"` (ou autre) | ✅ Champ absent dans dms-api       |
| `"mistral_configured"`        | `true` / `false`                    | ✅ Champ absent dans dms-api       |
| `"pass_orchestrator_enabled"` | `true` / `false`                    | ✅ Champ absent dans dms-api       |
| `"m12_subpasses_enabled"`     | `true` / `false`                    | ✅ Champ absent dans dms-api       |


**Image dms-api** : seuls 3 champs `{"status","service","version"}`.

---

### 5.2. Champs JSON GET / attendus


| Champ       | Valeur                     | Preuve |
| ----------- | -------------------------- | ------ |
| `"service"` | `"dms-annotation-backend"` | ✅      |
| `"health"`  | `"/health"`                | ✅      |
| `"setup"`   | `"/setup"`                 | ✅      |
| `"predict"` | `"/predict"`               | ✅      |


**Image dms-api** : GET `/` renvoie **HTML** (UI MVP), pas JSON.

---

### 5.3. Endpoints HTTP critiques


| Endpoint        | Statut attendu | Charge utile                                   | Preuve annotation |
| --------------- | -------------- | ---------------------------------------------- | ----------------- |
| `POST /predict` | 200 ou 400/422 | JSON `{"tasks":[…]}`                           | ✅ Route existe    |
| `POST /setup`   | 200            | JSON `{"model_version":"…"}`                   | ✅ Route existe    |
| `GET /health`   | 200            | JSON avec 10+ champs                           | ✅                 |
| `GET /`         | 200            | JSON avec `"service":"dms-annotation-backend"` | ✅                 |


**Image dms-api** : `/predict` et `/setup` → **404**.

---

### 5.4. Logs runtime au boot

**Pattern attendu** (aligné sur `services/annotation-backend/start.sh` et `backend.py`) :

```
[start.sh] DMS annotation-backend — uvicorn backend:app — port=<PORT>
[start.sh] flags: ANNOTATION_USE_PASS_ORCHESTRATOR=… ANNOTATION_USE_M12_SUBPASSES=…
INFO:     Uvicorn running on http://0.0.0.0:<PORT> (Press CTRL+C to quit)
[BOOT] dms-annotation-backend — uvicorn backend:app ; LS healthcheck: GET /health
```

**Image dms-api** :

```
[start.sh] Starting uvicorn...
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

Pas de mention `backend:app` ni `[BOOT] dms-annotation-backend`.

---

## 6. RISQUE EXTRACTION PIPELINE


| Composant                       | Impact                                                                               | Gravité     |
| ------------------------------- | ------------------------------------------------------------------------------------ | ----------- |
| **Extraction DAO (critères)**   | `extract_dao_content()` **ne** passe **pas** par `/predict` (parsing local + persistance SQL). Impact Railway 404 : **négligeable** sur ce chemin. | 🟢 N/A ici |
| **Extraction offre (ML)**       | `extract_offer_content_async` → `call_annotation_backend` → `POST …/predict` : 404 ou erreurs réseau → fallback / Gate B → matrice souvent **bloquée** | 🔴 BLOQUANT |
| **Label Studio ML backend**     | `/setup` handshake échoue → LS ne peut pas charger le backend                        | 🔴 BLOQUANT |
| **Tests E2E**                   | Scripts qui ciblent l’annotation backend échouent (404) si URL pointe sur `dms-api` | 🟠 CRITIQUE |
| **TIER Mistral (routeur)**      | `MISTRAL_API_KEY` absente → T4 offline (distinct d’`ANNOTATION_BACKEND_URL`, mais dégradation cumul possible) | 🟡 DÉGRADÉ  |


**Conséquence immédiate** : tout chemin qui repose sur **`POST /predict`** (offres, pipeline V5 extraction bundle, LS) est **cassé** tant que Railway sert l’image **`dms-api`** sur cette URL — pas l’ingestion DAO critères en elle-même.

---

## 7. ACTIONS CORRECTIVES — Ordre de priorité

### 7.1. Vérifier configuration Railway service "annotation-backend"

1. **Settings → Dockerfile Path** : doit être `services/annotation-backend/Dockerfile`
2. **Settings → Root Directory** : doit être `.` (racine monorepo) ou **vide** (pas `services/annotation-backend`)
3. **Settings → Start Command** : doit être **vide** (utilise `CMD ./start.sh` du Dockerfile) ou exactement `./start.sh`

### 7.2. Redéployer sans cache

Railway Dashboard → service "annotation-backend" → **Redeploy** → cocher **"Rebuild without cache"**.

### 7.3. Validation post-déploiement

```bash
# 1. Health check identité
curl https://annotation-backend-production-5513.up.railway.app/health | jq .
# Attendu : {"status":"ok","service":"dms-annotation-backend","schema":"v3.0.1d",…}

# 2. Root endpoint
curl https://annotation-backend-production-5513.up.railway.app/ | jq .
# Attendu : {"service":"dms-annotation-backend","health":"/health","setup":"/setup","predict":"/predict"}

# 3. Predict endpoint accessible (422 si pas de payload = OK)
curl -X POST https://annotation-backend-production-5513.up.railway.app/predict
# Attendu : 422 ou 400 (pas 404)

# 4. Setup endpoint accessible
curl -X POST https://annotation-backend-production-5513.up.railway.app/setup
# Attendu : 200 JSON model_version (pas 404)
```

### 7.4. Test extraction pipeline

```bash
# Depuis repo local avec ANNOTATION_BACKEND_URL=https://annotation-backend-production-5513.up.railway.app
python scripts/smoke_m12_annotation.py
# Attendu : chemins ML /predict OK (pas 404) ; statuts annotation selon script (souvent offre / LS, pas DAO critères via /predict)
```

---

## 8. RÉFÉRENCE DOCUMENTATION

**README annotation-backend** : `services/annotation-backend/README.md:59-64`

> **Tableau dépannage** :
>
> - 404 sur `/health` → Image API DMS (`Dockerfile` racine, `main:app`) ou Start Command qui lance `main:app`.
> - Build OK mais mauvais runtime → Start Command UI Railway remplace `./start.sh`.
> - Logs sans `[BOOT] dms-annotation-backend` → Ce n'est pas `backend:app`.
>
> **Vérifications rapides** : `…/` → JSON avec `"service":"dms-annotation-backend"` ; `…/health` → 200 JSON. Logs : ligne `DMS annotation-backend — uvicorn backend:app`.

**Freeze annotation-backend** : `.cursor/rules/dms-annotation-backend-freeze.mdc`

> Exception explicite : service déployable séparé (`services/annotation-backend/`).

---

## 9. CONCLUSION

Railway service "annotation-backend" **sert l'image dms-api (Dockerfile racine)** au lieu de `dms-annotation-backend` (services/annotation-backend/).  
**Tous les endpoints critiques** (`/predict`, `/setup`) **renvoient 404**.  
**Chemins dépendants de `POST /predict` et LS `/setup`** (offres, pipeline V5 bundles, ML backend) **bloqués** jusqu'à correction Railway (Dockerfile Path + redéploiement). L’ingestion DAO critères via `extract_dao_content` reste **hors** de ce flux HTTP.

**Priorité** : 🔴 **BLOQUANT PROD** — corriger immédiatement.