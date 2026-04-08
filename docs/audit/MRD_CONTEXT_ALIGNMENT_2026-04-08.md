# Alignement MRD vs CONTEXT_ANCHOR (P2-DOC-02)

## Alembic / migrations

- **Source opposable pour l’état dépôt + Railway prod** : section **« ÉTAT ALEMBIC »** dans [`docs/freeze/MRD_CURRENT_STATE.md`](../freeze/MRD_CURRENT_STATE.md) (head **090** et suivants, mis à jour avec les mandats migration).
- [`docs/freeze/CONTEXT_ANCHOR.md`](../freeze/CONTEXT_ANCHOR.md) contient des **lignes historiques** (ex. head **067**, M15 Phase 1) : elles documentent le passé après application `059→067`, **pas** l’état cible actuel de prod après V5.1.
- **Règle** : pour go/no-go migration ou preuve de head, lire le MRD ; utiliser l’anchor pour le contexte gelé E-01–E-67 et l’historique, pas comme substitute du MRD sur le numéro de révision courant.

## Sondes et métriques terrain

- Les métriques M15 (coverage mercuriale, annotations, etc.) dans l’anchor restent valides comme **référence de gate** sauf si le MRD les met à jour explicitement.

## Références

- Dette : [`docs/audit/DMS_TECHNICAL_DEBT_P0_P3.md`](DMS_TECHNICAL_DEBT_P0_P3.md) — P2-DOC-02
