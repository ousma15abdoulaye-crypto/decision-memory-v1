# M9_RESULT -- DONE
# head    : 043_market_signals_v11
# down_rev: 042_market_surveys
# CB-04   : upgrade->downgrade->upgrade OK

## Formule V1.1 -- ADR signe AO
  FORMULA_VERSION : '1.1'
  WEIGHTS : merc=0.50 survey=0.35 decision=0.15
  IQR_MULTIPLIER : 2.5
  Ajustements : crise + saisonnalite actifs
  Vecteurs ADR : 5/5 PASS

## Decisions architecturales probe-confirmed
  market_signals legacy (15 lignes INTEGER) : READ-ONLY intact
  market_signals_v2 : creee -- item_id TEXT -> dict_items
  signal_computation_log : creee
  trigger formula_version immuable : actif
  3 vues : price_series, vendor_price_positioning,
            basket_cost_by_zone

## Regle freshness mercuriale (ADR section 2)
  age_months = (CURRENT_YEAR - year) * 12
  Annee courante -> age=0 -> f=1.00
  Annee N-1      -> age=12 -> f=0.30

## Sources Railway -- etat confirme probe
  mercurials        : 27396 lignes, item_id NULL partout
  mercurials_item_map : 1629 mappings (97.6% couverture)
    Jointure via item_canonical -> dict_item_id TEXT
    Table creee manuellement sur Railway (hors migration 043)
    Migration index dediee : M10A
  market_surveys    : 0 lignes (vide)
  decision_history  : TABLE ABSENTE
    -> source_decision_count = 0
    -> poids 0.15 inactif, formule s'auto-normalise

## Dict Railway -- ingere ce soir
  procurement_dict_items Railway : 1490 items
    Synce depuis local via sync_dict_local_to_railway.py
    default_unit fallback 'unite' pour contrainte NOT NULL

## Seeds locaux
  seasonal_patterns INSTAT  : 648 (imc_entries 810 lignes)
  geo_price_corridors        : 6 (Menaka absent geo_master local)
  seasonal_patterns mercur   : 0 (mercurials_item_map Railway only)

## Railway -- a appliquer (hors scope M9 local)
  Migrations pending : m7_5, m7_6, m7_7, 042, 043
  Operation separee requise.

## CB-01 V2 SEMANTIC_GUARD : PASS
## CB-04 ROLLBACK_GATE : PASS
## Tests : 34 passed, 1 skipped, 0 failed
  TestConstantesADR : 9/9
  TestVecteursADR   : 5/5
  TestUnitaires     : 8/8
  TestDB            : 7/7 + 1 skip (no signals calcules)
## ETA_V1 Q1-Q9 : PASS
## next_milestone : M10A
