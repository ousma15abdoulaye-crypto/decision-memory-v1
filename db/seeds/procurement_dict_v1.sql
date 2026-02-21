-- procurement_dict_v1.sql
-- Seed versionné M-NORMALISATION-ITEMS (ADR-0002 §2.1)
-- 9 familles mandatory Sahel, items + aliases + conversions
-- Idempotent : ON CONFLICT DO NOTHING partout

-- ============================================================
-- FAMILLES (9 mandatory ADR-0002 §2.1)
-- ============================================================
INSERT INTO couche_b.procurement_dict_families (family_id, label_fr, criticite) VALUES
  ('carburants',              'Carburants et lubrifiants',         'CRITIQUE'),
  ('construction_liants',     'Construction — liants',             'CRITIQUE'),
  ('construction_agregats',   'Construction — agrégats',           'HAUTE'),
  ('construction_fer',        'Construction — ferraillage',        'HAUTE'),
  ('vehicules',               'Véhicules et engins',               'CRITIQUE'),
  ('informatique',            'Informatique et télécoms',          'MOYENNE'),
  ('alimentation',            'Alimentation et vivres',            'CRITIQUE'),
  ('medicaments',             'Médicaments et consommables',       'CRITIQUE'),
  ('equipements',             'Équipements et matériels divers',   'HAUTE')
ON CONFLICT (family_id) DO NOTHING;

-- ============================================================
-- UNITÉS
-- ============================================================
INSERT INTO couche_b.procurement_dict_units (unit_id, label_fr, unit_kind) VALUES
  ('litre',   'Litre',             'volume'),
  ('m3',      'Mètre cube',        'volume'),
  ('kg',      'Kilogramme',        'masse'),
  ('tonne',   'Tonne',             'masse'),
  ('ml',      'Millilitre',        'volume'),
  ('unite',   'Unité',             'quantite'),
  ('boite',   'Boîte',             'conditionnement'),
  ('sac_50kg','Sac 50 kg',         'conditionnement'),
  ('barre',   'Barre',             'quantite'),
  ('rouleau', 'Rouleau',           'quantite'),
  ('feuille', 'Feuille',           'quantite'),
  ('flacon',  'Flacon',            'conditionnement'),
  ('comprime','Comprimé',          'quantite'),
  ('voyage',  'Voyage (transport)','transport'),
  ('heure',   'Heure',             'temps')
ON CONFLICT (unit_id) DO NOTHING;

-- ============================================================
-- ITEMS — carburants (6 items)
-- ============================================================
INSERT INTO couche_b.procurement_dict_items (item_id, family_id, label_fr, label_en, default_unit, active) VALUES
  ('gasoil',            'carburants', 'Gasoil',                      'Diesel fuel',        'litre', TRUE),
  ('essence_super',     'carburants', 'Essence super',               'Premium petrol',     'litre', TRUE),
  ('jet_a1',            'carburants', 'Carburant aviation Jet A-1',  'Jet A-1 fuel',       'litre', TRUE),
  ('huile_moteur_15w40','carburants', 'Huile moteur 15W40',          'Engine oil 15W40',   'litre', TRUE),
  ('huile_hydraulique', 'carburants', 'Huile hydraulique',           'Hydraulic oil',      'litre', TRUE),
  ('graisse_auto',      'carburants', 'Graisse automobile multi-usage','Auto grease',       'kg',    TRUE)
ON CONFLICT (item_id) DO NOTHING;

-- ITEMS — construction_liants (6 items)
INSERT INTO couche_b.procurement_dict_items (item_id, family_id, label_fr, label_en, default_unit, active) VALUES
  ('ciment_cpa_42_5',       'construction_liants', 'Ciment CPA 42.5',         'Portland cement 42.5',  'sac_50kg', TRUE),
  ('ciment_cpj_35',         'construction_liants', 'Ciment CPJ 35',           'Portland cement 35',    'sac_50kg', TRUE),
  ('chaux_vive',            'construction_liants', 'Chaux vive',              'Quicklime',             'sac_50kg', TRUE),
  ('platre_batiment',       'construction_liants', 'Plâtre bâtiment',         'Building plaster',      'sac_50kg', TRUE),
  ('colle_carrelage',       'construction_liants', 'Colle carrelage',         'Tile adhesive',         'sac_50kg', TRUE),
  ('enduit_facade',         'construction_liants', 'Enduit façade',           'Facade render',         'sac_50kg', TRUE)
