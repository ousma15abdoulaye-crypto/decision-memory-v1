# ADR-M1B-001 — Audit Hash Chain

```
Statut   : ACCEPTÉ
Date     : 2026-02-27
Auteur   : Agent DMS V4.1.0
Milestone: M1B — Audit Hash Chain
Branche  : feat/m1b-audit-hash-chain
```

---

## Contexte

Le DMS (Decision Memory System) opère dans un contexte d'achat public au Mali.
Chaque décision — attribution de marché, approbation de commande, délégation de
comité — engage la responsabilité de l'organisation devant des auditeurs internes,
des partenaires bailleurs (USAID, UE, ONU) et potentiellement des juridictions
administratives.

L'exigence fondamentale : **toute action sur les données doit laisser une trace
opposable, immuable et vérifiable**.

Sans traçabilité cryptographique :
- Un opérateur mal intentionné peut modifier ou supprimer un événement passé
- Un auditeur externe ne peut pas distinguer un log légitime d'un log reconstruit
- En cas de litige, le système ne produit aucune preuve recevable

La table `audit_log` avec chaînage SHA-256 répond à cette exigence.

---

## Décision

### 1. Algorithme de hachage : SHA-256 via pgcrypto (DB) + hashlib (Python)

SHA-256 est retenu pour :
- Sa disponibilité native dans PostgreSQL via l'extension `pgcrypto` (confirmée v1.3)
- Sa disponibilité standard dans Python (`hashlib`)
- Sa résistance aux collisions pour un usage d'audit (non-cryptographique au sens
  authentification, mais suffisant pour la détection d'altération)
- Sa lisibilité (hexdigest 64 caractères) pour les auditeurs humains

### 2. Ordre total déterministe : `chain_seq BIGINT GENERATED ALWAYS AS IDENTITY`

Le chaînage requiert un ordre total strict entre les entrées. `GENERATED ALWAYS AS
IDENTITY` garantit :
- Un entier croissant strictement monotone, attribué par PostgreSQL
- Aucune collision possible (contrairement à `ORDER BY timestamp` où deux INSERT
  simultanés peuvent avoir le même `now()`)
- Déterminisme indépendant des fuseaux horaires, des réseaux ou des redémarrages

`chain_seq` est inclus dans le calcul du hash pour lier chaque entrée à sa position
dans la séquence.

### 3. Chaînage : `prev_hash` → `event_hash`

Chaque entrée contient :
- `prev_hash` : hash de l'entrée précédente (ou `"GENESIS"` pour la première)
- `event_hash` : SHA-256 calculé sur les champs de l'entrée + `prev_hash`

Cette structure forme une chaîne : altérer une entrée passée invalide tous les
hashes suivants — détectable immédiatement par `fn_verify_audit_chain()`.

### 4. `payload_canonical` : représentation canonique unique — IMMUABLE

La sérialisation JSON native de Python n'est pas déterministe (ordre des clés,
espacement). Pour garantir que Python et la DB calculent le même hash :

```python
# Règle immuable — ne jamais modifier après M1B
# Tout changement = rupture de chaîne rétroactive

if payload is None or payload == {}:
    payload_canonical = ""
else:
    payload_canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
```

`payload_canonical` est stocké en table. `fn_verify_audit_chain()` utilise
`payload_canonical` stocké — jamais `payload::text` directement.

**Cette définition est immuable après M1B.** Tout changement introduit une rupture
rétroactive de toutes les chaînes existantes.

### 5. Algorithme `event_hash` — IMMUABLE après M1B

Champs concaténés dans cet ordre exact (séparateur : aucun, concaténation directe) :

```
entity  ||  entity_id  ||  action  ||  (actor_id ou "")  ||
payload_canonical  ||  timestamp.isoformat()  ||  str(chain_seq)  ||  prev_hash
```

Calcul Python :

```python
event_hash = hashlib.sha256(
    (
        entity
        + entity_id
        + action
        + (actor_id or "")
        + payload_canonical
        + timestamp.isoformat()
        + str(chain_seq)
        + prev_hash
    ).encode("utf-8")
).hexdigest()
```

Calcul DB (`fn_verify_audit_chain`) :

```sql
computed := encode(
    digest(
        rec.entity            ||
        rec.entity_id         ||
        rec.action            ||
        COALESCE(rec.actor_id, '') ||
        rec.payload_canonical ||
        rec.timestamp::text   ||
        rec.chain_seq::text   ||
        prev,
        'sha256'
    ),
    'hex'
);
```

**Attention** : `timestamp.isoformat()` côté Python et `timestamp::text` côté DB
doivent produire la même représentation. Les tests de vérification croisée
(`test_audit_chain.py`) valident cette identité. En cas de divergence → STOP-M1B-9.

### 6. Séquence d'écriture `write_event()` — choix RETURNING

Le `chain_seq` est attribué par PostgreSQL à l'INSERT. Il faut le connaître pour
calculer `event_hash`. Deux approches possibles :

**Option A — INSERT puis UPDATE** :
1. INSERT avec `event_hash = ''` (provisoire)
2. DB attribue `chain_seq` via IDENTITY
3. Recalcul Python de `event_hash` avec `chain_seq` réel
4. `UPDATE audit_log SET event_hash = %s WHERE id = %s`

