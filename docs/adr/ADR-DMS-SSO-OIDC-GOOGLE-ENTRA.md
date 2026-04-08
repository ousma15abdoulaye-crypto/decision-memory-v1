# ADR-DMS-SSO-OIDC — Authentification fédérée (Google Workspace + Microsoft Entra ID)

**Statut :** Proposé (cadrage — implémentation soumise à mandat CTO dédié)  
**Date :** 2026-04-08  
**Périmètre :** DMS API (`main.py`) + `frontend-v51`  
**Prérequis :** Login JSON `POST /auth/login` aligné (email/username + JWT DMS)

---

## Contexte

- Le DMS émet des **JWT métier** (`create_access_token`) avec `role`, `tenant_id`, `jti`, compatible **RLS** PostgreSQL.
- Un **compte fournisseur** (Google, Microsoft) ne remplace pas ce JWT : l’API doit **vérifier** le jeton OIDC puis **créer ou lier** un enregistrement `users` / `user_tenants` et **émettre le même type d’access_token** qu’après `/auth/login`.
- SCI peut standardiser sur **Google Workspace** et/ou **Microsoft 365 (Entra ID)** selon l’organisation.

## Décision

1. **Flux recommandé** : **OAuth2 / OIDC médiané par le backend** (redirection `authorize` → callback → émission JWT DMS), pas seulement une session Next.js isolée sans lien DB.
2. **Fournisseurs cibles** : **Google** et **Microsoft Entra ID** (deux clients OAuth distincts, secrets Railway / variables déploiement).
3. **Provisioning** : à trancher produit entre :
   - **JIT** : première connexion OIDC crée `users` + `user_tenants` (email vérifié par l’IdP) ;
   - **Invitation** : l’email OIDC doit exister en base (sinon 403 + message métier).
4. **Mapping rôle / tenant** : claims IdP (ex. `groups`, custom claims) ou table de **règles** (email domaine → tenant) — **pas** de confiance au rôle annoncé par le client sans validation serveur.
5. **Secrets** : `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `OAUTH_REDIRECT_BASE_URL` (origine publique de l’API ou du front selon design final), scopes `openid email profile`.

## Conséquences

- Nouvelle surface d’attaque : endpoints callback ; obligation de **state PKCE** / **nonce** selon le flux, validation stricte **`aud` / `iss`** sur `id_token`.
- **Données personnelles** : journalisation minimale ; alignement politique SCI sur rétention logs OAuth.
- **Pas de régression** : `/auth/login` et `/auth/token` restent disponibles pour comptes locaux et scripts.

---

## Phases d’implémentation (mandat futur — hors ce ADR)

Ces livrables constituent le todo **sso-impl-followup** ; chaque phase peut être un PR distinct.

| Phase | Contenu |
|-------|---------|
| **P1 Schéma** | Table `oauth_accounts` (`provider`, `provider_subject`, `user_id`, contrainte unique) si liaison multi-fournisseur requise. |
| **P2 API** | `GET /auth/oauth/{google\|microsoft}/start`, `GET /auth/oauth/{provider}/callback` ; échange code ; validation JWT IdP (lib dédiée ou `httpx` + JWKS). |
| **P3 Émission** | Après validation : upsert user, `user_tenants`, puis `create_access_token` (même mapping rôle que login mot de passe). |
| **P4 Front** | Boutons « Continuer avec Google / Microsoft » → URL backend `start` ; gestion redirect succès/erreur (query `token` évitée si possible — préférer cookie **httpOnly** ou fragment selon menace). |
| **P5 Tests** | Mocks JWKS ; pas de secrets dans le dépôt. |

## Références

- [ADR-M2-001](ADR-M2-001_auth_unification.md) — JWT DMS et révocation.
- [frontend-v51/README.md](../../frontend-v51/README.md) — `NEXT_PUBLIC_API_URL`.
