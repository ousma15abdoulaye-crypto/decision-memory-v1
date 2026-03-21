# ADR-0053 — Endpoints `/geo/*` publics (lecture seule)

## Contexte

Les routes sous `/geo` exposent un référentiel géographique (pays, régions, communes, zones). Elles ne portent pas de `case_id` ni de données personnelles.

## Décision

Les `GET /geo/*` restent **sans authentification Bearer**, comme annuaire public en lecture seule. Toute évolution (quota, auth, cache edge) fera l’objet d’un ADR complémentaire.

## Conséquences

- Les gates CI `audit_fastapi_auth_coverage.py` ne doivent pas appliquer `--fail-prefix` sur `/geo` sans décision produit explicite.
- La charge ou l’abus éventuel relèvent du **rate limiting** (`REDIS_URL`) et de l’infra.
