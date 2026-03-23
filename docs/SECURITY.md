# SECURITY — DMS (API principale + périmètres associés)

**Version document** : alignée sur l’implémentation repo (JWT V4.1, RLS, M2).  
**Non** : ce document ne constitue pas une certification SOC2 / ISO 27001 ; il décrit les contrôles techniques présents.

---

## 1. Threat model (résumé)

| Menace | Contrôles principaux |
|--------|----------------------|
| Accès non autorisé aux dossiers / documents | JWT + RBAC + `require_case_access` / `require_document_case_access` + RLS PostgreSQL (`app.tenant_id`) |
| IDOR (deviner `case_id` / `document_id`) | Garde métier sur routes sensibles ; audit CI ([`scripts/audit_fastapi_auth_coverage.py`](../scripts/audit_fastapi_auth_coverage.py)) |
| Brute-force login | Rate limiting (`slowapi`) sur `/auth/token`, `/auth/register` |
| Upload malveillant | Magic bytes, taille max, MIME allowlist — [`src/upload_security.py`](../src/upload_security.py) |
| Abus de ressources | Rate limiting global + constantes par criticité — [`src/ratelimit.py`](../src/ratelimit.py) ; voir [SECURITY_RATE_LIMITING.md](SECURITY_RATE_LIMITING.md) |
| Fuite de secrets | Variables d’environnement uniquement en prod ; pas de secrets dans les logs — voir [SECURITY_SECRETS_RUNBOOK.md](SECURITY_SECRETS_RUNBOOK.md) |

---

## 2. Authentification (AuthN)

| Élément | Détail |
|---------|--------|
| **Point d’entrée** | [`src/auth_router.py`](../src/auth_router.py) (`/auth/token`, `/auth/register`, `/auth/me`) |
| **Moteur** | [`src/couche_a/auth/jwt_handler.py`](../src/couche_a/auth/jwt_handler.py) — ADR-M1-001 |
| **Algorithme** | HS256 |
| **Secret** | `SECRET_KEY` **requis** ; `JWT_SECRET` = repli de lecture seulement si `SECRET_KEY` absent (éviter les deux valeurs différentes en prod) |
| **Claims access token** | `sub` (user_id), `role`, `jti`, `iat`, `exp`, `type`, **`tenant_id`** (aligné RLS) |
| **TTL access** | `JWT_ACCESS_TTL_MINUTES` (défaut **30**) |
| **Refresh** | TTL refresh documenté dans le handler (`JWT_REFRESH_TTL_DAYS`) — flux refresh selon déploiement |
| **Révocation** | Table `token_blacklist` (migration **037**) — jetons révoqués rejetés à la vérif |
| **Unification** | ADR-M2-001 : plus de double stack legacy sur les routes d’auth exposées par `main.py` |

**Dépendance FastAPI** : [`get_current_user`](../src/couche_a/auth/dependencies.py) sur les routes protégées.

---

## 3. Autorisation (AuthZ)

| Élément | Détail |
|---------|--------|
| **Rôles JWT** | `admin`, `manager`, `buyer`, `viewer`, `auditor` — [`VALID_ROLES`](../src/couche_a/auth/jwt_handler.py) |
| **Matrice métier** | [`docs/adr/ADR-M1-002_rbac_matrix.md`](adr/ADR-M1-002_rbac_matrix.md) |
| **Accès dossier / document** | [`src/couche_a/auth/case_access.py`](../src/couche_a/auth/case_access.py) |
| **Isolation tenant (DB)** | `user_tenants` + `cases.tenant_id` + policies RLS — migration **051** ; `set_config('app.tenant_id', …)` dans [`src/db/core.py`](../src/db/core.py), [`src/db/connection.py`](../src/db/connection.py), [`src/db/tenant_context.py`](../src/db/tenant_context.py) |

**Limite** : l’audit automatisé des routes ne voit que les **dépendances FastAPI** déclarées sur le handler ; une garde appelée uniquement dans le corps de la fonction n’apparaît pas — d’où la revue manuelle et le registre des routes publiques.

---

## 4. Rate limiting

Détail opérationnel (Redis vs mémoire, multi-workers) : **[SECURITY_RATE_LIMITING.md](SECURITY_RATE_LIMITING.md)**.

---

## 5. Upload

- **Fichiers** : [`src/upload_security.py`](../src/upload_security.py) — `filetype` (magic bytes), `MAX_UPLOAD_SIZE`, `MAX_CASE_TOTAL`, allowlist MIME.
- **Tests** : [`tests/test_upload_security.py`](../tests/test_upload_security.py).

---

## 6. Secrets management