ON CONFLICT (item_id) DO NOTHING;

-- ITEMS — construction_agregats (6 items)
INSERT INTO couche_b.procurement_dict_items (item_id, family_id, label_fr, label_en, default_unit, active) VALUES
  ('sable_fleuve_7m3',      'construction_agregats', 'Sable du fleuve (7m3)',   'River sand 7m3',        'voyage', TRUE),
  ('gravier_15_25',         'construction_agregats', 'Gravier 15/25',           'Gravel 15/25',          'voyage', TRUE),
  ('laterite',              'construction_agregats', 'Latérite',                'Laterite',              'voyage', TRUE),
  ('tout_venant',           'construction_agregats', 'Tout-venant',             'All-in aggregate',      'voyage', TRUE),
  ('pave_beton_10x20',      'construction_agregats', 'Pavé béton 10x20',        'Concrete paver 10x20',  'unite',  TRUE),
  ('parpaing_15x20x40',     'construction_agregats', 'Parpaing 15x20x40',       'Hollow block 15x20x40', 'unite',  TRUE)
ON CONFLICT (item_id) DO NOTHING;

-- ITEMS — construction_fer (5 items)
INSERT INTO couche_b.procurement_dict_items (item_id, family_id, label_fr, label_en, default_unit, active) VALUES
  ('fer_ha_12_barre_12m',   'construction_fer', 'Fer HA 12mm barre 12m',   'Rebar HA 12mm 12m',   'barre', TRUE),
  ('fer_ha_10_barre_12m',   'construction_fer', 'Fer HA 10mm barre 12m',   'Rebar HA 10mm 12m',   'barre', TRUE),
  ('fer_ha_8_barre_12m',    'construction_fer', 'Fer HA 8mm barre 12m',    'Rebar HA 8mm 12m',    'barre', TRUE),
  ('tole_ondule_zinc',      'construction_fer', 'Tôle ondulée zinc',        'Corrugated zinc sheet','feuille',TRUE),
  ('fil_de_fer_recuit',     'construction_fer', 'Fil de fer recuit',        'Annealed wire',       'rouleau',TRUE)
ON CONFLICT (item_id) DO NOTHING;

-- ITEMS — vehicules (5 items)
INSERT INTO couche_b.procurement_dict_items (item_id, family_id, label_fr, label_en, default_unit, active) VALUES
  ('toyota_land_cruiser_hzj78','vehicules', 'Toyota Land Cruiser 4x4 HZJ78', 'Toyota LC HZJ78',  'unite', TRUE),
  ('toyota_hilux_pick_up',     'vehicules', 'Toyota Hilux Pick-up',          'Toyota Hilux',     'unite', TRUE),
  ('nissan_patrol_4x4',        'vehicules', 'Nissan Patrol 4x4',             'Nissan Patrol',    'unite', TRUE),
  ('moto_honda_cg125',         'vehicules', 'Moto Honda CG125',              'Honda CG125',      'unite', TRUE),
  ('groupe_electrogene_20kva', 'vehicules', 'Groupe électrogène 20 KVA',     'Generator 20 KVA', 'unite', TRUE)
ON CONFLICT (item_id) DO NOTHING;

-- ITEMS — informatique (5 items)
INSERT INTO couche_b.procurement_dict_items (item_id, family_id, label_fr, label_en, default_unit, active) VALUES
  ('laptop_core_i5',       'informatique', 'Ordinateur portable Core i5',    'Laptop Core i5',       'unite', TRUE),
  ('imprimante_laser_a4',  'informatique', 'Imprimante laser A4',             'A4 laser printer',     'unite', TRUE),
  ('onduleur_1kva',        'informatique', 'Onduleur 1 KVA',                  'UPS 1 KVA',            'unite', TRUE),
  ('telephone_portable',   'informatique', 'Téléphone portable',              'Mobile phone',         'unite', TRUE),
  ('tablette_android',     'informatique', 'Tablette Android',                'Android tablet',       'unite', TRUE)
ON CONFLICT (item_id) DO NOTHING;

