# ADR-M5-FIX-001 — Correction type market_signals.vendor_id

## Statut
ACCEPTÉ

## Date
2026-03-03

## Auteur
CTO — Abdoulaye Ousmane

## Contexte

La migration 005_add_couche_b.py a créé market_signals.vendor_id
en type INTEGER avec FK vers vendors(id).

Le sprint M5-PRE a supprimé cette FK lors du DROP de vendors legacy.
État résiduel : market_signals.vendor_id = INTEGER sans FK.

Le schéma cible DMS V4.1.0 définit vendors.id en UUID.
Ce mismatch rend impossible toute jointure cohérente en M9.
La correction sur table vide est sans risque.
La correction sur table avec données réelles est risquée.

### Schéma réel market_signals au moment du fix (probe P1 · 2026-03-03)

```
id          INTEGER  NOT NULL  PK
vendor_id   INTEGER  nullable  (sans FK · sans index nommé idx_signals_vendor)
item_id     INTEGER  nullable  FK → items(id)
zone_id     VARCHAR  nullable  FK → geo_master(id)
price       NUMERIC  nullable
quantity    NUMERIC  nullable
unit_id     INTEGER  nullable  FK → units(id)
observed_at TEXT     NOT NULL
created_at  TEXT     NOT NULL
```

Note : les colonnes signal_quality · formula_version · data_points
définies dans le freeze V4.1.0 n'existent pas encore.
Elles seront créées en M9 (Market Signal).
Cette migration ne les touche pas.

## Décision

Corriger market_signals.vendor_id :
  TYPE    : INTEGER → UUID
  FK      : documentée dans l'ADR · non créée dans la migration Alembic
  TIMING  : avant M5 · sur table vide confirmée par probe
  MÉTHODE : ALTER COLUMN · SQL brut via op.execute() · idempotent

Motif FK hors migration :
  market_signals est protégée append-only.
  PostgreSQL déclenche SELECT FOR KEY SHARE sur market_signals
  lors de tout DELETE vendors, quelle que soit l'action FK
  (RESTRICT · SET NULL · CASCADE · NO ACTION).
  Ce verrou est bloqué par la protection append-only locale.
  La FK est incompatible avec cette protection en environnement local.
  Elle sera appliquée manuellement sur Railway prod
  via scripts/apply_fk_prod.py après déploiement.

Contrainte logique (non enforced en dev, enforced en prod) :
  market_signals.vendor_id REFERENCES vendors(id) ON DELETE RESTRICT

## Alternatives écartées

Option A — Attendre M9 :
  Écarté : migration de type sur table avec données = risque corruption

Option B — DROP + RECREATE market_signals :
  Écarté : blast radius excessif · ALTER COLUMN suffit sur table vide

Option C — Conserver INTEGER + cast applicatif :
  Écarté : dette silencieuse · contraire à la doctrine source de vérité DB

## Conséquences

Positives :
  market_signals.vendor_id = UUID · cohérent avec vendors.id
  FK recréée · intégrité référentielle restaurée
  M9 peut joindre market_signals → vendors sans cast

Risques :
  Si market_signals n'est pas vide en prod → migration bloquée par garde
  → arbitrage CTO obligatoire avant toute action

## Chemin ADR
docs/adr/ (RÈGLE-ORG-11 · singulier · invariant)
