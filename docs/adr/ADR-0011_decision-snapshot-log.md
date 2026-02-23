# ADR-0011 — Decision Snapshot Log

**Statut :** ACCEPTED
**Date :** 2026-02-23
**Auteur :** Abdoulaye Ousmane — CTO, Founder
**Références :** Constitution DMS V3.3.2 §6.3, ADR-0002, ADR-0008, M-COMMITTEE-CORE (#9)
**SHA-256 :** 380E59298A6FA868DC7AE940EFE63176D1527B3053416132912FB5EB66DCC13A

---

## Contexte

Avant ce milestone, le système produit des calculs (scoring, PriceCheck) mais n'a pas de mécanisme
pour capturer la décision humaine au moment exact où elle devient vraie et opposable.
La Couche B (future) aura besoin de faits bruts, neutres, rejouables pour construire
l'intelligence marché. Ces faits doivent exister **avant** que la Couche B soit développée.

---

## Décision

### Principe cardinal : *capture tôt, agrégation tard*

Dès qu'un comité scelle une décision, un `DecisionSnapshot` append-only est émis
**dans la même transaction de seal**. Ce snapshot capture l'état brut de la décision
sans interprétation, sans classement, sans recommandation.

La Couche B (Milestones #18/#19) agrégera ces snapshots plus tard pour construire
le Market Intelligence Signal. Elle n'a pas besoin d'exister pour que les snapshots
s'accumulent correctement.

---

## Architecture

### Table `public.decision_snapshots` (append-only)

```sql
snapshot_id          UUID        PK DEFAULT gen_random_uuid()
case_id              TEXT        NOT NULL          -- FK logique cases.id
committee_id         UUID                          -- comité source
committee_seal_id    UUID                          -- lien au seal
decision_at          TIMESTAMPTZ NOT NULL          -- horodatage de la décision
zone                 TEXT        NOT NULL          -- zone géographique
currency             TEXT        NOT NULL DEFAULT 'XOF'

item_id              TEXT                          -- canonique (nullable)
alias_raw            TEXT        NOT NULL          -- brut obligatoire
quantity             NUMERIC
unit                 TEXT
price_paid           NUMERIC

supplier_id          TEXT                          -- canonique (nullable)
supplier_name_raw    TEXT        NOT NULL          -- brut obligatoire

source_hashes        JSONB       NOT NULL DEFAULT '{}'  -- traçabilité sources
scoring_meta         JSONB       NOT NULL DEFAULT '{}'  -- méta scoring

snapshot_hash        TEXT        NOT NULL          -- SHA-256 déterministe
created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()

CONSTRAINT uq_snapshot_idempotence UNIQUE (case_id, snapshot_hash)
```

### Neutralité du schéma (NON NÉGOCIABLE)

Les champs suivants sont **interdits** dans `decision_snapshots` :

```
winner, best_offer, rank, ranking, recommendation, recommended,
shortlist, shortlisted, position, score_rank
```

Un test AST et une vérification des colonnes DB garantissent cette interdiction en CI.

### Champs raw obligatoires

`alias_raw` et `supplier_name_raw` sont **NOT NULL** même si les équivalents canoniques
(`item_id`, `supplier_id`) sont absents. Raison : préserver la fidélité au réel au moment
de la capture (INV-9), avant normalisation rétroactive éventuelle.

---

## Hash déterministe (version v1)

```python
SNAPSHOT_HASH_VERSION = "v1"

stable_fields = {
    "_hash_version":     "v1",
    "case_id":           str(snapshot["case_id"]),
    "committee_id":      str(snapshot.get("committee_id") or ""),
    "decision_at":       snapshot["decision_at"].isoformat(),  # ou str()
    "supplier_name_raw": str(snapshot["supplier_name_raw"]),
    "alias_raw":         str(snapshot["alias_raw"]),
    "price_paid":        str(snapshot.get("price_paid") or ""),
    "currency":          str(snapshot.get("currency") or "XOF"),
    "zone":              str(snapshot.get("zone") or ""),
    "quantity":          str(snapshot.get("quantity") or ""),
    "unit":              str(snapshot.get("unit") or ""),
}
payload = json.dumps(stable_fields, sort_keys=True, ensure_ascii=False)
hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

**Propriétés** :
- `json.dumps(sort_keys=True)` → déterminisme garanti
- `_hash_version="v1"` → versionnage explicite
- champs variables (`snapshot_id`, `created_at`) exclus

---

## Atomicité seal + snapshot

L'opération `seal_committee_decision()` est une **transaction unique** :

```
1. Préconditions
2. UPDATE committees SET status='sealed'     ← arme le verrou DB
3. UPDATE committee_decisions SET status='sealed', seal_id=...  ← autorisé par trigger
4. Calcul snapshot + hash + assert_no_forbidden_fields()
5. INSERT decision_snapshots ON CONFLICT DO NOTHING  ← idempotence
6. INSERT committee_events (seal_completed, snapshot_emitted)
```

Si une étape échoue, **tout est rollback**. Pas de snapshot orphelin.

---

## Idempotence

`UNIQUE (case_id, snapshot_hash)` avec `ON CONFLICT DO NOTHING` :

- Un double seal avec les mêmes données → une seule ligne en DB
- Rejouer l'opération → aucun effet de bord

---

## Triggers append-only

```sql
trg_decision_snapshots_append_only  -- BEFORE UPDATE OR DELETE → RAISE EXCEPTION
trg_committee_events_append_only    -- BEFORE UPDATE OR DELETE → RAISE EXCEPTION
```

Testés en CI (T6a) : UPDATE bloqué, DELETE bloqué.

---

## Pont Couche B (#18/#19)

Les snapshots accumulés constituent la matière première du Market Intelligence Signal :

- historique prix payés par zone/item/fournisseur
- tendances sur fenêtre glissante
- détection d'anomalies statistiques (±30% prix moyen)

La Couche B lira ces snapshots en lecture seule. Elle ne les modifiera jamais.

---

## Conséquences

### Positives

- Chaque dossier scellé devient une unité de vérité institutionnelle exploitable
- Le signal marché s'enrichit automatiquement sans action manuelle
- Idempotence = ops tranquilles (replay safe)
- Neutralité = la Couche B ne peut pas "interpréter" ce qui n'existe pas dans le schéma

### Négatives / contraintes

- Tout seal déclenche un snapshot (pas d'option "seal sans snapshot")
- La transaction de seal est légèrement plus longue (atomique)
- L'API n'expose pas de endpoint pour "modifier" un snapshot (c'est voulu)

---

## Décisions alternatives rejetées

| Alternative | Raison du rejet |
|---|---|
| Snapshot émis en dehors de la transaction de seal | Risque de snapshot orphelin si le seal échoue |
| Champs rank/recommendation dans snapshot | Violation Constitution §6.3 + ADR-0011 neutralité |
| Snapshots muables (UPDATE autorisé) | Viole INV-6 (append-only) |
| `case_id` UUID dans #9 | `cases.id` est TEXT — confirmé via sonde #8 |

---

## Fichiers livrés

```
alembic/versions/029_create_decision_snapshots.py
src/couche_a/committee/snapshot.py
tests/decision_snapshot/test_decision_snapshots_append_only.py
tests/decision_snapshot/test_snapshot_created_on_seal.py
tests/decision_snapshot/test_snapshot_schema_neutrality.py
```
