# DMS V4.2.0 — INVARIANTS COMPLETS

**Référence** : DMS-V4.2.0-ADDENDUM-WORKSPACE §IV
**Date freeze** : 2026-04-04
**Statut** : FREEZE DÉFINITIF après hash

---

## Invariants canon préservés et adaptés (V4.1.0 → V4.2.0)

| Canon | Texte original V4.1.0 | Adaptation workspace V4.2.0 | Enforcement |
|---|---|---|---|
| INV-R1 | 1 comité = 1 registre (UNIQUE committee_id) | 1 workspace = 1 committee_session (UNIQUE workspace_id) | UNIQUE constraint sur `committee_sessions(workspace_id)` |
| INV-R2 | recorded_at = système. Jamais saisi. | `emitted_at`, `occurred_at`, `assembled_at` = système | DEFAULT NOW() sur colonnes timestamp |
| INV-R3 | submission_registry_events = append-only | `workspace_events` + `committee_deliberation_events` = append-only | Trigger `fn_reject_mutation` |
| INV-R4 | Aucun dépôt après fermeture registre | Workspace sealed = lecture seule totale (INV-W04) | Trigger `fn_workspace_sealed_final` |
| INV-R5 | Registre sans comité = impossible (FK NOT NULL) | Session sans workspace = impossible (FK NOT NULL) | FK NOT NULL sur `committee_sessions.workspace_id` |
| INV-R6 | Registre n'écrit jamais en Couche B | Workspace n'écrit jamais en W2 directement (ARQ projector) | Architecture : seul ARQ projector écrit en Couche B |
| INV-R7 | Pipeline lit le registre — jamais le modifie | M12→M14 lisent workspace, émettent des events | Architecture : pipeline émet, ne modifie pas |
| INV-R8 | Dépôt = supplier_name_raw + (email OU téléphone) | Bundle = vendor_name_raw obligatoire | NOT NULL sur `supplier_bundles.vendor_name_raw` |
| INV-R9 | Chaque dépôt = recorded_by + recorded_at | Tout event = actor_id + emitted_at | NOT NULL sur `workspace_events.actor_id` + `emitted_at` |

---

## Invariants workspace ajoutés (V4.2.0)

### INV-W01 — Immuabilité des actes de comité

```
committee_deliberation_events = APPEND-ONLY (trigger DB)
committee_sessions : sealed et closed = irréversibles (trigger DB)
Correction d'un acte = nouvel enregistrement avec référence à l'original.
```

**Enforcement** : trigger `fn_reject_mutation` sur `committee_deliberation_events` + trigger `fn_committee_session_sealed_final` sur `committee_sessions`
**Test requis** : INSERT/UPDATE/DELETE sur CDE sealed → exception
**Stop signal** : S12

### INV-W02 — Souveraineté de la chaîne canonique

```
Aucune donnée affichée au comité ne provient :
- d'un calcul UI
- d'un cache non lié à workspace_events
- d'un endpoint hors chaîne M12→M14
Le dashboard est une projection de workspace_events. Rien d'autre.
```

**Enforcement** : review code — aucun calcul côté WebSocket ou route
**Test requis** : WebSocket payload = sous-ensemble de workspace_events
**Stop signal** : S8

### INV-W03 — Séparation CRUD / append-only

```
CRUD (composition administrative) :
  committee_session_members, workspace_memberships

APPEND-ONLY (actes et faits) :
  workspace_events, committee_deliberation_events,
  score_history, elimination_log, decision_history,
  vendor_market_signals, dict_collision_log, audit_log
```

**Enforcement** : triggers `fn_reject_mutation` sur chaque table append-only
**Test requis** : UPDATE/DELETE sur chaque table append-only → exception
**Stop signal** : S12

### INV-W04 — Frontière sealed / live

```
Workspace status = 'sealed' → lecture seule totale.
Aucun agent, service, utilisateur ne peut modifier un artefact
d'un workspace sealed.

Opérations permises :
  - lecture
  - export PV
  - audit log query
  - alimentation Couche B (via ARQ event — écriture HORS workspace)
```

**Enforcement** : trigger `fn_workspace_sealed_final`
**Test requis** : modification artefact workspace sealed → exception
**Stop signal** : S7

