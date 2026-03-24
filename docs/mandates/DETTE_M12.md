# DETTE TECHNIQUE M12
**Reportee depuis :** M11
**Date :** 2026-03-11
**Autorite :** CTO / AO — Abdoulaye Ousmane

---

## CHEMIN CRITIQUE HUMAIN — BLOQUANT M12

**Prérequis historique :** 15 documents `annotated_validated` minimum (RÈGLE-23).  
**Statut terrain (2026-03-24) :** **22** documents validés ; corpus sur **Cloudflare R2**. Le verrou corpus M12 est **relevé** pour cette vague — voir [DMS_M12_CORPUS_GATE_EXECUTION.md](../m12/DMS_M12_CORPUS_GATE_EXECUTION.md).

**Non délégable. Non automatisable. AO uniquement** (pour toute nouvelle vague de ground truth).

  Sources disponibles confirmees :
    3 DAO (Dossiers d'Appel d'Offres)
    3 RFQ (Request for Quotation)
    Offres reelles anonymisables

  **Atteint :** 22 documents ≥ 15 requis — M12 débloqué côté corpus pour cette vague.

---

## DETTE TECHNIQUE

### DETTE-1 — API publique signaux marche
  Aucune API REST n'expose market_signals_v2.
  Les agents consomment la DB directement.
  Action : FastAPI endpoint GET /signals
           params : zone_id, alert_level, signal_quality
           auth   : a definir

### DETTE-2 — Alertes automatiques CRITICAL
  pg_notify actif (M10B) mais aucun listener operationnel.
  Les CRITICAL sont detectes, pas notifies.
  Action : listener pg_notify -> webhook / email sur CRITICAL
           Integrer AgentRunContext pour tracabilite

### DETTE-3 — Validation humaine decision_history
  decision_history peuple (M11) mais workflow de validation
  inexistant. Statut 'pending_review' bloque.
  Action : interface validation + statut reviewed/approved/rejected

### DETTE-4 — Tests Railway en CI/CD
  pytest tourne manuellement uniquement.
  Action : Railway test environment + GitHub Actions pipeline

### DETTE-5 — 046_evaluation_documents
  Migration prevue Plan Directeur V4.1.0 — decalee M13/M14.
  Depend du chemin critique humain (15 annotations).
  Reference : DMS_V4.1.1_PATCH.md

### DETTE-6 — market_surveys terrain reels
  Les surveys M11 sont des proxies mercurials.
  Ils doivent etre remplaces par des enquetes terrain reelles.
  Action : protocole collecte terrain + import pipeline

### DETTE-7 — IMC INSTAT : mapping categories → items

**Contexte :**
  imc_entries : indices agreges INSTAT 2018→2026
                8 categories × 88 periodes = 810 lignes
  mercurials  : prix unitaires DGMP 2023→2026
                27 396 lignes × 19 zones

**Manquant :**
  Table imc_category_item_map absente.
  Sans ce mapping, impossible de calculer :
    - Revision de prix (P1 = P0 × IMC_t1/IMC_t0)
    - Market basket construction
    - Benchmark historique 2018→2022

**Action M12 :**
  1. Creer migration 046_imc_category_map.py
     Table : imc_category_item_map
       (category_raw TEXT, item_canonical TEXT,
        weight NUMERIC, notes TEXT)
  2. Seed le mapping (8 categories → ~35 items)
  3. Creer compute_price_revision.py
  4. Exposer via API GET /revision-price

**Impact utilisateurs :**
  Mines    : revision couts infrastructure pluriannuelle
  ONG      : justification revision devis projets construction
  DGMP     : conformite clauses revision marches publics
  DMS      : signal IMC variation > 5% MOM → alerte construction

### DETTE-8 — Signaux IMC dans market_signals_v2

**Contexte :**
  imc_entries.variation_mom et variation_yoy calcules
  mais jamais transformes en signaux marche.

**Action M12 :**
  Integrer dans compute_market_signals.py :
    Si variation_mom > 3% → signal WATCH construction
    Si variation_mom > 8% → signal STRONG construction
    Si variation_yoy > 15% → signal CRITICAL construction
  taxo_l3 = 'construction_materials'
  Zones : Bamako (national) + propagation corridors

### DETTE-9 — Donnees IMC 2018→2022 non utilisees

**Contexte :**
  5 ans de donnees historiques presentes dans imc_entries
  Jamais utilisees dans aucun calcul DMS.

**Action M12 :**
  Recalculer seasonal_patterns pour categories construction
  en utilisant imc_entries 2018→2022 comme baseline.
  Precision residual_pct construction × 3 estimee.

---

## SEUILS M15 — A SURVEILLER DES M12

  Aucune modification M12+ ne peut degrader :
    coverage_extraction  >= 80%
    unresolved_rate      <= 25%
    vendor_match_rate    >= 60%
    review_queue_rate    <= 30%