-- ITEMS — alimentation (6 items)
INSERT INTO couche_b.procurement_dict_items (item_id, family_id, label_fr, label_en, default_unit, active) VALUES
  ('riz_brise_25kg',       'alimentation', 'Riz brisé sac 25kg',              'Broken rice 25kg',     'sac_50kg', TRUE),
  ('huile_vegetale_5l',    'alimentation', 'Huile végétale bidon 5L',         'Cooking oil 5L',       'unite',    TRUE),
  ('farine_ble_50kg',      'alimentation', 'Farine de blé sac 50kg',          'Wheat flour 50kg',     'sac_50kg', TRUE),
  ('sel_iode_1kg',         'alimentation', 'Sel iodé 1kg',                    'Iodized salt 1kg',     'kg',       TRUE),
  ('lait_poudre_25kg',     'alimentation', 'Lait en poudre sac 25kg',         'Powdered milk 25kg',   'sac_50kg', TRUE),
  ('haricots_blancs_50kg', 'alimentation', 'Haricots blancs sac 50kg',        'White beans 50kg',     'sac_50kg', TRUE)
ON CONFLICT (item_id) DO NOTHING;

-- ITEMS — medicaments (6 items)
INSERT INTO couche_b.procurement_dict_items (item_id, family_id, label_fr, label_en, default_unit, active) VALUES
  ('paracetamol_500mg_boite_100cp', 'medicaments', 'Paracétamol 500mg boîte 100cp',  'Paracetamol 500mg 100tab', 'boite',   TRUE),
  ('amoxicilline_500mg_boite_100',  'medicaments', 'Amoxicilline 500mg boîte 100',   'Amoxicillin 500mg 100tab', 'boite',   TRUE),
  ('sro_sachet',                    'medicaments', 'SRO sachet (sel de réhydratation)','ORS sachet',             'unite',   TRUE),
  ('eau_oxygenee_1l',               'medicaments', 'Eau oxygénée 1L',                 'Hydrogen peroxide 1L',   'flacon',  TRUE),
  ('gants_latex_boite_100',         'medicaments', 'Gants latex boîte 100',           'Latex gloves box 100',   'boite',   TRUE),
  ('seringue_5ml_boite_100',        'medicaments', 'Seringue 5ml boîte 100',          'Syringe 5ml box 100',    'boite',   TRUE)
ON CONFLICT (item_id) DO NOTHING;

-- ITEMS — equipements (6 items)
INSERT INTO couche_b.procurement_dict_items (item_id, family_id, label_fr, label_en, default_unit, active) VALUES
  ('tente_familiale_4x4',  'equipements', 'Tente familiale 4x4',             'Family tent 4x4',      'unite', TRUE),
  ('bache_pe_4x6',         'equipements', 'Bâche PE 4x6m',                   'PE tarpaulin 4x6m',    'unite', TRUE),
  ('jerrican_20l',         'equipements', 'Jerrican plastique 20L',          'Plastic jerrycan 20L', 'unite', TRUE),
  ('seau_plastique_20l',   'equipements', 'Seau plastique 20L avec couvercle','Plastic bucket 20L',  'unite', TRUE),
  ('kit_hygiene_menage',   'equipements', 'Kit hygiène ménage standard',     'Household hygiene kit','unite', TRUE),
  ('natte_de_couchage',    'equipements', 'Natte de couchage',               'Sleeping mat',         'unite', TRUE)
ON CONFLICT (item_id) DO NOTHING;

-- ============================================================
-- ALIASES — seed_sahel (mandatory ADR-0002 §2.1)
-- ============================================================

-- gasoil
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('gasoil', 'gasoil',      'gasoil',      'seed_sahel'),
  ('gasoil', 'gas oil',     'gas oil',     'seed_sahel'),
  ('gasoil', 'diesel',      'diesel',      'seed_sahel'),
  ('gasoil', 'gaz oil',     'gaz oil',     'seed_sahel'),
  ('gasoil', 'GO',          'go',          'seed_sahel')
ON CONFLICT (normalized_alias) DO NOTHING;

-- ciment CPA 42.5
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('ciment_cpa_42_5', 'ciment CPA 42.5', 'ciment cpa 42.5', 'seed_sahel'),
  ('ciment_cpa_42_5', 'ciment 42.5',     'ciment 42.5',     'seed_sahel'),
  ('ciment_cpa_42_5', 'CPA42,5',         'cpa42,5',         'seed_sahel'),
  ('ciment_cpa_42_5', 'CPJ 42.5',        'cpj 42.5',        'seed_sahel')
