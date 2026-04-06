# Preuve produit — mandat hardening

**Date** : 2026-04-06  
**Verdict** : **AMBRE**

## Questions / réponses

| Question | Réponse |
|----------|---------|
| Le seal est-il réel (prod pilote) ? | **Non** au moment du check — `session_status=active`, pas de `seal_hash` / `pv_snapshot` (workspace `3a1ebd0e-dc79-4b40-bc94-dcae1de6d33f`, Railway). |
| PV exportable ? | **Code OK** — route + intégrité hash ; **preuve fichier** non capturée sans session sealed. |
| Comparatif exportable ? | **Code OK** — XLSX depuis snapshot via `build_comparative_table_model_from_snapshot`. |
| Champs interdits absents ? | **Oui** dans pipeline snapshot (validation + sanitize) — tests unitaires. |
| Exports lisibles / traçables ? | PDF footer + feuille Traceability XLSX ; relecture métier **non faite** sur export réel. |
| GAP bloquant ? | **Seal prod** sur un workspace en `in_deliberation` → exécuter `POST …/committee/seal` après déploiement + JWT, puis `python scripts/with_railway_env.py python scripts/hardening_product_sql_checks.py <workspace_id>`. |

## Commandes de preuve

```bash
python scripts/with_railway_env.py python scripts/hardening_product_sql_checks.py <workspace_uuid>
```

Attendu **VERT** : `session_status=sealed`, `len(seal_hash)=64`, `pv_snapshot` non NULL, `process_workspaces.status=sealed`.

## Pour passer en VERT

1. Seal réussi (API + SQL).
2. `GET …/committee/pv?format=json|pdf|xlsx` sur le même workspace.
3. Archiver hashes + extraits (sans secrets) dans le ticket release.
