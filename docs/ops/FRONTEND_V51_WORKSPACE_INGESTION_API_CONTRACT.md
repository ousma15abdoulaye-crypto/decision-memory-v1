# Contrat API — ingestion workspace (frontend-v51)

Référence d’implémentation pour le corridor **ZIP → bundles → run-pipeline** branché sur l’UI workspace.

## Endpoints

| Endpoint | Méthode | Corps / query | Réponse succès | Erreurs typiques | UX attendue |
|----------|---------|---------------|----------------|------------------|-------------|
| `/api/workspaces/{id}/upload-zip` | POST | `multipart/form-data`, champ fichier nommé **`file`**, extension `.zip` | `{"workspace_id":"<uuid>","status":"accepted","message":"Pass -1 démarré…"}` | **422** si non-zip ; **403** si permission `bundle.upload` absente | HTTP 200 **ne signifie pas** Pass -1 terminé : traitement **async** (ARQ). Rafraîchir bundles / état cognitif. **UI** : l’utilisateur peut envoyer un **dossier** ; le frontend construit un `.zip` **dans le navigateur** (`fflate`) avant d’appeler cet endpoint. Attention : la limite mémoire côté client reste d’environ **400 Mo**, mais l’archive envoyée reste aussi soumise à la **limite serveur de 100 MB sur le ZIP** ; des dossiers PDF/JPG peu compressibles peuvent donc ne pas passer même si la compression côté navigateur réussit. |
| `/api/workspaces/{id}/bundles` | GET | — | `{"workspace_id":"<uuid>","bundles":[{…}]}` (tableau d’objets bundle) | **403** accès workspace | Liste vide = normal tant que Pass -1 n’a pas produit de lignes `supplier_bundles`. |
| `/api/workspaces/{id}/run-pipeline` | POST | Query `force_m14` bool (défaut false) | `PipelineV5Result` (JSON) : `completed`, `error`, étapes, `duration_seconds` | **403** ; erreurs métier dans `error` ou `completed: false` | Requête **HTTP synchrone** : durée potentiellement longue → risque **timeout** proxy / LB / navigateur en prod. Vérifier plafonds Railway/nginx. Si blocage, mandat backend « job async + poll ». |

## Auth

Toutes les routes exigent `Authorization: Bearer <access_token>` (aligné sur `lib/api-client.ts`).

## Déploiement

- Build frontend : `NEXT_PUBLIC_API_URL` = URL publique HTTPS de l’API.
- API : `CORS_ORIGINS` doit inclure l’origine exacte du frontend.

## PR / CI

- Vérifier `npm run lint` et `npx tsc --noEmit` dans `frontend-v51`.
- Les E2E Playwright sont exécutés dans la CI (`npx playwright install --with-deps chromium` dans `.github/workflows/dms_invariants_v51.yml`). En local, `npx playwright install` peut échouer derrière un proxy TLS ; la CI reste la référence.
