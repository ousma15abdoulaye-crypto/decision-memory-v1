# M8_RESULT -- DONE
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

## Schema reel confirme par probe ETAPE 0
  item_id     : TEXT  (cle existante couche_b.procurement_dict_items)
                NOTE : item_id existait avant M8 -- M8 l'utilise en FK
                       PHASE 0 absente -- aucune modification de la table
  zone_id     : TEXT/VARCHAR(50) (geo_master)
  vendor_id   : UUID  (vendors)
  unit_id     : INTEGER (units)
  case_id     : TEXT  (cases)
  source_case_id : TEXT + FK public.cases(id)
  users.id    : INTEGER -> created_by / collected_by / validated_by = INTEGER

## Decisions architecturales gelees
  item_id FK uniforme (pas item_uid) OK
  market_baskets GLOBAL_CORE zero org_id OK
  market_coverage bornee tracked scope OK
  premier refresh sans CONCURRENTLY OK
  index unique cree apres premier refresh OK
  is_bidirectional absent OK
  price_series absent -> M9 OK
  downgrade() complet -- aucune modif procurement_dict_items OK
  source_case_id TEXT + FK cases(id) OK

## CB-01 : PASS (5/5 fichiers OK)
## CB-08 : total=610 t1=179 t2=431 t3=0 mode=FULL
## Seeds : 6 contextes FEWS Mali ok=6 skip=0 err=0
##         items=45 zones=6 baskets=3/3 cardinalite=270
## Tests : 39 passed, 1 skipped (0 failed)
## Engine: AUCUN (market_signals preexistant hors M8)
## INSTAT: present -> seasonal_patterns M9
## ETA_V1 Q1-Q9 : PASS
## next_milestone : M9