### INV-W05 — Identité workspace-event

```
Tout événement émis dans DMS contient :
  - workspace_id (NOT NULL)
  - tenant_id (NOT NULL)
  - event_type (enum strict)
  - actor_id (NOT NULL)
  - emitted_at (UTC, immutable)
  - payload (JSONB, versionné via schema_version)
Un événement incomplet est rejeté par contraintes DB.
```

**Enforcement** : NOT NULL constraints sur `workspace_events`
**Test requis** : INSERT avec workspace_id NULL → exception
**Stop signal** : S6

### INV-W06 — Interdiction de verdict automatique

```
Aucun composant M12→M14, Pass -1, agent ne produit :
  winner / rank / recommendation / best_offer / selected_vendor

Constraint CHECK niveau DB sur evaluation_documents.
Constraint de prompt sur tous les agents PydanticAI.
Conforme RÈGLE-09 canon V4.1.0.
```

**Enforcement** : `ALTER TABLE evaluation_documents ADD CONSTRAINT no_winner_field`
**Test requis** : INSERT evaluation_documents avec payload winner → rejeté
**Stop signal** : S5

### INV-W07 — WebSocket = diffusion de vérité fédérée uniquement

```
Le WebSocket pousse uniquement des événements issus de workspace_events.
Il ne pousse jamais :
  - des objets calculés côté API
  - des états de tables non passés par workspace_events
  - des payloads construits à la demande
```

**Enforcement** : review code — WebSocket query = SELECT FROM workspace_events
**Test requis** : comparer WebSocket payload avec workspace_events row
**Stop signal** : S8

### INV-W08 — Pas d'artefact flottant

```
Tout document, bundle, score, event appartient à un workspace.
workspace_id NOT NULL sur toute table (après migration 074).
Exception : market_surveys.workspace_id nullable (W2 hors processus).
```

**Enforcement** : NOT NULL constraints après migration 074
**Test requis** : INSERT document sans workspace_id → exception
**Stop signal** : S11

---

## Nouvelle règle système — BLOC-04 corrigé

### RÈGLE-W01 — SET LOCAL tenant obligatoire

```
Toute connexion DB dans une requête API DOIT exécuter
SET LOCAL app.tenant_id = $1 avant toute opération.
Si l'appelant est admin, SET LOCAL app.is_admin = 'true'.

SET LOCAL obligatoire (pas SET).
  SET LOCAL scope = transaction uniquement.
  Réinitialisé automatiquement à la fin de la transaction.
  Empêche la fuite de tenant entre requêtes sur le même pool.

Variable : app.tenant_id (cohérent avec migrations 055-059).
Override admin : app.is_admin (cohérent avec RLS existant).
Le tenant_id provient du JWT décodé, JAMAIS d'un paramètre query/body.
```

**Pattern obligatoire :**

```python
async def get_db_with_tenant(
    token: str = Depends(verify_jwt),
    pool: asyncpg.Pool = Depends(get_pool)
) -> AsyncGenerator[asyncpg.Connection, None]:
    claims = decode_jwt(token)
    tenant_id = claims["tenant_id"]
    is_admin = claims.get("is_admin", False)
    async with pool.acquire() as conn:
        await conn.execute(
            "SET LOCAL app.tenant_id = $1", str(tenant_id)
        )
        if is_admin:
            await conn.execute("SET LOCAL app.is_admin = 'true'")
        yield conn
```

**Enforcement** : middleware FastAPI — dependency injection obligatoire
**Test requis** : requête sans SET LOCAL → RLS retourne 0 lignes
**Test requis** : deux requêtes consécutives, tenants différents → isolation
**Test requis** : admin voit tous les tenants (app.is_admin = 'true')
**Stop signal** : aucun dédié — couvert par test CI

---

## Résumé

| Catégorie | Identifiants | Total |
|---|---|---|
| Invariants canon préservés | INV-R1 → INV-R9 | 9 |
| Invariants workspace ajoutés | INV-W01 → INV-W08 | 8 |
| Règle système ajoutée | RÈGLE-W01 | 1 |
| **Total invariants + règles** | | **18** |

---

*Gelé après hash. Tout amendement → DMS_V4.2.1_PATCH.md*
