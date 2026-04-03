# Rapport Metriques M15 — DMS V4.1

**Date :** 2026-04-03T15:55:17Z
**Script :** `scripts/measure_m15_metrics.py`
**Gates VERT :** 1/5 | **ROUGE :** 4/5

---

## Tableau de bord M15

| Metrique | Valeur | Seuil | Gate |
|---|---|---|---|
| coverage_extraction (%) | 0.0% | >= 80.0% | ROUGE |
| unresolved_rate (%) | 100.0% | <= 25.0% | ROUGE |
| vendor_match_rate (%) | 0.0% | >= 60.0% | ROUGE |
| review_queue_rate (%) | 0.0% | <= 30.0% | VERT |
| signal_quality_cov (%) | 5.5% | >= 50.0% | ROUGE |

---

## Details metriques

### coverage_extraction (%)
- **Valeur :** `0.0`
- **Gate :** `>= 80.0%` -> **ROUGE**
- **Detail :** 0/25 documents extractes
- **Note :** % docs hors status pending

### unresolved_rate (%)
- **Valeur :** `100.0`
- **Gate :** `<= 25.0%` -> **ROUGE**
- **Detail :** 293/293 dossiers sans decision
- **Note :** % cases sans decision_snapshot

### vendor_match_rate (%)
- **Valeur :** `0.0`
- **Gate :** `>= 60.0%` -> **ROUGE**
- **Detail :** 0/21850 market_surveys avec vendor_id
- **Note :** % surveys avec vendor identifie

### review_queue_rate (%)
- **Valeur :** `0.0`
- **Gate :** `<= 30.0%` -> **VERT**
- **Detail :** 0/0 annotations en attente validation
- **Note :** % annotation_registry is_validated=false

### signal_quality_cov (%)
- **Valeur :** `5.5`
- **Gate :** `>= 50.0%` -> **ROUGE**
- **Detail :** 82/1490 items avec signal
- **Note :** % dict items avec >= 1 signal market_signals_v2

### drift_by_category
- **Valeur :** `voir detail`
- **Derive par categorie :**
  - Textile : residual=12.30% (82 signaux)
  - Fournitures bureau : residual=11.93% (142 signaux)
  - Sante et hygiene : residual=10.80% (10 signaux)
  - Presse et abonnements : residual=9.94% (71 signaux)
  - Construction : residual=9.36% (190 signaux)
  - Divers : residual=8.94% (177 signaux)
  - Materiel scolaire : residual=7.82% (17 signaux)
  - Alimentation : residual=7.71% (293 signaux)
  - Art de la table : residual=7.25% (55 signaux)
  - Plastiques et emballages : residual=7.21% (14 signaux)
- **Note :** Top categories par deviation prix (residual_pct)

---

## Actions requises

| Gate | Statut | Action |
|---|---|---|
| coverage_extraction (%) | ROUGE | Lancer orchestrateur M12 sur documents pending |
| unresolved_rate (%) | ROUGE | Traiter 100 dossiers DAO/RFQ avant M15-done |
| vendor_match_rate (%) | ROUGE | Enrichir vendors dans market_surveys (mapping fournisseurs) |
| review_queue_rate (%) | VERT | Sync 87 annotations locales + valider review_required |
| signal_quality_cov (%) | ROUGE | Compléter mapping mercurials_item_map (coverage 67->70%) |

---

## Checklist M15 — 14 criteres

```
[X] 1. Probe Railway documentee — 9 metriques dans docs/PROBE_2026_04_03.md
[X] 2. Migrations 059->067 appliquees — alembic current = 067
[ ] 3. annotated_validated >= 50 — gate REGLE-23 (0 actuel, 87 local a sync)
[X] 4. mercurials_item_map coverage documentee (67.38%)
[X] 5. market_signals_v2 : strong+moderate >= 40% (90.43% VERT)
[X] 6. 100 items dict_items label_status = validated
[ ] 7. ANNOTATION_USE_PASS_ORCHESTRATOR = 1 en prod (mandat Railway Dashboard CTO)
[X] 8. RLS policies actives Railway — 12 policies verifiees
[X] 9. DISASTER_RECOVERY.md operationnel
[ ] 10. 100 dossiers DAO/RFQ traites avec metriques
[ ] 11. Precision extraction documentee (donnee reelle)
[X] 12. ADR-SIGNAL-TRIGGER-001 signe
[ ] 13. Redis/ARQ ou alternative documentee (ADR-H2-ARQ-001 existant, REDIS_URL Railway pending)
[ ] 14. M15_METRICS.md publie avec donnees reelles (ce fichier — donnees partielles)
```

---

*Genere automatiquement par `scripts/measure_m15_metrics.py`*