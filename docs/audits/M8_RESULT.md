# M8_RESULT — DONE
## head    : 042_market_surveys
## down_rev: m7_7_genome_stable
## CB-04   : upgrade -> downgrade -> upgrade OK

## Tables : 13
  GLOBAL_CORE  : tracked_market_items,
                 tracked_market_zones, market_baskets,
                 market_basket_items,
                 zone_context_registry, zone_context_audit,
                 seasonal_patterns, geo_price_corridors
  TENANT_SCOPED: survey_campaigns, survey_campaign_items,
                 survey_campaign_zones, market_surveys,
                 price_anomaly_alerts
  MATVIEW      : market_coverage (bornee scope tracked)

## Triggers : 6 exacts
  trg_compute_price_per_unit
  trg_zone_context_no_overlap
  trg_zone_context_audit_log
  trg_zone_context_audit_append_only
  trg_market_survey_immutable_validated
  trg_market_survey_flag_duplicate

## Adaptations schema reel appliquees
  users.id  = INTEGER  -> created_by / collected_by / validated_by = INTEGER
  units.id  = INTEGER  -> unit_id = INTEGER
  cases.id  = TEXT     -> case_id = TEXT
  geo_master.id = VARCHAR (pas UUID) -> zone_id = TEXT partout
  procurement_dict_items sans item_uid -> PHASE 0 ajoute item_uid UUID

## Decisions architecturales gelees
  market_baskets GLOBAL_CORE zero org_id OK
  market_coverage bornee tracked scope OK
  premier refresh sans CONCURRENTLY OK
  index unique cree apres premier refresh OK
  item_uid FK uniforme OK
  is_bidirectional absent OK
  price_series absent -> M9 OK
  downgrade() complet OK

## CB-01 : PASS (5/5 fichiers OK)
## CB-08 : total=610 t1=179 t2=431 t3=0 mode=FULL
## Seeds : 6 contextes FEWS Mali ok=6 skip=0 err=0
##         items=47 zones=6 baskets=3/3 cardinalite=282
## Tests : 39 passed, 1 skipped (0 failed)
## Engine: AUCUN (market_signals preexistant hors M8)
## INSTAT: present -> seasonal_patterns M9
## ETA_V1 Q1-Q9 : PASS
## next_milestone : M9
