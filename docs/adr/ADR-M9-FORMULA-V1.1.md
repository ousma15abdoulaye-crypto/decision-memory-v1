# ADR-M9-FORMULA-V1.1
# Statut    : DECIDE -- signe AO
# Date      : 2026-03-10
# Decideur  : AO -- Abdoulaye Ousmane
# Remplace  : ADR-M8-FORMULA-V1.1-INTENTION.md

## 1. Formule price_raw -- V1.1

Poids sources (REGLE-22 -- immuables) :
  mercuriale_official : 0.50
  market_survey       : 0.35
  decision_history    : 0.15

Freshness decay :
  0 mois  : 1.00
  1 mois  : 0.90
  2 mois  : 0.75
  3 mois  : 0.55
  > 3 mois: 0.30

IQR outlier rejection multiplicateur : 2.5

Calcul :
  price_raw = sum(W_s * f(age_s) * P_s)
              / sum(W_s * f(age_s))

  Si source absente -> contribution 0 au numerateur
  ET denominateur -> formule s'auto-normalise.
  Pas de redistribution de poids (OPTION B -- REGLE-22).

## 2. Regle freshness par source (probe-confirmed)

  Pour mercuriale_official :
    age_months = (CURRENT_YEAR - year) * 12
    Annee courante -> age=0 -> f=1.00 (poids plein)
    Annee N-1      -> age=12 -> f=0.30 (OLD)
    Justification : mercuriale = reference annuelle officielle
                    fait autorite toute l'annee fiscale.

  Pour market_survey :
    age_months = EXTRACT(MONTH FROM
                   AGE(CURRENT_DATE, date_surveyed))
    Calcul mensuel exact.

  Pour decision_history :
    Meme calcul mensuel si la table existe un jour.
    Actuellement ABSENTE -> contribution 0.

## 3. Ajustements contextuels V1.1

  price_crisis_adj   = price_raw
                       / (1 + markup_pct / 100)
  price_seasonal_adj = price_crisis_adj
                       / (1 + seasonal_dev / 100)
  residual_pct       = (price_raw
                        / price_seasonal_adj - 1)
                       * 100

## 4. Logique d'alerte sur residuel

  IPC4/5 : residuel > 40%  -> CRITICAL
           residuel > 20%  -> WATCH
           sinon           -> CONTEXT_NORMAL

  IPC3   : residuel > 30%  -> WARNING
           sinon           -> CONTEXT_NORMAL

  IPC2   : residuel > 25%  -> WARNING
           sinon           -> SEASONAL_NORMAL

  IPC1/normal :
           residuel > 30%  -> CRITICAL
           residuel > 15%  -> WARNING
           sinon           -> NORMAL

## 5. Role INSTAT dans V1.1

  Source : public.imc_entries
  Colonnes : period_year INT, period_month INT,
             category_raw TEXT, index_value NUMERIC
  Note : category_normalized = NULL (non peuple)
         -> utiliser category_raw

  INSTAT -> seasonal_patterns UNIQUEMENT.
  Pas un 4e poids dans price_raw.
  computation_version = 'v1.0_instat'
  confidence = 0.95
  taxo_l1 = 'Materiaux de construction'

  Regles fusion INSTAT + mercuriales dans seasonal_patterns :
    Les deux coexistent avec computation_version differente.
    Le moteur utilise la ligne a confiance max :
      INSTAT (0.95) > mercuriales (variable)
    Fallback : si INSTAT absent -> mercuriales.

## 6. Propagation zones blanches

  Si zone sans donnees propres :
    Chercher corridor geo_price_corridors
    Prix = prix_zone_source
           * transport_markup * crisis_multiplier
    source_type = 'propagated'
    signal_quality = 'propagated'

## 7. Decisions architecturales probe-confirmed

  market_signals legacy (items.id INTEGER, 15 lignes)
    -> READ-ONLY. Ne pas modifier.
    -> Hors scope M9.

  market_signals_v2 (cree par migration 043)
    -> item_id TEXT -> procurement_dict_items(item_id)
    -> zone_id TEXT -> geo_master(id)
    -> UNIQUE (item_id, zone_id)
    -> formula_version TEXT NOT NULL DEFAULT '1.1'
    -> Toutes colonnes V1.1 a la creation

  mercurials.item_id = UUID, NULL partout
    -> Jointure via mercurials_item_map (table Railway)
    -> mercurials_item_map.item_canonical -> dict_item_id TEXT
    -> 1629 mappings confirmes (97.6% de couverture)
    -> Cree ce soir -- hors migration 043

  decision_history : ABSENTE sur Railway
    -> Poids 0.15 inactif
    -> source_decision_count = 0
    -> Si table creee plus tard : moteur la consomme auto

  signal_computation_log : item_id TEXT
    -> Meme typage que market_signals_v2

## 8. Vecteurs de test figures -- IMMUABLES

  V1 -- contexte normal source unique :
    input  : price=10000 source=mercuriale age=0
             context=normal markup=0 seasonal=0
    output : price_raw=10000
             price_crisis_adj=10000
             price_seasonal_adj=10000
             residual_pct=0.0
             alert=NORMAL

  V2 -- IPC4 Menaka +32% crise +8% saisonnalite :
    input  : price=22500 source=mercuriale age=0
             context=IPC4 markup=32.0 seasonal=8.0
    output : price_raw=22500
             price_crisis_adj=17045.45
             price_seasonal_adj=15782.82
             residual_pct=42.56
             alert=CRITICAL

  V3 -- 3 sources freshness differente :
    input  : [(10000 mercuriale age=0)
              (11000 survey age=2)
              (9500  decision age=1)]
             context=normal markup=0 seasonal=0
    calcul :
      num = 0.50*1.00*10000
            + 0.35*0.75*11000
            + 0.15*0.90*9500
      den = 0.50*1.00 + 0.35*0.75 + 0.15*0.90
      price_raw = num/den
    output : residual_pct=0.0
             alert=NORMAL

  V4 -- IPC3 residuel sous seuil :
    input  : price=15000 source=mercuriale age=0
             context=IPC3 markup=25.0 seasonal=0
    output : price_crisis_adj=12000
             residual_pct=25.0
             alert=CONTEXT_NORMAL (< 30%)

  V5 -- contexte normal residuel > 15% :
    input  : price=12000 source=mercuriale age=0
             context=normal markup=0 seasonal=0
    output : residual_pct=0.0
             alert=NORMAL

## 9. formula_version

  '1.1' -- gravee dans market_signals_v2
  Immuable apres premier INSERT
  Trigger trg_market_signals_formula_immutable
  Modification -> V2.0 + nouvel ADR

## 10. Chemin jointure mercurials -> dict_items

  Via mercurials_item_map (table cree ce soir) :
    SELECT m.price_avg, m.zone_id, m.year
    FROM mercurials m
    JOIN public.mercurials_item_map map
      ON map.item_canonical = m.item_canonical
    WHERE map.dict_item_id = %s
      AND m.zone_id = %s
      AND m.year >= EXTRACT(YEAR FROM CURRENT_DATE) - 1

  Documenter dans M9_RESULT.md :
    "mercurials.item_id UUID NULL partout --
     jointure via mercurials_item_map (1629 mappings).
     Migration index dediee M10A."
