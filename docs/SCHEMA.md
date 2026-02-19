# Schéma Base de Données — Decision Memory System V3.3.2

**Référence :** Constitution V3.3.2 (freeze actif et opposable)
**Migration :** `alembic/versions/0001_init_schema.py`
**Date :** 2026-02-19
**Phase :** Zéro — Milestone M-SCHEMA-CORE

---

## Vue d'ensemble

6 tables — séparation stricte Couche A / Couche B (ADR-0003 §3.1)

| Table | Couche | Rôle |
|-------|--------|------|
| `suppliers` | Partagée | Référentiel fournisseurs résolus |
| `dictionary` | Couche A | Dictionnaire Sahel — 9 familles min |
| `offers` | Couche A | Offres brutes ingérées |
| `structured_data` | Couche A | Offres normalisées (JSONB) |
| `scores` | Couche A | Scores calculés — read-only Couche B |
| `market_data` | Couche B | Mémoire marché — append-only |

---

## Tables Couche A

### `suppliers`
| Colonne | Type | Contrainte |
|---------|------|------------|
| `id` | UUID | PK |
| `canonical_name` | VARCHAR(255) | NOT NULL, UNIQUE |
| `aliases` | JSONB | NOT NULL, default `[]` |
| `country` | VARCHAR(100) | nullable |
| `created_at` | TIMESTAMPTZ | NOT NULL |
| `updated_at` | TIMESTAMPTZ | NOT NULL |

### `dictionary`
Dictionnaire Sahel — référentiel canonique de normalisation.

**9 familles obligatoires :**
`carburants` · `construction_liants` · `construction_agregats` ·
`construction_fer` · `vehicules` · `informatique` ·
`alimentation` · `medicaments` · `equipements`

| Colonne | Type | Contrainte |
|---------|------|------------|
| `id` | UUID | PK |
| `canonical_name` | VARCHAR(255) | NOT NULL, UNIQUE |
| `family` | VARCHAR(100) | NOT NULL |
| `unit` | VARCHAR(50) | NOT NULL |
| `aliases` | JSONB | NOT NULL, default `[]` — min 3 par item |
| `created_at` | TIMESTAMPTZ | NOT NULL |

### `offers`
| Colonne | Type | Contrainte |
|---------|------|------------|
| `id` | UUID | PK |
| `process_id` | VARCHAR(255) | NOT NULL, INDEX |
| `supplier_id` | UUID | FK → suppliers |
| `raw_filename` | VARCHAR(500) | NOT NULL |
| `raw_content` | TEXT | nullable |
| `status` | VARCHAR(50) | NOT NULL, default `pending` |
| `created_at` | TIMESTAMPTZ | NOT NULL |

### `structured_data`
Offres normalisées selon dictionnaire Sahel.
Structure JSONB conforme à Constitution V3.3.2 §4.

| Colonne | Type | Contrainte |
|---------|------|------------|
| `id` | UUID | PK |
| `offer_id` | UUID | FK → offers, NOT NULL |
| `data` | JSONB | NOT NULL, default `{}` |
| `normalisation_version` | VARCHAR(50) | NOT NULL, default `v3.3.2` |
| `created_at` | TIMESTAMPTZ | NOT NULL |

### `scores`
Scores calculés exclusivement par la Couche A.
**La Couche B ne peut jamais écrire dans cette table.**
(Constitution V3.3.2 §7 + ADR-0003 §3.1)

| Colonne | Type | Contrainte |
|---------|------|------------|
| `id` | UUID | PK |
| `offer_id` | UUID | FK → offers, NOT NULL |
| `essentials` | NUMERIC(5,2) | NOT NULL |
| `capacity` | NUMERIC(5,2) | NOT NULL |
| `commercial` | NUMERIC(5,2) | NOT NULL |
| `sustainability` | NUMERIC(5,2) | NOT NULL |
| `total` | NUMERIC(5,2) | NOT NULL |
| `computed_at` | TIMESTAMPTZ | NOT NULL |
| `constitution_version` | VARCHAR(50) | NOT NULL, default `v3.3.2` |

---

## Table Couche B

### `market_data`
Mémoire marché — **append-only** (Invariant 9 Constitution V3.3.2).
Aucune opération UPDATE ou DELETE autorisée.
La Couche B lit cette table. La Couche A ne la lit jamais.

| Colonne | Type | Contrainte |
|---------|------|------------|
| `id` | UUID | PK |
| `item_canonical` | VARCHAR(255) | NOT NULL, INDEX |
| `family` | VARCHAR(100) | NOT NULL |
| `unit` | VARCHAR(50) | NOT NULL |
| `unit_price` | NUMERIC(12,4) | NOT NULL |
| `currency` | VARCHAR(10) | NOT NULL, default `XOF` |
| `country` | VARCHAR(100) | nullable |
| `zone` | VARCHAR(100) | nullable |
| `source_process_id` | VARCHAR(255) | nullable |
| `supplier_id` | UUID | FK → suppliers |
| `observed_at` | TIMESTAMPTZ | NOT NULL |
| `created_at` | TIMESTAMPTZ | NOT NULL |

---

## Index

| Nom | Table | Colonnes | Raison |
|-----|-------|----------|--------|
| `ix_offers_process_id` | offers | process_id | Recherche par appel d'offres |
| `ix_scores_offer_id` | scores | offer_id | Jointure scoring |
| `ix_market_data_item` | market_data | item_canonical, family | Recherche prix marché |
| `ix_dictionary_family` | dictionary | family | Filtrage par famille Sahel |

---

## Invariants schéma

- **Invariant 9 :** `market_data` est append-only — pas de DELETE, pas d'UPDATE
- **Séparation A/B :** `scores` est en écriture Couche A uniquement
- **Traçabilité :** Toutes les tables ont `created_at` horodaté
- **Versionnage :** `scores.constitution_version` et
  `structured_data.normalisation_version` tracent la version active

---

*© 2026 — Decision Memory System — Schéma V3.3.2*
