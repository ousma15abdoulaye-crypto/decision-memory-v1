# ADR-0052 — Annuaire fournisseurs global, auth HTTP, option multi-tenant

## Contexte

La table `vendors` est un **référentiel partagé** (pas de colonne `tenant_id` à ce jour). Le scan invariant `inv10` peut signaler des requêtes sans filtre tenant sur `vendors` : c’est **accepté** tant que le périmètre produit reste « annuaire global ».

## Décision

1. **Court terme** : toutes les routes `GET /vendors` et `GET /vendors/{vendor_id}` exigent un **JWT Bearer** (`get_current_user`). Lecture seule inchangée.
2. **Contrôle d’accès** : pas d’isolation par dossier ; le RBAC existant (viewer, buyer, admin, etc.) s’applique via le token.
3. **Moyen terme (option)** : introduire `tenant_id` sur `vendors` (ou table de liaison), filtrer les listes, adapter `inv10` et les migrations.

## Conséquences

- Les clients scripts doivent passer `Authorization: Bearer …` (comme le reste de l’API métier).
- La surface « données globales » reste documentée ; la preuve forte d’isolement reste **RLS sur les tables dossier** (`cases`, etc.) avec rôle `dm_app`.

## Références

- [`docs/audits/SEC_MT_01_BASELINE.md`](../audits/SEC_MT_01_BASELINE.md)
- `src/vendors/router.py`
