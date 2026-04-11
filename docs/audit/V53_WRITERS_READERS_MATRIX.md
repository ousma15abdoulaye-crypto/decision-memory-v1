# V53 — Matrice écrivains / lecteurs (audit opposable)

**Référence mandat :** `docs/mandates/M-CTO-V53-A-INVENTORY.md`  
**Date :** 2026-04-11  
**Statut :** opposable à la phase B (implémentation ADR-V53)

---

## 1. Marché

| Table | Writer(s) | Reader(s) | Fréquence | Invariant |
|-------|-----------|------------|-----------|-----------|
| `market_signals_v2` | `src/couche_a/market/signal_engine.py` (INSERT) ; `src/couche_b/imc_signals.py` (UPDATE enrichissement IMC) ; jobs / batch signal | M16 `src/services/market_delta.py` ; PV `src/services/pv_builder.py` ; W2 `src/api/routers/market.py` ; MQL T7 `src/mql/templates.py` ; cadre `src/api/routers/workspaces.py` | Batch + temps réel lecture | **Vérité agrégée M9** : `price_seasonal_adj`, `signal_quality`, formule versionnée (043) |
| `vendor_market_signals` | `src/workers/arq_projector_couche_b.py` ; `src/workers/arq_sealed_workspace.py` (projection post-événement) | PV ; `GET /api/market/vendors/...` ; cadre évaluation (via `process_market_signals_for_frame`) | Après seal / projection | **Projection mémoire fournisseur** ; ne pas recalculer une formule parallèle à M9 (ADR-V53) |
| `market_surveys` | ETL / routes enquêtes (hors inventaire exhaustif ici) | MQL T1–T6 `src/mql/templates.py` | Forte (agent MQL) | Vérité **micro** enquête / campagne ; complément à `market_signals_v2` |
| `survey_campaigns` | Idem | MQL (JOIN) | Lié aux surveys | Métadonnées campagne |
| `mercurials` | `src/couche_b/mercuriale/repository.py` (ingestion) | `src/couche_a/market/signal_engine.py` (agrégation vers msv2) ; `src/couche_b/imc_signals.py` | Batch | Source amont **brute** ; pas la lecture directe comparative M16 |

---

## 2. M16 prix

| Table | Writer(s) | Reader(s) | Invariant |
|-------|-----------|------------|-----------|
| `price_line_comparisons` | Routes M16 / init workspace | M16 frame ; `market_delta` (JOIN label) | `workspace_id` + tenant |
| `price_line_bundle_values` | Routes M16 POST prix ; `persist_market_deltas_for_workspace` (UPDATE `market_delta_pct`) | Grille M16 ; `compute_price_signal` | Delta signé vs **`market_signals_v2.price_seasonal_adj`** (module `market_signal_lookup`) |

---

## 3. M16 historique

| Table | Writer(s) | Reader(s) | Note |
|-------|-----------|------------|------|
| `assessment_history` | Trigger V52 `v52_p1_002` ; inserts métier | API M16 historique ; audit | Canon post-093 |
| `criterion_assessment_history` | Application / triggers legacy | `m16_evaluation_service` list history | **E18** — mandat `M-CTO-V53-E` pour fusion / vue |

---

## 4. Mémoire & event index

| Table | Writer(s) | Reader(s) | Note |
|-------|-----------|------------|------|
| `memory_entries` | `case_memory_writer` ; `src/core/dependencies.py` | Retrieval déterministe | Souvent clé `case_id` — mandat F pour `workspace_id` |
| `dms_event_index` | Triggers bridge `066` / fixes `077` ; ARQ `index_event` | `EventIndexService` ; `case_timeline` view | Fédération — pas remplacer les sources |

---

## 5. Corrections M12

| Table | Writer(s) | Reader(s) | Note |
|-------|-----------|------------|------|
| `m12_correction_log` | `M12CorrectionWriter` (`src/procurement/m12_correction_writer.py`) — **module présent** | Tests unitaires ; **aucune route produit** au moment V53-A | Mandat **G** : brancher écriture + lecture audit |

---

## 6. Référence décisionnelle

Décision de préséance et rôle VMS : **`docs/adr/ADR-V53-MARKET-READ-MODEL.md`**.
