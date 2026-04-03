# Inventaire des routes mutantes — `main:app` (audit E1–E3)

**Périmètre** : application production `uvicorn main:app` — routers montés dans `main.py`.  
**Date** : 2026-04-01 — revue statique du code ; à réactualiser si nouveaux routers.

## Principes

- **JWT** : les endpoints métier sensibles doivent dépendre de `get_current_user` (`src/couche_a/auth/dependencies.py`) pour validation **HS256** et claims (`tenant_id`, rôle).
- **RLS** : `TenantContextMiddleware` pose un `tenant_id` à partir de claims **non vérifiés** pour les sessions Bearer ; `is_admin` y est **forcé à False** (voir `src/couche_a/auth/middleware.py`). Le chemin d’autorisation métier repose sur `get_current_user` + `require_case_access` / `require_case_tenant_org` / dépendances extractions.
- **Connexion DB** : les requêtes via `get_connection()` bénéficient du contexte RLS lorsque `set_config` est appliqué par la couche appropriée (pattern migrations 051+). Vérifier les chemins critiques lors de toute nouvelle route.

## Routes publiques (mutation d’état sans JWT)

| Endpoint | Méthode | Auth | Classification | Commentaire |
|----------|---------|------|----------------|-------------|
| `/auth/token` | POST | Aucune (credentials form) | **P1** — surface login ; rate limit | Comportement attendu OAuth2 password. |
| `/auth/register` | POST | Aucune | **P1** — création compte ; rate limit | DETTE-M1-04 documentée dans `auth_router`. |

## Routes mutantes avec `get_current_user` ou dépendance équivalente

| Zone | Préfixe / pattern | Méthodes | Auth | RLS / accès |
|------|-------------------|----------|------|-------------|
| Couche A upload | `/api/cases/{id}/upload-dao`, `upload-offer` | POST | `get_current_user` + ownership | Case-scoped |
| Documents | `/api/upload/{case_id}/{kind}` | POST | `get_current_user` + `require_case_access` | Case-scoped |
| Cases | `/api/cases` | POST | `get_current_user` + tenant dans JWT | Tenant + owner |
| Analysis | `/api/analyze`, `/api/decide` | POST | `get_current_user` + `require_case_access` | Case-scoped |
| Extractions | `/api/...` (voir `extractions.py`) | POST | `require_document_case_access_dep` / équivalent | Document + case |
| Committee | `/committee/...` | POST, DELETE | `get_current_user` | Conn + user |
| Criteria | `/cases/{case_id}/criteria/...` | POST, DELETE | `get_current_user` + `require_case_tenant_org` | Tenant org |
| Scoring | `/api/scoring/calculate` | POST | `get_current_user` | Retourne **501** (volontaire) |
| M14 | `/api/m14/status`, `/api/m14/evaluate`, `/api/m14/evaluations/{case_id}` | GET, POST | `get_current_user` | Case / évaluation — voir `src/api/routes/evaluation.py` |
| Pipeline A | `/api/cases/{case_id}/pipeline/a/run` | POST | `require_case_access_dep` + `apply_rls_session_vars_to_connection` | Monté si import OK |
| Mercuriale / price_check / geo / vendors | selon router | POST | Vérifier fichier | Optionnels |

## Gap analysis (P0 / P1 / P2)

| ID | Sujet | Priorité | Action |
|----|-------|----------|--------|
| GAP-01 | Routes optionnelles (geo, vendors, mercuriale, …) : confirmer dépendance auth sur chaque POST | P2 | Revue fichier par fichier lors d’un durcissement API |
| GAP-02 | `TenantContextMiddleware` sans signature vérifiée sur Bearer : ne pas s’y fier pour `is_admin` | — | Déjà mitigé (admin forcé False) ; doc `middleware.py` |
| GAP-03 | Endpoints 501 (`/api/analyze`, `/api/scoring/calculate`) : pas de fuite de données, mais attentes client | P2 | Voir `HTTP_501_PUBLIC_STATUS.md` |

**P0** : mutation d’état sans contrôle d’identité ni autre garde-fou.  
**P1** : surface attendue mais à surveiller (auth, abuse).  
**P2** : dette documentée ou renforcement progressif.

_Aucun P0 évident_ sur les handlers listés sous « mutantes avec JWT » à la date de l’audit statique ; une passe dynamique (tests d’intrusion / contract tests) reste recommandée.

## Références

- `src/couche_a/auth/middleware.py`
- `src/db/tenant_context.py`
- `docs/adr/ADR-DUAL-FASTAPI-ENTRYPOINTS.md`
