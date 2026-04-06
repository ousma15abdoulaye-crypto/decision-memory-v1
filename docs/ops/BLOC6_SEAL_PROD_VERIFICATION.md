# Runbook — preuve POST `/committee/seal` en production (BLOC 6 BIS)

**Objectif** : documenter la preuve opposable **HTTP 200/201**, `seal_hash`, `pv_snapshot` persistés sur Railway après déploiement du correctif UUID (`safe_json_dumps`, handler seal).

**Prérequis** : image API déployée incluant le merge du correctif BLOC 6 BIS ; JWT utilisateur autorisé à sceller ; `workspace_id` et `session_id` de test en état **in_deliberation** (ou flux mandat pilote).

## 1. Variables

```text
BASE_URL=https://decision-memory-v1-production.up.railway.app
TOKEN=<JWT Bearer>
WORKSPACE_ID=<uuid>
```

## 2. Appel seal

```http
POST /api/workspaces/{WORKSPACE_ID}/committee/seal
Authorization: Bearer {TOKEN}
Content-Type: application/json

{"seal_comment": "Seal preuve BLOC 6 BIS post-deploy"}
```

**Attendu** : statut **200** ou **201** ; corps JSON avec `seal_hash` (64 hex) et structure de session incluant `pv_snapshot` (ou champs documentés par l’API).

**Échec** : **500** — capturer **corps brut** `r.text` + logs Railway au timestamp ; **STOP**, escalade CTO (ne pas valider BLOC 7 tant que non résolu).

## 3. Vérification SQL (lecture prod)

Avec `scripts/with_railway_env.py` + `scripts/run_pg_sql.py` (ou client SQL habituel) :

```sql
SELECT id, session_status, seal_hash, sealed_at,
       pv_snapshot IS NOT NULL AS has_pv_snapshot
FROM committee_sessions
WHERE workspace_id = '{WORKSPACE_ID}'::uuid;
```

**Attendu** : `session_status = 'sealed'` ; `seal_hash` non NULL ; `has_pv_snapshot = true`.

## 4. Archivage preuve

Conserver dans le ticket / rapport pilote :

- timestamp UTC du POST ;
- extrait JSON de réponse (hash + clés snapshot) ;
- résultat SQL ci-dessus ;
- révision Git déployée (`git rev-parse HEAD` côté pipeline ou tag release).

## 5. Lien scripts

- Enchaînement API + contrôles : [`scripts/bloc6_pilot_sci_mali_run.py`](../../scripts/bloc6_pilot_sci_mali_run.py)
- Rapport opposable : [`BLOC6_PILOT_SCI_MALI_REPORT.md`](BLOC6_PILOT_SCI_MALI_REPORT.md)

**Statut** : la preuve machine est **humaine-attestée** après exécution sur l’environnement cible ; ce runbook ne substitue pas l’exécution en prod.