ON CONFLICT (normalized_alias) DO NOTHING;

-- fer HA 12
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('fer_ha_12_barre_12m', 'fer HA 12mm barre 12m', 'fer ha 12mm barre 12m', 'seed_sahel'),
  ('fer_ha_12_barre_12m', 'rond tor 12',            'rond tor 12',           'seed_sahel'),
  ('fer_ha_12_barre_12m', 'HA12',                   'ha12',                  'seed_sahel'),
  ('fer_ha_12_barre_12m', 'tor 12',                 'tor 12',                'seed_sahel')
ON CONFLICT (normalized_alias) DO NOTHING;

-- sable fleuve
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('sable_fleuve_7m3', 'sable fleuve 7m3',   'sable fleuve 7m3',   'seed_sahel'),
  ('sable_fleuve_7m3', 'sable du fleuve',    'sable du fleuve',    'seed_sahel'),
  ('sable_fleuve_7m3', 'sable voyage',       'sable voyage',       'seed_sahel')
ON CONFLICT (normalized_alias) DO NOTHING;

-- toyota land cruiser
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('toyota_land_cruiser_hzj78', 'Toyota Land Cruiser 4x4 HZJ78', 'toyota land cruiser 4x4 hzj78', 'seed_sahel'),
  ('toyota_land_cruiser_hzj78', 'Land Cruiser 78',               'land cruiser 78',               'seed_sahel'),
  ('toyota_land_cruiser_hzj78', 'LC 78',                         'lc 78',                         'seed_sahel')
ON CONFLICT (normalized_alias) DO NOTHING;

-- paracetamol
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('paracetamol_500mg_boite_100cp', 'paracetamol 500mg comprimé', 'paracetamol 500mg comprime', 'seed_sahel'),
  ('paracetamol_500mg_boite_100cp', 'doliprane 500',              'doliprane 500',              'seed_sahel'),
  ('paracetamol_500mg_boite_100cp', 'efferalgan 500',             'efferalgan 500',             'seed_sahel')
ON CONFLICT (normalized_alias) DO NOTHING;

-- ============================================================
-- ALIASES — seed_min (couverture minimale, 3 aliases/item)
-- ============================================================

