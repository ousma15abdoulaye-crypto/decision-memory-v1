# W4 — Worker Railway DMS : Runbook opérationnel

**Autorité** : CTO principal DMS (décision gate W3-bis PASS PARTIEL 2026-04-23)  
**Auteur** : Agent Claude Code (mandat DMS-W4-EMISSION-POST-W3BIS-PASS-PARTIEL-2026-04-22)  
**Date** : 2026-04-23  
**Statut** : ✅ OPPOSABLE — Runbook production

---

## 1. Identité du service

### Service Railway

**Nom service** : `dms-db-worker`  
**URL publique** : `https://dms-db-worker-production.up.railway.app`  
**Projet Railway** : DMS  
**Build** : Nixpacks (Python 3.11)

### Référence code source

**Repository** : `decision-memory-v1`  
**Branche déploiement** : `chore/p3-4-infra-stabilization`  
**Commit référence code** : `8bda421f` — fix(worker): add public /healthz endpoint for Railway healthcheck  
**Répertoire source** : `services/worker-railway/`

**Fichiers principaux** :
- `main.py` : Application FastAPI (endpoints, auth, logging)
- `requirements.txt` : Dépendances Python
- `railway.json` : Configuration Railway (build, deploy, healthcheck)
- `.env.example` : Template variables (documentation uniquement, non déployé)

### Spécification technique

**Référence design** : `decisions/worker/W1_worker_railway_spec.md`  
**Validation POC** : `decisions/worker/W2_worker_railway_poc.md`  
**Test stabilité** : `decisions/worker/W3_bis_worker_railway_stability_50min.md` (PASS PARTIEL)

---

## 2. Démarrage / arrêt / redéploiement

### Redéploiement automatique

**Trigger** : Push sur branche `chore/p3-4-infra-stabilization`

Railway détecte automatiquement les commits et redéploie le service si modifications dans `services/worker-railway/` ou `railway.toml`.

**Procédure** :
```bash
# 1. Modifier code dans services/worker-railway/
# 2. Commit et push
git add services/worker-railway/
git commit -m "fix(worker): description"
git push origin chore/p3-4-infra-stabilization

# 3. Railway redéploie automatiquement (build + restart)
# 4. Vérifier déploiement dans Railway dashboard
```

**Durée build** : ~2-3 min (Nixpacks + dependencies)  
**Durée total déploiement** : ~3-5 min

### Redéploiement manuel

**Via Railway CLI** :
```bash
railway redeploy --service dms-db-worker
```

**Via Railway dashboard** :
1. Accéder projet DMS > service `dms-db-worker`
2. Onglet "Deployments"
3. Cliquer "Redeploy" sur dernier déploiement réussi

### Arrêt d'urgence

**Via Railway dashboard** :
1. Service `dms-db-worker` > Settings
2. Section "Danger Zone"
3. "Pause Service" (arrête conteneur, conserve configuration)

⚠️ **Impact** : Endpoints publics deviennent inaccessibles immédiatement (HTTP 503).

**Via Railway CLI** :
```bash
# Pas de commande CLI directe pour pause
# Utiliser dashboard obligatoirement
```

### Redémarrage

**Via Railway dashboard** :
1. Service `dms-db-worker` > Settings
2. "Resume Service" (si pausé) OU cliquer "Restart" dans Deployments

**Via Railway CLI** :
```bash
railway restart --service dms-db-worker
```

**Durée redémarrage** : ~30-60 secondes (pas de rebuild)

---

## 3. Variables d'environnement

### Variables obligatoires

| Variable              | Source                  | Usage                                    |
|-----------------------|-------------------------|------------------------------------------|
| `DATABASE_URL`        | Service link Railway    | Connexion PostgreSQL interne Railway    |
| `WORKER_AUTH_TOKEN`   | Configuration manuelle  | Bearer token authentification endpoints |
| `PORT`                | Railway auto-injection  | Port écoute uvicorn (défaut: 8080)      |
| `LOG_LEVEL`           | Configuration manuelle  | Niveau logs Python (INFO/DEBUG/WARNING) |

### Configuration actuelle

**DATABASE_URL** :
- **Source** : Service link Railway (PostgreSQL → dms-db-worker)
- **Format** : `postgresql://postgres:[PASSWORD]@postgres.railway.internal:5432/railway`
- **Injection** : Automatique (Railway configure lors du service link)
- **Modification** : Via Railway dashboard uniquement (Service Link section)