Procédures de rotation et variables : **[SECURITY_SECRETS_RUNBOOK.md](SECURITY_SECRETS_RUNBOOK.md)**.

---

## 7. Routes publiques et exceptions (registre)

Liste blanche maintenue : **[SECURITY_PUBLIC_ROUTES.md](SECURITY_PUBLIC_ROUTES.md)**.

---

## 8. Audit logging (métier / traçabilité)

- Tables et événements selon modules (comité, pipeline, etc.) — voir migrations `audit_*` et code métier.
- **Pseudonymisation** sortie sensible : [`docs/adr/ADR-013_sensitive_data_pseudonymisation.md`](adr/ADR-013_sensitive_data_pseudonymisation.md).

---

## 9. Service satellite — annotation-backend (M12)

Même dépôt, **autre processus** (FastAPI dédié) : pas de JWT utilisateur DMS.

| Contrôle | Référence |
|----------|-----------|
| Webhook LS | `WEBHOOK_CORPUS_SECRET` (header `X-Webhook-Secret`) si défini |
| CORS | `CORS_ORIGINS` — éviter `*` en prod |
| Clés externes | Mistral, Label Studio, S3/R2 — [`services/annotation-backend/ENVIRONMENT.md`](../services/annotation-backend/ENVIRONMENT.md) |
| Checklist prod | [`services/annotation-backend/SECURITY_CHECKLIST_PROD.md`](../services/annotation-backend/SECURITY_CHECKLIST_PROD.md) |

---

## 10. Audit automatisé des routes FastAPI

```bash
python scripts/audit_fastapi_auth_coverage.py --app main:app
python scripts/audit_fastapi_auth_coverage.py --app main:app --fail-prefix /api/extractions
python scripts/audit_fastapi_auth_coverage.py --app main:app --fail-sensitive-prefix /api/cases
```

- **Heuristique** : présence de `get_current_user` et de garde case/document dans l’arbre `Depends`.
- **CI** : voir [`.github/workflows/ci-main.yml`](../.github/workflows/ci-main.yml) — rapport généré sous `docs/audits/artifacts/` + artefact GitHub Actions.
- **Limite** : ne remplace pas pentest ni revue manuelle.

---

## 11. Tests sécurité (non exhaustif)

| Zone | Fichiers |
|------|----------|
| Auth / headers | `tests/auth/test_security_headers.py`, `tests/test_auth.py` |
| Upload | `tests/test_upload_security.py` |
| RBAC | `tests/test_rbac.py` |
| API / accès | `tests/api/test_extractions_auth.py` (et assimilés) |
| Frontière A/B | `tests/boundary/` |

Il n’existe pas de répertoire unique `tests/security/test_*.py` ; les tests sont répartis par domaine.

---

## 12. Références ADR

- [ADR-M2-001 — Unification auth](adr/ADR-M2-001_auth_unification.md)
- [ADR-M1-001 — JWT](adr/ADR-M1-001_jwt_strategy.md)
- [ADR-M1-002 — RBAC](adr/ADR-M1-002_rbac_matrix.md)
- [ADR-016 — Rate limiting Redis](adr/ADR-016_rate_limiting_redis.md)
- [ADR-0010 — Suivi post-audit](adr/ADR-0010_correctifs-prioritaires-post-audit.md) (table d’implémentation §10)
- [CONTRACT_A_B.md](CONTRACT_A_B.md) — frontière Couche A / B

---

## 13. Matrice menace → contrôle (synthèse 1 page)

| Menace | Contrôle | Où / preuve |
|--------|----------|-------------|
| Session / token abus | JWT court, `jti`, blacklist | `jwt_handler.py`, migration 037 |
| Brute-force login | Rate limit | `auth_router.py`, `ratelimit.py` |
| IDOR case/document | `require_case_access*` + RLS tenant | `case_access.py`, migration 051 |
| Upload malveillant | MIME + taille | `upload_security.py`, `tests/test_upload_security.py` |
| Absence de garde sur route | Audit deps FastAPI | `scripts/audit_fastapi_auth_coverage.py`, CI `ci-main.yml` |
| Fuite credentials | Env + pas de log secrets | [SECURITY_SECRETS_RUNBOOK.md](SECURITY_SECRETS_RUNBOOK.md) |
| Webhook / LLM satellite | Secret webhook, CORS, clés | [SECURITY_CHECKLIST_PROD.md](../services/annotation-backend/SECURITY_CHECKLIST_PROD.md) |

**Gel pendant annotation** : ne pas modifier `src/` ni redéployer l’annotation-backend sans second plan — voir [`.cursor/rules/dms-annotation-backend-freeze.mdc`](../.cursor/rules/dms-annotation-backend-freeze.mdc).
