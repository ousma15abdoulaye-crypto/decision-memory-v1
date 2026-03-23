# Registre des routes publiques et exceptions — API DMS (`main:app`)

**Objet** : documenter les chemins **sans** `Bearer` / `get_current_user` dans l’arbre FastAPI, ou avec justification métier.  
**Mise à jour** : lors de l’ajout d’une route sur [`main.py`](../main.py) ou des routeurs inclus.

**Méthode de revue** : exécuter  
`python scripts/audit_fastapi_auth_coverage.py --app main:app --report-md docs/audits/artifacts/audit_main_app_auth_coverage.md`  
et consolider les lignes `AUTH = NO`.

---

## Liste blanche (intentionnel)

| Méthode | Path | Justification |
|---------|------|---------------|
| GET | `/health` | Sonde load balancer / Railway — aucune donnée métier ; statut + version |
| GET | `/docs` | Documentation OpenAPI FastAPI (désactiver en prod stricte via `openapi_url=None` si requis) |
| GET | `/openapi.json` | Schéma API (idem) |
| GET, HEAD | `/static/*` | Fichiers statiques publics (pas de PII par convention déploiement) |

## Routes authentifiées par mécanisme hors Bearer (si présentes)

_Aucune à ce jour sur l’app principale_ : l’auth utilisateur repose sur JWT Bearer via `get_current_user`.

## Routes sensibles — doivent avoir auth + garde case/document

Tout path contenant `{case_id}`, `{document_id}` ou `{job_id}` sous `/api/*` doit apparaître avec **bearer = yes** et **case_guard = yes** dans le rapport d’audit (sauf exception CTO documentée ici).

| Exception | Statut |
|-----------|--------|
| — | Aucune exception ouverte |

---

## Application modulaire `src.api.main:app`

Certaines routes métiers (mercuriale, price-check, vendors, etc.) sont montées sur **`src.api.main:app`** (tests / déploiements modulaires). Le même principe s’applique ; la CI exécute l’audit avec `--fail-prefix` / `--fail-sensitive-prefix` sur cet objet.

---

## Annotation-backend (service séparé)

- `/health` — public pour probes.
- `/webhook` — peut être protégé par `WEBHOOK_CORPUS_SECRET` ; voir [SECURITY_CHECKLIST_PROD.md](../services/annotation-backend/SECURITY_CHECKLIST_PROD.md).
