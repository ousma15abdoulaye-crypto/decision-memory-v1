# Runbook — secrets et rotation (DMS)

## 1. JWT / signature des tokens (API principale)

| Variable | Rôle |
|----------|------|
| **`SECRET_KEY`** | **Primaire** — secret HMAC pour JWT (HS256). **Obligatoire** en production. |
| **`JWT_SECRET`** | **Repli** — lu seulement si `SECRET_KEY` est absent ([`jwt_handler._secret_key`](../src/couche_a/auth/jwt_handler.py)). |

**Règle prod** : définir **uniquement `SECRET_KEY`** (ou les deux avec la **même** valeur) pour éviter toute ambiguïté.

**Rotation** :

1. Générer une nouvelle clé (ex. `openssl rand -hex 32`).
2. Déployer `SECRET_KEY` sur tous les workers / instances.
3. **Effet** : tous les access tokens encore valides émis avec l’ancienne clé deviennent invalides au prochain déploiement (downtime auth bref acceptable) **ou** procéder par fenêtre double-clé si vous implémentez la rotation JWK (non présente dans le repo actuel).

**Où** : Railway / variables d’environnement du service API — jamais dans le dépôt Git.

---

## 2. Base de données

| Variable | Rôle |
|----------|------|
| `DATABASE_URL` | Connexion PostgreSQL (format `postgresql+psycopg://` ou `postgresql://` selon couche). |

**Rotation** : modifier le mot de passe côté hébergeur, mettre à jour `DATABASE_URL`, redémarrer l’application. Prévoir migration sans couper les connexions longues (pool).

---

## 3. Redis (rate limiting)

| Variable | Rôle |
|----------|------|
| `REDIS_URL` | Backend slowapi partagé entre workers — recommandé en prod ([`src/ratelimit.py`](../src/ratelimit.py)). |

**Rotation** : régénérer credentials Redis, mettre à jour `REDIS_URL`, redémarrer. Impact : compteurs de rate limit repartent à zéro (acceptable).

---

## 4. Label Studio + annotation-backend

| Variable | Rôle |
|----------|------|
| `LABEL_STUDIO_API_KEY` / `LS_API_KEY` | Token API LS |
| `MISTRAL_API_KEY` | Appels LLM |
| `WEBHOOK_CORPUS_SECRET` | Si défini, header `X-Webhook-Secret` obligatoire sur `POST /webhook` |
| `PSEUDONYM_SALT` | HMAC pseudonymisation — **ne pas changer** sans invalider les exports historiques (voir ADR-013) |

**Rotation LS / Mistral** : régénérer dans les dashboards respectifs, mettre à jour les variables Railway, redémarrer le service annotation-backend.

---

## 5. Cloudflare R2 / S3 (corpus annotations)

| Variable | Rôle |
|----------|------|
| `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` | (ou préfixe `AWS_*`) clés API R2 |
| `S3_ENDPOINT` | Endpoint `https://<account>.r2.cloudflarestorage.com` sans slash final |

**Rotation** : créer une nouvelle paire de clés R2, mettre à jour les variables, redémarrer ; révoquer l’ancienne paire après validation (`PutObject` / lecture test).

**Bonnes pratiques** : pas de guillemets ni retour ligne dans les champs Railway ; pas de log des secrets (les logs corpus n’affichent que l’hôte endpoint).

---

## 6. Fichiers locaux développement

- `.env` / `.env.local` : **gitignored** — ne jamais committer.
- CI GitHub : secrets dans **Repository secrets**, pas en clair dans les workflows.