**WORKER_AUTH_TOKEN** :
- **Source** : Manuelle (Railway dashboard Variables)
- **Format** : UUID v4 sans chevrons (36 caractères)
- **Valeur actuelle** : `[REDACTED — voir Railway dashboard]`
- **Usage** : Header `Authorization: Bearer <token>` pour tous endpoints sauf `/healthz`

**PORT** :
- **Source** : Railway auto-injection
- **Valeur** : `8080` (Railway assigne automatiquement)
- **Modification** : Non nécessaire (Railway gère)

**LOG_LEVEL** :
- **Source** : Configuration manuelle (optionnel)
- **Valeurs** : `DEBUG`, `INFO` (défaut), `WARNING`, `ERROR`
- **Modification** : Railway dashboard Variables

### Procédure rotation WORKER_AUTH_TOKEN

**Fréquence recommandée** : Tous les 90 jours ou après exposition suspectée.

**Procédure** :
1. Générer nouveau token :
   ```bash
   openssl rand -hex 18 | xxd -r -p | base64 | tr -d '=' | tr '+/' '-_' | cut -c1-32
   # OU utiliser UUID v4
   # Vérifier longueur 32-36 caractères, pas de chevrons
   ```

2. Mettre à jour Railway :
   - Dashboard > Service `dms-db-worker` > Variables
   - Éditer `WORKER_AUTH_TOKEN`
   - Coller nouveau token (SANS chevrons `<>`)
   - Sauvegarder

3. Railway redémarre automatiquement le worker (~30s)

4. Mettre à jour clients/scripts utilisant le worker (si applicable)

5. Tester endpoint avec nouveau token :
   ```bash
   curl -H "Authorization: Bearer <NEW_TOKEN>" \
     https://dms-db-worker-production.up.railway.app/health
   # Attendu: {"status":"ok","db":"reachable",...}
   ```

### Règles de sécurité

❌ **INTERDIT** :
- Commiter `WORKER_AUTH_TOKEN` en clair dans code ou documentation
- Afficher token dans logs applicatifs (main.py masque automatiquement)
- Copier-coller token avec chevrons `<>` (erreur auth 100%)

✅ **OBLIGATOIRE** :
- Token stocké uniquement dans Railway Variables
- Transmission via canaux sécurisés (pas email/Slack en clair)
- Rotation immédiate si exposition détectée

---

## 4. Surveillance et santé

### Endpoints de santé

#### `/healthz` — Healthcheck public Railway

**Usage** : Healthcheck automatique Railway (toutes les 30s)

**Requête** :
```bash
curl https://dms-db-worker-production.up.railway.app/healthz
```

**Réponse normale** :
```json
{
  "status": "ok",
  "timestamp": "2026-04-23T15:30:00.123456+00:00"
}
```
HTTP 200

**Authentification** : Aucune (public)

**Interprétation** :
- ✅ HTTP 200 : Worker uvicorn répond
- ❌ HTTP 503/timeout : Worker down ou Railway réseau coupé

⚠️ **Note** : `/healthz` ne teste PAS la DB PostgreSQL (healthcheck léger).

#### `/health` — Healthcheck complet avec DB

**Usage** : Vérification opérationnelle complète (worker + DB)

**Requête** :
```bash
curl -H "Authorization: Bearer <WORKER_AUTH_TOKEN>" \
  https://dms-db-worker-production.up.railway.app/health
```

**Réponse normale** :
```json
{
  "status": "ok",
  "db": "reachable",
  "timestamp": "2026-04-23T15:30:00.123456+00:00"
}
```
HTTP 200

**Réponse dégradée** :
```json
{
  "status": "degraded",
  "db": "unreachable",
  "error": "connection timeout...",
  "timestamp": "2026-04-23T15:30:00.123456+00:00"
}
```
HTTP 503

**Authentification** : Bearer token obligatoire

**Interprétation** :
- ✅ `"db": "reachable"` : Worker → PostgreSQL OK
- ❌ `"db": "unreachable"` : Problème connexion DB (voir §5)

#### `/db/ping` — Latence DB

**Usage** : Mesure latence PostgreSQL interne

**Requête** :
```bash
curl -H "Authorization: Bearer <WORKER_AUTH_TOKEN>" \
  https://dms-db-worker-production.up.railway.app/db/ping
```

**Réponse normale** :
```json
{
  "ok": 1,
  "server_time": "2026-04-23T15:30:00.123456+00:00",
  "latency_ms": 52.18
}
```
HTTP 200

**Seuils indicatifs** :
- ✅ **Normal** : `latency_ms` < 100 ms
- ⚠️ **Dégradé** : `latency_ms` 100-300 ms
- ❌ **Critique** : `latency_ms` > 300 ms

