# DETTE TECHNIQUE M12
**Reportee depuis :** M11
**Date :** 2026-03-11
**Autorite :** CTO / AO — Abdoulaye Ousmane

---

## CHEMIN CRITIQUE HUMAIN — BLOQUANT M12

**15 documents annotated_validated requis avant M12.**
**Non delegable. Non automatisable. AO uniquement.**

  Sources disponibles confirmees :
    3 DAO (Dossiers d'Appel d'Offres)
    3 RFQ (Request for Quotation)
    Offres reelles anonymisables

  Sans ces 15 documents : M12 ne demarre pas.
  Ce n'est pas une dette technique — c'est un prerequis metier.

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

---

## SEUILS M15 — A SURVEILLER DES M12

  Aucune modification M12+ ne peut degrader :
    coverage_extraction  >= 80%
    unresolved_rate      <= 25%
    vendor_match_rate    >= 60%
    review_queue_rate    <= 30%
