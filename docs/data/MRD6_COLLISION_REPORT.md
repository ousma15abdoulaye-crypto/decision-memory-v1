# MRD6_COLLISION_REPORT
# Rapport collisions conceptuelles — MRD-6 BRIQUE-3
# Date : 2026-03-09

## Parametres

seuil_fuzzy    : 85 (REGLE-26)
items_analyses : 600 (premiers 600 par item_id)
paires_totales : 179700

## Resultats

found     : 610
inserted  : 610 (586 pre-existants + 24 nouveaux MRD-6)
errors    : 0
pending   : 610

## Note schema V4

dict_collision_log dans public (schema V4)
fuzzy_score stocke en 0.0-1.0
resolution = 'unresolved' | 'auto_merged' | 'proposal_created'
item_a_id/item_b_id = varchar(64) — ids tronques si > 64 chars

## Types de collisions detectees

Principaux patterns :
  Agrafes de formats differents (23/8, 23/17, 24/6...)
  Aiguilles machine a coudre (differents numeros)
  Abonnements journaux (variantes orthographiques)
  Acide pour carreaux (avec/sans preparation)
  Anneau pour reliure (differents numeros)

## Resolution

Toutes les collisions sont status='unresolved'
Resolution : humain uniquement (REGLE-26)
Jamais resolution automatique LLM
