# DETTE M10B — À résoudre post-M10A

**Date** : 2026-03-11  
**Contexte** : Audit final M10A

---

## DETTE-1 [M10B] zone_id mapping

| Source | Format | Exemple |
|--------|--------|---------|
| mercurials.zone_id | zone-{nom}-1 | zone-bamako-1 |
| zone_context_registry | ML-x (FEWS Mali) | ML-1 |

**Impact** : 420 signaux avec `severity_level` NULL (zones sans contexte M8).

**Zones sans zone_context_registry** :
- zone-bandiagara-1, zone-bougouni-1, zone-dioila-1, zone-douentza-1
- zone-kita-1, zone-koulikoro-1, zone-koutiala-1, zone-mopti-1
- zone-nara-1, zone-nioro-1, zone-san-1, zone-segou-1
- zone-sikasso-1, zone-taoudeni-1

**Action** : Créer une table `zone_id_mapping` ou normaliser les zone_id mercurials vers les zone_id M8.

---

## DETTE-2 [M10B] market_surveys vide

Script `import_market_surveys.py` livré ✓  
Données terrain à importer.

---

## DETTE-3 [M10B] decision_history vide

Table créée ✓  
Données historiques à importer.  
Poids 0.15 activé quand données présentes.
