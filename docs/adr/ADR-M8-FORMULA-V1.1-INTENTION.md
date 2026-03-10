# ADR-M8-FORMULA-V1.1-INTENTION

**Statut** : INTENTION — décision reportée à M9 après ADR dédié  
**Date** : 2026-03-10  
**Auteur** : AO — Abdoulaye Ousmane  
**Branche** : feat/m8-market-intelligence  

---

## Contexte

M8 pose la fondation de l'intelligence marché : tables de collecte,
scope suivi, contextes de zone. La formule de signal de prix (V1.1)
n'est pas implémentée en M8 — elle est documentée ici comme intention
architecturale pour M9.

## Décision reportée

La formule signal V1.1 n'est **pas** créée en M8.

Raisons :
- Nécessite `market_signals` (table M9)
- Nécessite `price_series` (vue M9)
- Nécessite `seasonal_patterns` alimentées (données INSTAT via M9)
- Nécessite ADR dédié sur méthode de calcul baseline

## Intention architecturale V1.1

La formule cible (M9) devra calculer :

```
signal_pct = (prix_observé - baseline_contextualisé) / baseline_contextualisé × 100

baseline_contextualisé = prix_référence
                       × (1 + structural_markup_pct / 100)
                       × facteur_saisonnier_mensuel
```

Où :
- `prix_référence` = médiane des surveys validés sur 90 jours, zone Bamako
- `structural_markup_pct` = `zone_context_registry.structural_markup_pct`
- `facteur_saisonnier_mensuel` = `seasonal_patterns.historical_deviation_pct`

## Invariants posés en M8 (non négociables pour M9)

| Invariant | Valeur |
|-----------|--------|
| Colonne FK items | `item_uid` uniquement — jamais `item_id` |
| Baskets système | `market_baskets` GLOBAL_CORE — zéro `org_id` |
| Coverage matview | bornée `tracked_market_items × tracked_market_zones` |
| Premier refresh | sans `CONCURRENTLY` — index unique créé après |
| `is_bidirectional` | absent de `geo_price_corridors` — deux lignes = deux sens |
| `collection_method` | `mercuriale` interdit dans `market_surveys` |
| `market_signals` | absent en M8 — créé en M9 uniquement |

## Hors scope M8 — reporté M9

- `market_signals`
- `compute_signal`
- `price_series`
- `vendor_price_positioning`
- `basket_cost_by_zone`
- `tenant_market_baskets`
- Refresh automatique matview
- Formule signal V1.0 et V1.1

## Références

- ETA_V1 Section 2 — positionnement multi-secteur
- FEWS NET Mali Feb 2026 — contextes seedés
- MRD-6 DONE — tag mrd-6-done
