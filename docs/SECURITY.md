# SECURITY — DMS V3.3.2

## Threat model

- Principales menaces: accès non autorisé, fuite données, upload malveillant, abus ressources.

## Authentification (AuthN)

- JWT access + refresh, rotation, expirations.
- Bibliothèque utilisée, algorithme, durée.

## Autorisation (AuthZ)

- RBAC 5 rôles: admin, manager, buyer, viewer, auditor.
- Matrice permissions (table).

## Rate limiting

- Règles par endpoint (upload, export, API publiques).

## Upload validation

- Magic bytes, taille max, types autorisés.

## Secrets management

- Variables d’environnement, gestion `.env`.

## Audit logging

- Tables, événements loggés.

## Tests sécurité obligatoires

- Liste `tests/security/test_*.py`.
