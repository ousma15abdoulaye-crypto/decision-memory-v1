# Runbook — BLOC7 DOCGEN Enterprise (V4.2.1)

## Objectif

Exporter le PV comité depuis un snapshot scellé avec vérification d’intégrité cryptographique.

Formats supportés :
- JSON (`application/json`)
- PDF (`application/pdf`)
- XLSX (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`)

## Endpoint

`GET /api/workspaces/{workspace_id}/committee/pv?format=json|pdf|xlsx`

## Préconditions

1. `committee_sessions.session_status = sealed`
2. `committee_sessions.seal_hash` non NULL
3. `committee_sessions.pv_snapshot` non NULL
4. JWT autorisé sur le workspace (`workspace.read`)

## Contrôles d’intégrité

- Le service recalcule SHA-256 sur le snapshot canonique (sans `seal.seal_hash`) :
  - `409` si session non scellée
  - `500` si hash recalculé différent du hash scellé

## Contrôles de conformité

- Kill-list interdite absente du snapshot/export JSON :
  - `winner`, `rank`, `recommendation`, `selected_vendor`, `best_offer`, `weighted_scores`
- Export endpoint strictement read-only (aucune écriture DB).
- `weighted_score` XLSX calculé en mémoire export uniquement.

## Vérification rapide (curl)

```bash
curl -sS -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/workspaces/$WORKSPACE_ID/committee/pv?format=json" > pv.json
```

```bash
curl -sS -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/workspaces/$WORKSPACE_ID/committee/pv?format=pdf" > pv.pdf
```

```bash
curl -sS -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/workspaces/$WORKSPACE_ID/committee/pv?format=xlsx" > pv.xlsx
```

## Troubleshooting

- `500 Integrity mismatch` :
  - vérifier que `pv_snapshot` n’a pas été altéré après seal ;
  - vérifier la sérialisation canonique et la présence du bloc `seal`.
- PDF KO en runtime :
  - vérifier build Dockerfile Railway + dépendances système WeasyPrint.
- XLSX vide :
  - vérifier présence `evaluation.scores_matrix` et `evaluation.bundles` dans snapshot.
