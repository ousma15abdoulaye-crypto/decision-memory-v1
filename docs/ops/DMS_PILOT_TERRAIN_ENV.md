# Pilote terrain — variables d’environnement (Railway)

Mode **opt-in**, **désactivé par défaut**. À utiliser uniquement pour valider le DMS de bout en bout avec un compte identifié, sans dépendre des memberships / RBAC / scellement / garde M16.

**Gouvernance** : ce compte est le **pilote principal** de test terrain et stress test pré-prod — voir **`docs/freeze/CONTEXT_ANCHOR.md`** (**E-102**, addendum **PILOTE TERRAIN PRODUCTION / STRESS TEST**). **Ne pas** coder d’email ou d’id en dur dans le dépôt : uniquement ces variables.

## Variables

| Variable | Obligatoire | Description |
|----------|-------------|-------------|
| `DMS_PILOT_TERRAIN_FULL_ACCESS` | Pour activer | `true` / `1` pour activer le mode pilote. |
| `DMS_PILOT_USER_IDS` | Recommandé | Liste d’identifiants `users.id` (JWT `sub`), séparés par virgule ou point-virgule. Ex. `12` ou `3, 5, 7`. |
| `DMS_PILOT_USER_EMAILS` | Optionnel | Emails (minuscules conseillés), séparés par virgule. Résolus une fois au chargement vers des `users.id` (requête DB). Les échecs de résolution sont loggés **sans** exposer les emails (compteur uniquement). |
| `DMS_PILOT_DEFAULT_TENANT_UUID` | Optionnel | UUID du tenant PostgreSQL pour `acquire_with_rls` quand le JWT pilote n’a pas de `tenant_id` : évite un `SELECT` synchrone sur `tenants` au premier appel agent. |

**Règle de sécurité** : si le flag est activé mais **aucun** id n’est obtenu (listes vides ou emails inconnus), **aucun** utilisateur n’est pilote.

## Obtenir le `sub` (user id)

En SQL : `SELECT id, email FROM users WHERE email ILIKE 'votre@email';`  
Sur Railway, renseigner `DMS_PILOT_USER_IDS` avec la colonne `id`.

## Comportement

- Accès **tous workspaces** (contrôle tenant contourné pour le pilote).
- `guard()` : membership / permissions / scellement contournés pour le pilote.
- M16 : pas de blocage état cognitif ni scellement pour le pilote.
- Agent : pas de blocage INV-W06 pour le pilote ; `agent.query` sans `workspaceId` autorisé ; RLS async `is_admin` pour le pilote.
- JWT validé : après login, `set_rls_is_admin(true)` pour le pilote (contourne RLS PostgreSQL côté requêtes synchrones).
- Dossiers / documents (`case_access`) : pas de contrôle propriétaire pour le pilote.

## Désactivation

Mettre `DMS_PILOT_TERRAIN_FULL_ACCESS=false` (ou supprimer la variable) et retirer les ids / emails pilotes.