**Interprétation** : `latency_ms` mesure uniquement worker → PostgreSQL (réseau interne Railway), pas client → worker.

### Logs Railway

#### Accès logs

**Via Railway dashboard** :
1. Service `dms-db-worker` > Deployments
2. Cliquer déploiement actif
3. Section "Logs" (temps réel)

**Via Railway CLI** :
```bash
# Logs récents (100 dernières lignes)
railway logs --service dms-db-worker

# Logs temps réel (non supporté toutes versions CLI)
# Utiliser dashboard si erreur CLI
```

#### Format logs

**Logs structurés JSON** (stdout) :
```json
{
  "timestamp": "2026-04-23T15:30:00.123456+00:00",
  "level": "INFO",
  "message": "GET /db/ping",
  "endpoint": "/db/ping",
  "status_code": 200,
  "latency_ms": 52.18
}
```

**Logs uvicorn** (startup/shutdown) :
```
INFO:     Started server process [1]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

#### Filtres recommandés

**Erreurs critiques** :
```bash
# Dans logs Railway, chercher:
"level": "ERROR"
"status_code": 503
"status_code": 500
"db": "unreachable"
```

**Performance dégradée** :
```bash
# Latence > 300ms
"latency_ms": [3-9][0-9]{2,}
```

**Auth failures** :
```bash
"status_code": 401
"Invalid authentication"
```

### Signaux de santé

#### Signaux sains ✅

- Healthcheck Railway `/healthz` HTTP 200 stable
- `/health` retourne `"db": "reachable"` (> 95% succès)
- Latence `/db/ping` médiane < 100 ms
- Logs structurés JSON bien formés
- Aucun ERROR level dans logs (0-2 par jour acceptable si résolu)

#### Signaux d'alerte ⚠️

- Latence `/db/ping` p95 > 150 ms (investigation recommandée)
- `/health` retourne `"db": "unreachable"` sporadiquement (< 5% requests)
- Logs contiennent reconnexions PostgreSQL
- Taux 401 > 1% (possible rotation token non synchronisée)

#### Signaux critiques ❌

- Healthcheck Railway DOWN > 2 min (worker crash ou Railway outage)
- `/health` retourne HTTP 503 de façon soutenue (> 10% requests)
- Logs montrent `psycopg.OperationalError` récurrents
- Aucun log depuis > 5 min (processus frozen)

---

## 5. Diagnostic incidents

### Symptôme A — `/health` retourne 503 `db: unreachable`

**Hypothèses** :
1. PostgreSQL Railway service DOWN
2. Service link Railway cassé (DATABASE_URL invalide)
3. Credentials PostgreSQL expirés/changés
4. Réseau interne Railway dégradé

**Actions de diagnostic** :

1. Vérifier statut PostgreSQL Railway :
   ```bash
   railway status
   # Chercher service PostgreSQL, vérifier "healthy"
   ```

2. Vérifier service link :
   - Dashboard Railway > Service `dms-db-worker` > Settings
   - Section "Service Link" : doit pointer vers PostgreSQL
   - Si absent : recréer service link

3. Tester connexion DB directe (via tunnel Railway CLI) :
   ```bash
   railway connect postgres
   # Si échec : problème PostgreSQL ou credentials
   ```

4. Vérifier `DATABASE_URL` injecté :
   ```bash
   railway variables --service dms-db-worker | grep DATABASE_URL
   # Doit contenir: postgresql://postgres:...@postgres.railway.internal:5432/railway
   ```

5. Consulter logs PostgreSQL Railway :
   - Dashboard Railway > Service PostgreSQL > Logs
   - Chercher erreurs connexion/auth

**Escalade** : Si PostgreSQL Railway healthy mais worker inaccessible → support Railway (incident plateforme).

---

### Symptôme B — `/db/ping` latence dégradée (> 300ms soutenu)

**Hypothèses** :
1. Charge PostgreSQL élevée (queries longues autres services)
2. Réseau interne Railway congestionné
3. Worker CPU throttled (limite Railway atteinte)

**Actions de diagnostic** :

1. Vérifier charge PostgreSQL :
   ```bash
   railway connect postgres
   # Puis:
   SELECT count(*) FROM pg_stat_activity WHERE state = 'active';
   # Si > 10 connexions actives : charge élevée
   ```

2. Vérifier métriques worker Railway :
   - Dashboard > Service `dms-db-worker` > Metrics
   - CPU usage : si > 80% soutenu → scaling requis
   - Memory : si > 400MB → possible leak (redémarrage)

3. Comparer latence endpoints :
   - `/db/ping` vs `/db/info` : si similaire → problème DB
   - Si `/db/ping` seul lent → problème query spécifique

4. Tester depuis autre client :
   - Curl depuis machine différente
   - Si latence normale ailleurs → problème réseau local opérateur

**Escalade** : Si latence interne Railway > 300ms et PostgreSQL charge normale → ticket support Railway.

---

### Symptôme C — Service Railway DOWN (healthcheck fail > 2 min)

**Hypothèses** :
1. Worker crash au startup (erreur code Python)
2. Build Railway échoué (dépendances manquantes)
3. Railway platform outage
4. Port conflict (rare)

**Actions de diagnostic** :

1. Vérifier dernier déploiement :
   - Dashboard > Service `dms-db-worker` > Deployments
   - Status dernier deploy : "Failed" ou "Crashed" ?
   - Consulter logs build + runtime

2. Identifier erreur startup :
   ```bash
   railway logs --service dms-db-worker | grep -i "error\|failed\|traceback"
   ```

   **Erreurs courantes** :
   - `ValueError: DATABASE_URL environment variable is required` → service link cassé
   - `ValueError: WORKER_AUTH_TOKEN environment variable is required` → variable manquante
   - `ModuleNotFoundError` → `requirements.txt` désynchronisé

3. Vérifier Railway status page :
   - https://status.railway.app
   - Si incident plateforme déclaré → attendre résolution Railway

4. Redémarrer service :
   ```bash
   railway restart --service dms-db-worker
   ```

5. Si échec persist, redéployer commit stable connu :
   ```bash
   git checkout 8bda421f  # Commit référence stable W2
   git push origin chore/p3-4-infra-stabilization --force
   # Railway redéploie version stable
   ```

**Escalade** : Si restart + redeploy stable échouent → support Railway + CTO principal DMS.

---

### Symptôme D — 401 Unauthorized inattendus

**Hypothèses** :
1. `WORKER_AUTH_TOKEN` mismatch (client utilise ancien token)
2. Token Railway contient chevrons `<>` (erreur config)
3. Header `Authorization` malformé (typo `Bearer`)

**Actions de diagnostic** :

1. Vérifier format token Railway :
   ```bash
   railway variables --service dms-db-worker | grep WORKER_AUTH_TOKEN
   # Longueur doit être 32-36 caractères
   # AUCUN chevron <>
   ```

2. Tester avec token Railway actuel :
   ```bash
   # Récupérer token depuis Railway dashboard (copier exact)
   TOKEN="<copier depuis Railway Variables>"
   curl -H "Authorization: Bearer $TOKEN" \
     https://dms-db-worker-production.up.railway.app/health
   ```

3. Vérifier logs worker :
   ```bash
   railway logs --service dms-db-worker | grep "401"
   # Logs structurés montrent endpoint + status_code
   ```

4. Si token Railway a chevrons `<...>` :
   - Éditer variable Railway
   - Supprimer chevrons (garder seulement UUID)
   - Redémarrer worker

5. Si token client différent token Railway :
   - Mettre à jour client avec token actuel Railway
   - OU régénérer token (voir §3 Rotation)

**Escalade** : Si 401 persistent avec token vérifié correct → CTO principal DMS (bug auth worker).

---

### Symptôme E — Redéploiement échoué

**Hypothèses** :
1. Build Nixpacks erreur (dependencies Python)
2. Tests startup échouent (`DATABASE_URL` inaccessible au build)
3. Réseau Railway timeout
4. Ressources Railway insuffisantes

**Actions de diagnostic** :

1. Consulter logs build Railway :
   - Dashboard > Deployments > Deploy échoué > "Build Logs"
   - Identifier étape échec (setup / install / start)

2. **Erreur install dependencies** :
   ```
   ERROR: Could not find a version that satisfies the requirement...
   ```
   → Vérifier `requirements.txt` pinned versions
   → Tester build local :
   ```bash
   cd services/worker-railway
   python -m venv .venv
   .venv/Scripts/activate
   pip install -r requirements.txt
   # Si échec local : corriger requirements.txt
   ```

3. **Erreur startup DB connection** :
   ```
   ERROR: DB connection test FAILED on startup
   ```
   → Causé par healthcheck Railway qui teste `/health` avant DB ready
   → Non bloquant si endpoint `/healthz` existe (résolu commit `8bda421f`)
   → Si `/healthz` manquant : vérifier code main.py ligne ~100

4. **Timeout build** :
   → Réessayer déploiement (flake Railway)
   → Si récurrent : augmenter `healthcheckTimeout` dans `railway.json`

5. Rollback version stable :
   ```bash
   git revert <commit-problematique>
   git push origin chore/p3-4-infra-stabilization
   ```

**Escalade** : Si build échoue sur commit stable précédemment déployé → support Railway (régression plateforme).

---

## 6. Dette résiduelle connue (W3-bis)

### Positionnement

**Référence décision** : CTO principal DMS — décision gate W3-bis PASS PARTIEL (2026-04-23)  
**Commit décision** : `6e7fe546` — fix(W3-bis): reclassify verdict as PASS PARTIEL

### Dette actée

**Nature** : Protocole test stabilité W3-bis incomplet (83/100 pings exécutés au lieu de 100).

**Statut** : **Non bloquante pour production** — Stabilité worker validée sur 50 min continues, 83/83 HTTP 200, aucune déconnexion, aucun timeout DB.

**Contexte** :
- W3-bis a démontré stabilité worker Railway sur 50 min continues
- Taux succès 100% observé (83/83 requêtes)
- Latence DB interne normale (~52ms)
- Protocole incomplet dû à latence réseau local test (artifact Windows → Railway HTTPS, non représentatif du worker)

**Classification CTO** :
> "W3-bis PASS PARTIEL est jugé suffisant pour lever le blocage infra. Stabilité fortement corroborée. Le caractère incomplet du protocole (83/100 pings) est conservé comme dette de preuve résiduelle, non bloquante."

### Implications opérationnelles

**Usage production** : Aucune restriction. Worker validé pour sessions annotation longues 45+ min.

**Re-test futur** :
- **Non requis immédiatement** (décision CTO principal)
- Considérer W3-ter (100/100 pings) uniquement si :
  1. Symptôme nouveau apparaît (déconnexions récurrentes production)
  2. Exigence formelle émise (audit/compliance)

**Monitoring prioritaire** :
- Surveiller uptime worker > 45 min en production réelle
- Logger tout timeout DB ou déconnexion (aucun attendu)
- Si symptôme détecté → ouvrir investigation dédiée (pas automatiquement W3-ter)

### Documentation complète

**Rapports complets** :
- `decisions/worker/W3_worker_railway_stability_45min.md` — W3 run 1 INCONCLUSIF
- `decisions/worker/W3_bis_worker_railway_stability_50min.md` — W3-bis PASS PARTIEL

---

## 7. Contacts et escalade

### Propriétaires

**Propriétaire technique** : CTO principal DMS  
**Conception & POC** : Agent Claude Code (mandats W1/W2/W3/W3-bis/W4)

### Escalade incidents

**Niveau 1 — Opérateur** :
- Appliquer diagnostic §5 selon symptôme
- Consulter logs Railway + runbook
- Redémarrage service si applicable

**Niveau 2 — CTO principal DMS** :
- Symptôme non résolu après diagnostic §5
- Modification code/config worker requise
- Décision rollback version stable
- Rotation credentials d'urgence

**Niveau 3 — Support Railway** :
- Railway platform outage confirmé (status.railway.app)
- PostgreSQL Railway DOWN sans cause identifiée
- Build échoue sur commit stable (régression plateforme)
- Latence réseau interne Railway > 300ms soutenue

### Références mandats

**Architecture & décision** :
- ADR Option C : `decisions/p34_infra_stabilization_opening_preflight.md` (Phase 1 synthesis)
- Mandat W1 : `decisions/worker/W1_worker_railway_spec.md`
- Mandat W2 : `decisions/worker/W2_worker_railway_poc.md`
- Mandat W3-bis : `decisions/worker/W3_bis_worker_railway_stability_50min.md`
- Mandat W4 : Ce document

**Chantier parent** : P3.4-INFRA-STABILIZATION  
**Branche** : `chore/p3-4-infra-stabilization`

### Canaux communication

**Synchrone** : Session Agent Claude Code (terminal)  
**Asynchrone** : Commits + PR GitHub `decision-memory-v1`  
**Urgence** : CTO principal DMS (escalade directe)

---

## Changelog

| Date       | Version | Auteur       | Changement                               |
|------------|---------|--------------|------------------------------------------|
| 2026-04-23 | 1.0.0   | Agent W4     | Création runbook initial (mandat W4)     |

---

**Statut** : ✅ OPPOSABLE — Runbook production worker Railway DMS  
**Dernière révision** : 2026-04-23  
**Prochaine révision** : À besoin (symptôme nouveau ou évolution architecture)