-- essence_super
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('essence_super', 'essence super',   'essence super',   'seed_min'),
  ('essence_super', 'super',           'super',           'seed_min'),
  ('essence_super', 'essence',         'essence',         'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- jet_a1
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('jet_a1', 'jet A-1',   'jet a-1',   'seed_min'),
  ('jet_a1', 'jet A1',    'jet a1',    'seed_min'),
  ('jet_a1', 'kérosène',  'kerosene',  'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- huile_moteur_15w40
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('huile_moteur_15w40', 'huile moteur 15W40', 'huile moteur 15w40', 'seed_min'),
  ('huile_moteur_15w40', 'huile 15W40',        'huile 15w40',        'seed_min'),
  ('huile_moteur_15w40', 'huile moteur',        'huile moteur',       'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- huile_hydraulique
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('huile_hydraulique', 'huile hydraulique', 'huile hydraulique', 'seed_min'),
  ('huile_hydraulique', 'hydraulique',       'hydraulique',       'seed_min'),
  ('huile_hydraulique', 'huile HV',          'huile hv',          'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- graisse_auto
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('graisse_auto', 'graisse auto',         'graisse auto',        'seed_min'),
  ('graisse_auto', 'graisse multi-usage',  'graisse multi-usage', 'seed_min'),
  ('graisse_auto', 'graisse automobile',   'graisse automobile',  'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- ciment_cpj_35
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('ciment_cpj_35', 'ciment CPJ 35',   'ciment cpj 35',   'seed_min'),
  ('ciment_cpj_35', 'CPJ35',           'cpj35',           'seed_min'),
  ('ciment_cpj_35', 'ciment 35',       'ciment 35',       'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- chaux_vive
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('chaux_vive', 'chaux vive',   'chaux vive',   'seed_min'),
  ('chaux_vive', 'chaux',        'chaux',        'seed_min'),
  ('chaux_vive', 'quicklime',    'quicklime',    'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- platre_batiment
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('platre_batiment', 'plâtre bâtiment',  'platre batiment',  'seed_min'),
  ('platre_batiment', 'plâtre',           'platre',           'seed_min'),
  ('platre_batiment', 'plaster',          'plaster',          'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- colle_carrelage
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('colle_carrelage', 'colle carrelage',     'colle carrelage',     'seed_min'),
  ('colle_carrelage', 'colle à carrelage',   'colle a carrelage',   'seed_min'),
  ('colle_carrelage', 'tile adhesive',        'tile adhesive',       'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- enduit_facade
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('enduit_facade', 'enduit façade',   'enduit facade',   'seed_min'),
  ('enduit_facade', 'enduit',          'enduit',          'seed_min'),
  ('enduit_facade', 'facade render',   'facade render',   'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- gravier_15_25
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('gravier_15_25', 'gravier 15/25',   'gravier 15/25',   'seed_min'),
  ('gravier_15_25', 'gravier',         'gravier',         'seed_min'),
  ('gravier_15_25', 'caillasse',       'caillasse',       'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- laterite
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('laterite', 'latérite',         'laterite',          'seed_min'),
  ('laterite', 'latérite rouge',   'laterite rouge',    'seed_min'),
  ('laterite', 'latérite voyage',  'laterite voyage',   'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- tout_venant
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('tout_venant', 'tout-venant',   'tout-venant',   'seed_min'),
  ('tout_venant', 'tout venant',   'tout venant',   'seed_min'),
  ('tout_venant', 'all-in',        'all-in',        'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- pave_beton_10x20
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('pave_beton_10x20', 'pavé béton 10x20',  'pave beton 10x20',  'seed_min'),
  ('pave_beton_10x20', 'pavé 10x20',        'pave 10x20',        'seed_min'),
  ('pave_beton_10x20', 'paving stone',       'paving stone',      'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- parpaing_15x20x40
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('parpaing_15x20x40', 'parpaing 15x20x40',   'parpaing 15x20x40',   'seed_min'),
  ('parpaing_15x20x40', 'parpaing',             'parpaing',             'seed_min'),
  ('parpaing_15x20x40', 'hollow block',         'hollow block',         'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- fer_ha_10_barre_12m
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('fer_ha_10_barre_12m', 'fer HA 10mm barre 12m', 'fer ha 10mm barre 12m', 'seed_min'),
  ('fer_ha_10_barre_12m', 'rond tor 10',            'rond tor 10',           'seed_min'),
  ('fer_ha_10_barre_12m', 'HA10',                   'ha10',                  'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- fer_ha_8_barre_12m
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('fer_ha_8_barre_12m', 'fer HA 8mm barre 12m', 'fer ha 8mm barre 12m', 'seed_min'),
  ('fer_ha_8_barre_12m', 'rond tor 8',            'rond tor 8',           'seed_min'),
  ('fer_ha_8_barre_12m', 'HA8',                   'ha8',                  'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- tole_ondule_zinc
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('tole_ondule_zinc', 'tôle ondulée zinc', 'tole ondulee zinc', 'seed_min'),
  ('tole_ondule_zinc', 'tôle ondulée',      'tole ondulee',      'seed_min'),
  ('tole_ondule_zinc', 'zinc sheet',        'zinc sheet',        'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- fil_de_fer_recuit
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('fil_de_fer_recuit', 'fil de fer recuit', 'fil de fer recuit', 'seed_min'),
  ('fil_de_fer_recuit', 'fil de fer',        'fil de fer',        'seed_min'),
  ('fil_de_fer_recuit', 'fil recuit',        'fil recuit',        'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- toyota_hilux_pick_up
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('toyota_hilux_pick_up', 'Toyota Hilux',       'toyota hilux',       'seed_min'),
  ('toyota_hilux_pick_up', 'Hilux Pick-up',      'hilux pick-up',      'seed_min'),
  ('toyota_hilux_pick_up', 'Hilux',              'hilux',              'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- nissan_patrol_4x4
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('nissan_patrol_4x4', 'Nissan Patrol',    'nissan patrol',    'seed_min'),
  ('nissan_patrol_4x4', 'Patrol 4x4',       'patrol 4x4',       'seed_min'),
  ('nissan_patrol_4x4', 'GR Patrol',        'gr patrol',        'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- moto_honda_cg125
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('moto_honda_cg125', 'Moto Honda CG125', 'moto honda cg125', 'seed_min'),
  ('moto_honda_cg125', 'Honda CG125',      'honda cg125',      'seed_min'),
  ('moto_honda_cg125', 'CG125',            'cg125',            'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- groupe_electrogene_20kva
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('groupe_electrogene_20kva', 'groupe électrogène 20 KVA', 'groupe electrogene 20 kva', 'seed_min'),
  ('groupe_electrogene_20kva', 'groupe 20 KVA',             'groupe 20 kva',             'seed_min'),
  ('groupe_electrogene_20kva', 'genset 20 kva',             'genset 20 kva',             'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- laptop_core_i5
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('laptop_core_i5', 'ordinateur portable Core i5', 'ordinateur portable core i5', 'seed_min'),
  ('laptop_core_i5', 'laptop i5',                   'laptop i5',                   'seed_min'),
  ('laptop_core_i5', 'PC portable i5',              'pc portable i5',              'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- imprimante_laser_a4
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('imprimante_laser_a4', 'imprimante laser A4', 'imprimante laser a4', 'seed_min'),
  ('imprimante_laser_a4', 'imprimante laser',    'imprimante laser',    'seed_min'),
  ('imprimante_laser_a4', 'laser printer',       'laser printer',       'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- onduleur_1kva
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('onduleur_1kva', 'onduleur 1 KVA', 'onduleur 1 kva', 'seed_min'),
  ('onduleur_1kva', 'onduleur 1kva',  'onduleur 1kva',  'seed_min'),
  ('onduleur_1kva', 'UPS 1 KVA',      'ups 1 kva',      'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- telephone_portable
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('telephone_portable', 'téléphone portable', 'telephone portable', 'seed_min'),
  ('telephone_portable', 'mobile phone',       'mobile phone',       'seed_min'),
  ('telephone_portable', 'GSM',                'gsm',                'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- tablette_android
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('tablette_android', 'tablette Android', 'tablette android', 'seed_min'),
  ('tablette_android', 'tablette',         'tablette',         'seed_min'),
  ('tablette_android', 'Android tablet',   'android tablet',   'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- riz_brise_25kg
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('riz_brise_25kg', 'riz brisé 25kg', 'riz brise 25kg', 'seed_min'),
  ('riz_brise_25kg', 'riz brisé',      'riz brise',      'seed_min'),
  ('riz_brise_25kg', 'broken rice',    'broken rice',    'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- huile_vegetale_5l
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('huile_vegetale_5l', 'huile végétale 5L', 'huile vegetale 5l', 'seed_min'),
  ('huile_vegetale_5l', 'huile de cuisine',  'huile de cuisine',  'seed_min'),
  ('huile_vegetale_5l', 'cooking oil',       'cooking oil',       'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- farine_ble_50kg
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('farine_ble_50kg', 'farine de blé 50kg', 'farine de ble 50kg', 'seed_min'),
  ('farine_ble_50kg', 'farine de blé',      'farine de ble',      'seed_min'),
  ('farine_ble_50kg', 'wheat flour',         'wheat flour',        'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- sel_iode_1kg
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('sel_iode_1kg', 'sel iodé 1kg', 'sel iode 1kg', 'seed_min'),
  ('sel_iode_1kg', 'sel iodé',     'sel iode',     'seed_min'),
  ('sel_iode_1kg', 'iodized salt', 'iodized salt', 'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- lait_poudre_25kg
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('lait_poudre_25kg', 'lait en poudre 25kg', 'lait en poudre 25kg', 'seed_min'),
  ('lait_poudre_25kg', 'lait en poudre',      'lait en poudre',      'seed_min'),
  ('lait_poudre_25kg', 'powdered milk',        'powdered milk',       'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- haricots_blancs_50kg
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('haricots_blancs_50kg', 'haricots blancs 50kg', 'haricots blancs 50kg', 'seed_min'),
  ('haricots_blancs_50kg', 'haricots blancs',      'haricots blancs',      'seed_min'),
  ('haricots_blancs_50kg', 'white beans',           'white beans',          'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- amoxicilline_500mg_boite_100
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('amoxicilline_500mg_boite_100', 'amoxicilline 500mg', 'amoxicilline 500mg', 'seed_min'),
  ('amoxicilline_500mg_boite_100', 'amoxicillin',        'amoxicillin',        'seed_min'),
  ('amoxicilline_500mg_boite_100', 'amox 500',           'amox 500',           'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- sro_sachet
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('sro_sachet', 'SRO sachet',  'sro sachet',  'seed_min'),
  ('sro_sachet', 'SRO',         'sro',         'seed_min'),
  ('sro_sachet', 'ORS sachet',  'ors sachet',  'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- eau_oxygenee_1l
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('eau_oxygenee_1l', 'eau oxygénée 1L',       'eau oxygenee 1l',       'seed_min'),
  ('eau_oxygenee_1l', 'eau oxygénée',           'eau oxygenee',          'seed_min'),
  ('eau_oxygenee_1l', 'hydrogen peroxide',       'hydrogen peroxide',     'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- gants_latex_boite_100
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('gants_latex_boite_100', 'gants latex boîte 100', 'gants latex boite 100', 'seed_min'),
  ('gants_latex_boite_100', 'gants latex',           'gants latex',           'seed_min'),
  ('gants_latex_boite_100', 'latex gloves',           'latex gloves',          'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- seringue_5ml_boite_100
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('seringue_5ml_boite_100', 'seringue 5ml boîte 100', 'seringue 5ml boite 100', 'seed_min'),
  ('seringue_5ml_boite_100', 'seringue 5ml',           'seringue 5ml',           'seed_min'),
  ('seringue_5ml_boite_100', 'syringe 5ml',            'syringe 5ml',            'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- tente_familiale_4x4
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('tente_familiale_4x4', 'tente familiale 4x4', 'tente familiale 4x4', 'seed_min'),
  ('tente_familiale_4x4', 'tente familiale',     'tente familiale',     'seed_min'),
  ('tente_familiale_4x4', 'family tent',          'family tent',         'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- bache_pe_4x6
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('bache_pe_4x6', 'bâche PE 4x6m', 'bache pe 4x6m', 'seed_min'),
  ('bache_pe_4x6', 'bâche PE',      'bache pe',      'seed_min'),
  ('bache_pe_4x6', 'tarpaulin',     'tarpaulin',     'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- jerrican_20l
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('jerrican_20l', 'jerrican plastique 20L', 'jerrican plastique 20l', 'seed_min'),
  ('jerrican_20l', 'jerrican 20L',           'jerrican 20l',           'seed_min'),
  ('jerrican_20l', 'jerrycan',               'jerrycan',               'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- seau_plastique_20l
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('seau_plastique_20l', 'seau plastique 20L', 'seau plastique 20l', 'seed_min'),
  ('seau_plastique_20l', 'seau 20L',           'seau 20l',           'seed_min'),
  ('seau_plastique_20l', 'plastic bucket',      'plastic bucket',     'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- kit_hygiene_menage
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('kit_hygiene_menage', 'kit hygiène ménage', 'kit hygiene menage', 'seed_min'),
  ('kit_hygiene_menage', 'kit hygiène',        'kit hygiene',        'seed_min'),
  ('kit_hygiene_menage', 'hygiene kit',         'hygiene kit',        'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- natte_de_couchage
INSERT INTO couche_b.procurement_dict_aliases (item_id, alias_raw, normalized_alias, source) VALUES
  ('natte_de_couchage', 'natte de couchage', 'natte de couchage', 'seed_min'),
  ('natte_de_couchage', 'natte',             'natte',             'seed_min'),
  ('natte_de_couchage', 'sleeping mat',       'sleeping mat',      'seed_min')
ON CONFLICT (normalized_alias) DO NOTHING;

-- ============================================================
-- CONVERSIONS UNITAIRES (13 mandatory Sahel)
-- ============================================================
INSERT INTO couche_b.procurement_dict_unit_conversions (from_unit, to_unit, factor) VALUES
  ('litre',    'm3',      0.001),
  ('m3',       'litre',   1000),
  ('kg',       'tonne',   0.001),
  ('tonne',    'kg',      1000),
  ('ml',       'litre',   0.001),
  ('litre',    'ml',      1000),
  ('sac_50kg', 'kg',      50),
  ('kg',       'sac_50kg',0.02),
  ('m3',       'voyage',  0.143),
  ('voyage',   'm3',      7),
  ('tonne',    'sac_50kg',20),
  ('sac_50kg', 'tonne',   0.05),
  ('comprime', 'boite',   0.01)
ON CONFLICT (from_unit, to_unit) DO NOTHING;