**Option B — INSERT avec RETURNING** :
1. `INSERT ... RETURNING id, chain_seq`
2. Calcul Python de `event_hash` avec `chain_seq` retourné
3. `UPDATE audit_log SET event_hash = %s WHERE id = %s`

_Remarque : les Options A et B ont été envisagées au design mais **ne sont pas**
implémentées dans la version actuelle. La migration crée un trigger
`BEFORE UPDATE` qui rejette tout `UPDATE` sur `audit_log`, rendant ces
stratégies en deux temps (INSERT puis UPDATE) inapplicables._

**Option C — mono-INSERT (implémentation actuelle)** :
1. Récupération de `chain_seq` (via `nextval`/IDENTITY ou équivalent) côté
   application avant l'écriture
2. Calcul Python de `event_hash` avec le `chain_seq` réel et le hash précédent
3. `INSERT INTO audit_log (..., chain_seq, event_hash, ...) VALUES (...)`

**Décision : Option C retenue**.
Cette option est alignée avec le trigger append-only `BEFORE UPDATE` : aucune
mise à jour de ligne (y compris de `event_hash`) n'est autorisée après l'INSERT.
Le hash doit donc être définitif au moment de l'écriture.

**Note de sécurité** : toute tentative d'`UPDATE` (y compris sur `event_hash`
seul) est bloquée par le trigger append-only. L'intégrité repose sur :
- le calcul correct de `event_hash` côté application avant l'INSERT ;
- le fait que les lignes sont strictement append-only (pas de DELETE/UPDATE).
Si un audit plus strict est requis (par ex. matérialiser l'état de
finalisation), une colonne `hash_finalized BOOLEAN` peut être ajoutée
ultérieurement (post-M1B).
### 7. `actor_id` : TEXT nullable — FK reportée

`actor_id` est `TEXT` nullable pour deux raisons :
- Certaines actions système n'ont pas d'acteur humain (jobs, triggers)
- La FK formelle vers `users(id)` est reportée : `users.id` est actuellement
  `INTEGER` (legacy), incompatible avec UUID — voir `DETTE-M1-01`

La FK sera ajoutée lors de la résolution de `DETTE-M1-01` (migration dédiée post-beta).

### 8. Trigger append-only — DELETE / UPDATE / TRUNCATE

La protection append-only est **applicative, non absolue** :
- Un superuser PostgreSQL peut désactiver le trigger (`ALTER TABLE DISABLE TRIGGER`)
- La protection cible le cadre applicatif normal

Formulation honnête (CORR-08) :
> `audit_log` est append-only — l'opération est non autorisée et détectable
> dans le cadre applicatif normal.

Deux triggers distincts :
- `trg_audit_log_no_delete_update` : trigger `FOR EACH ROW` sur DELETE et UPDATE
- `trg_audit_log_no_truncate` : trigger `FOR EACH STATEMENT` sur TRUNCATE (CORR-04)

---

## Alternatives écartées

| Alternative | Raison du rejet |
|---|---|
| Hash sans chaînage (hash par entrée indépendant) | Ne détecte pas l'insertion ou la suppression d'entrées — un attaquant peut supprimer une ligne et recalculer les hashes restants |
| `ORDER BY timestamp` seul | Non déterministe — deux INSERT simultanés peuvent avoir le même `now()` |
| Chiffrement des colonnes | Protège la confidentialité, pas l'intégrité — un admin peut déchiffrer et réchiffrer après modification |
| Hash côté applicatif uniquement (sans pgcrypto) | Possible, mais la vérification DB via `fn_verify_audit_chain()` est plus rapide et évite un aller-retour Python pour des millions de lignes |
| Blockchain externe | Sur-ingénierie hors de propos pour le périmètre Mali DMS |

---

## Conséquences

### Positives
- Toute altération de `audit_log` est détectable par `fn_verify_audit_chain()`
- La chaîne est vérifiable sans accès à un système externe
- L'algorithme est documenté et reproductible par un auditeur tiers

### Négatives / Contraintes
- **Performance INSERT** : chaque `write_event()` nécessite deux opérations DB
  (INSERT + UPDATE). Acceptable pour un volume d'audit DMS (< 10k événements/jour
  en contexte Mali). À surveiller si le volume augmente.
- **Vérification O(n)** : `fn_verify_audit_chain()` parcourt toutes les entrées
  de la plage. Sur des millions de lignes, utiliser les paramètres `p_from`/`p_to`
  pour limiter la plage.
- **Immuabilité de l'algorithme** : toute modification de l'ordre des champs,
  de la canonicalisation ou de l'algorithme de hash après M1B invalide toutes les
  chaînes existantes. Documenter toute évolution dans un ADR dédié.
- **Superuser peut désactiver le trigger** : la protection n'est pas absolue.
  Pour une protection maximale, combiner avec des audits PostgreSQL au niveau WAL
  (hors scope M1B).

---

## Références

- `TECHNICAL_DEBT.md` — `DETTE-M1-01` (actor_id FK reportée)
- `docs/freeze/DMS_V4.1.0_FREEZE.md` — §PARTIE V schéma cible
- `alembic/versions/038_audit_hash_chain.py`
- `src/couche_a/audit/logger.py`
- CORR-01 à CORR-08 — registre des corrections v1.0 → v1.1 du mandat M1B
