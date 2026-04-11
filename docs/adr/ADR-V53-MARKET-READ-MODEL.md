# ADR-V53 — Modèle de lecture marché (agrégat M9 vs projection fournisseur)

**Statut :** Accepted (exécution technique mandat M-CTO-V53-B)  
**Date :** 2026-04-11  
**Contexte :** R9 / E24 — `vendor_market_signals` ≠ `market_signals_v2` (`docs/audit/RUPTURES_V52.md`).  
**Autorité :** Ne contredit pas `DMS_V4.1.0_FREEZE.md` ni Kill List (pas de winner/rank/recommendation).

---

## 1. Décision

1. **Lecture de référence pour signal prix agrégé** (écarts comparatif M16, `market_delta_pct`, requêtes MQL sur **signal national/zone agrégé**) : **`market_signals_v2`** uniquement, en particulier **`price_seasonal_adj`** et **`signal_quality` ∈ ('strong','moderate','propagated')** avec résolution item (slug + `pg_trgm` seuil **0.55**) alignée sur `src/services/market_signal_lookup.py`.

2. **`vendor_market_signals`** : **projection métier** (mémoire fournisseur / contexte workspace) alimentée par **workers** (`arq_projector_couche_b`, `arq_sealed_workspace`). Elle **ne définit pas** un second prix de référence concurrent de la formule M9. Les payloads restent **indicatifs** pour pertinence (`evaluation_frame`), pas pour recalculer un prix de marché officiel.

3. **Ordre d’affichage** (PV snapshot, cadre d’évaluation workspace) : si le workspace a un **`zone_id`** et qu’il existe **au moins une** ligne `market_signals_v2` pour cette zone, la section « marché » **priorise** ces lignes ; sinon repli sur **`vendor_market_signals`** pour le même workspace. *(Comportement inverse de l’ancien fallback « VMS puis MSV2 ».)*

4. **MQL** : les templates T1–T6 restent sur **`market_surveys`** (enquêtes). Le template **`T7_MSV2_REFERENCE`** interroge **`market_signals_v2`** pour les questions de **prix de référence agrégé** (mots-clés : signal agrégé, M9, référence marché, mercuriale agrégée).

5. **Routes W2** : `GET /api/market/overview` et `GET /api/market/items/{item_key}/history` restent sur **`market_signals_v2`** ; `GET /api/market/vendors/{vendor_id}/signals` reste sur **`vendor_market_signals`** (périmètre fournisseur).

---

## 2. Conséquences (fichiers phase B)

- `src/services/market_signal_lookup.py` (nouveau)
- `src/services/market_delta.py`
- `src/mql/templates.py`, `template_selector.py`, `engine.py` (sources T7)
- `src/services/pv_builder.py`
- `src/api/routers/workspaces.py` (evaluation-frame)
- `src/api/routers/market.py` (commentaires / cohérence)
- `src/workers/arq_projector_couche_b.py`, `arq_sealed_workspace.py` (documentation)
- Tests : `tests/unit/test_mql_engine.py`, `tests/unit/test_market_signal_lookup.py`, `tests/services/test_pv_builder.py`

---

## 3. Vérification (testable)

- Même `zone_id` + `item_id` : MQL T7 et `lookup_market_price_seasonal_adj` utilisent la **même** sémantique SQL (paramètres bindés).
- PV + evaluation-frame : avec `zone_id` et lignes MSV2, la réponse **contient** des signaux issus de MSV2 avant tout contenu VMS-only.

---

## 4. Implémentation

Voir PR / commits `M-CTO-V53-B` sur branche `feat/M-CTO-V53-execution` (réf. dépôt).
