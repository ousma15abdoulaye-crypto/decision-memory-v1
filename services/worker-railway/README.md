# DMS Worker Railway

Worker FastAPI minimal pour accès PostgreSQL Railway depuis réseau interne Railway.

## Spec

Voir `decisions/worker/W1_worker_railway_spec.md`

## Setup local

1. Créer environnement virtuel :
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # ou
   .venv\Scripts\activate  # Windows
   ```

2. Installer dépendances :
   ```bash
   pip install -r requirements.txt
   ```

3. Configurer `.env` :
   ```bash
   cp .env.example .env
   # Éditer .env avec vraies valeurs (DATABASE_URL, WORKER_AUTH_TOKEN)
   ```

4. Lancer worker local :
   ```bash
   python main.py
   # ou
   uvicorn main:app --reload --port 8000
   ```

## Endpoints

Tous les endpoints nécessitent authentification bearer token :
```bash
curl -H "Authorization: Bearer <WORKER_AUTH_TOKEN>" http://localhost:8000/health
```

### GET /health
Health check worker + DB reachability.

### GET /db/ping
Execute SELECT 1 + server timestamp, retourne latence.

### GET /db/info
Informations PostgreSQL (version, taille DB).

## Déploiement Railway

1. Créer service Railway :
   ```bash
   railway service create dms-db-worker
   ```

2. Lier à PostgreSQL existant (service link Railway dashboard)

3. Configurer env vars Railway :
   - `WORKER_AUTH_TOKEN` : générer via `openssl rand -hex 32`
   - `DATABASE_URL` : auto-injecté par service link

4. Déployer :
   ```bash
   railway up
   ```

5. Vérifier :
   ```bash
   curl -H "Authorization: Bearer <TOKEN>" https://dms-db-worker.railway.app/health
   ```

## Logs

Logs structurés JSON stdout, visible dans Railway dashboard.

## Troubleshooting

### DB unreachable
- Vérifier service link Railway configuré
- Vérifier DATABASE_URL injecté (Railway env vars)
- Vérifier PostgreSQL service UP

### 401 Unauthorized
- Vérifier header `Authorization: Bearer <token>`
- Vérifier WORKER_AUTH_TOKEN configuré et identique client/serveur
