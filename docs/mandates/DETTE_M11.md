# DETTE TECHNIQUE M11
**Reportée depuis :** M10A / M10B
**Date :** 2026-03-11
**Priorité :** À traiter avant tout développement signal M11

---

## DETTE-1 — 14 zones sans severity_level

**Symptôme :**
578 signaux dont ~400 ont `severity_level = NULL`
→ `alert_level = NORMAL` même en zone de crise potentielle
→ Faux négatifs sur alertes humanitaires

**Zones concernées :**
zone-bandiagara-1, zone-bougouni-1, zone-dioila-1,
zone-douentza-1, zone-kita-1, zone-koulikoro-1,
zone-koutiala-1, zone-mopti-1, zone-nara-1,
zone-nioro-1, zone-san-1, zone-segou-1,
zone-sikasso-1, zone-taoudeni-1

**Action requise :**
Mapper ces 14 zone_id vers les contextes FEWS ML-x appropriés
dans zone_context_registry.

---

## DETTE-2 — market_surveys vide

**Symptôme :**
Signal quality plafonnée à `moderate` — aucun signal `strong`
ne peut être généré sans données market_surveys.

**Action requise :**
Implémenter import_market_surveys.py et peupler Railway.

---

## DETTE-3 — decision_history à peupler

**Symptôme :**
Table créée en 044 — 0 lignes.
Audit trail des décisions procurement inexistant.

**Action requise :**
Définir le modèle de données et les triggers d'alimentation.

---

## DETTE-4 — seasonal_patterns partiels

**Symptôme :**
1 786 patterns présents mais couverture incomplète.
residual_pct sous-estimé pour les items saisonniers.

**Action requise :**
Compléter les patterns manquants et valider la couverture
par taxo_l3.
