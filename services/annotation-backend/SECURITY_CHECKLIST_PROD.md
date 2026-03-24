# Checklist sécurité — annotation-backend (production)

Avant go-live ou après changement d’infra, cocher.

## Secrets et configuration

- [ ] **`MISTRAL_API_KEY`** défini — jamais dans le dépôt ni dans les logs applicatifs.
- [ ] **`PSEUDONYM_SALT`** défini et identique à la politique DMS (ADR-013) — rotation = impact sur corrélation historique.
- [ ] **`LABEL_STUDIO_URL`** / **`LABEL_STUDIO_API_KEY`** (ou `LS_URL` / `LS_API_KEY`) — token LS avec périmètre minimal.
- [ ] **`WEBHOOK_CORPUS_SECRET`** défini **et** même valeur configurée côté Label Studio (header `X-Webhook-Secret`) — sinon tout appelant peut déclencher le webhook.
- [ ] **`CORPUS_SINK=s3`** + **`S3_*`** : clés R2/API S3 sans espaces / guillemets parasites ; endpoint sans `/` final.

## Réseau et surface d’attaque

- [ ] **`CORS_ORIGINS`** : origines explicites (URL Label Studio + front autorisés) — **pas** `*` en production.
- [ ] Load balancer / TLS terminé côté plateforme (Railway) — pas d’HTTP clair vers Internet pour les secrets.

## Logs et observabilité

- [ ] Vérifier qu’aucun log n’affiche : clés API, `S3_SECRET_ACCESS_KEY`, `WEBHOOK_CORPUS_SECRET`, corps complet des requêtes sensibles.
- [ ] Les logs `[BOOT][CORPUS]` n’exposent que schéma + hôte endpoint (pas de credentials) — comportement actuel [`corpus_sink.py`](corpus_sink.py).

## Webhook

- [ ] `POST /webhook` : si secret configuré, tester un appel **sans** header → **401**.
- [ ] `CORPUS_WEBHOOK_ENABLED` aligné avec l’intention (désactiver si pas de sink pour éviter erreurs bruyantes).

## Santé

- [ ] `GET /health` accessible pour probes — ne doit pas exposer secrets (comportement actuel : statut service).

## Documentation

- [ ] Variables complètes : [`ENVIRONMENT.md`](ENVIRONMENT.md).
