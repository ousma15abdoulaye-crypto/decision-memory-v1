# DMS V5.2 — Registre des Ruptures

**Identifiées lors de la radiographie V4.1+V4.2+V5.1 (Phase P2.5-R1)**
**Mis à jour :** 2026-04-09

---

## Légende

| Symbole | Signification |
|---|---|
| ✅ | Corrigé en P2.5b |
| 🔜 | Dette documentée — mandat futur |
| ⚠️ | Partiel — test en attente de données |

---

## Ruptures P1 — Critiques (PV non opposable sans correction)

| ID | Rupture | Impact | Statut | Phase correction |
|---|---|---|---|---|
| **R1** | `criterion_assessments.cell_json` rempli manuellement, pas depuis M14 | Les utilisateurs refont le travail de M14. Risque d'erreur humaine dans le PV | ✅ | P2.5b-R1 + **M-V52-A** tests synthétiques `test_v52_r1_r3_synthetic.py` |
| **R3** | `market_delta_pct` M16 non calculé depuis `market_signals_v2` | Signal prix toujours jaune → expert aveugle sur anomalies prix | ✅ | P2.5b-R3 + **M-V52-A** (idem) ; correctif SQL `set_limit(REAL)` dans `src/services/market_signal_lookup.py` |
| **R10** | `quorum_service` + `weight_validator` existaient mais jamais appelés au seal | Scellement possible sans quorum ni validation poids → PV non conforme | ✅ | P2.5b-R10 |

*Les scénarios **Railway** riches en données restent une preuve complémentaire ; les tests **M-V52-A** couvrent la chaîne sur DB de test migrée (`geo_master`, `procurement_dict_items`, `pg_trgm`).*

---

## Ruptures P2 — Importantes (dette technique significative)

| ID | Rupture | Impact | Statut | Mandat futur |
|---|---|---|---|---|
| **R2** | `decision_history` absente (signal poids 0.15 mort) | Signal quality systématiquement dégradé | 🔜 | P4 ou P6 — mandat dédié |
| **R4** | `decision_snapshots` absent du PV W3 | Décision M14 perdue au scellement | 🔜 | P2.6-R4 dans mandat PV V5.3 |
| **R6** | `score_history` non lu dans le PV | Scores granulaires M14 perdus | 🔜 | P2.6-R6 dans mandat PV V5.3 |
| **R7** | M13 blueprint non persisté | Blueprint réglementaire indisponible pour agent/audit | 🔜 | Mandat M13-persistence |
| **R9** | `vendor_market_signals` ≠ `market_signals_v2` | Signaux contradictoires possibles | 🔜 | Mandat cohérence Couche B |

---

## Ruptures P3 — Dette documentée

| ID | Rupture | Impact | Statut |
|---|---|---|---|
| **R5** | `score_runs` (case_id) non consommé | Scores Couche A V3.3.2 inaccessibles | 🔜 |
| **R8** | `m13_correction_log` jamais relu | Boucle d'apprentissage morte | 🔜 |

---

## Détail des corrections P2.5b

### R10 — Seal checks

**Avant :**
```
Scellement W3 → build_pv_snapshot() directement
(quorum, poids, flags jamais vérifiés)
```

**Après :**
```
Scellement W3 → run_all_seal_checks()
  ├─ CHECK 1 : quorum ≥ 4 membres, ≥ 1 par rôle critique (INV-W01)
  ├─ CHECK 2 : SUM(ponderation) non-éliminatoires ∈ [99.5, 100.5] (INV-W03)
  ├─ CHECK 3 : 0 assessment_comments.is_flag non résolus
  └─ CHECK 4 : committees.status cohérent si legacy_case_id (WARNING)
  
Si check_result.passed = False → HTTP 422 (liste complète des erreurs)
SINON → build_pv_snapshot() (comportement inchangé)
```

### R3 — market_delta_pct

**Avant :**
```
M16 affichage → compute_price_signal(market_delta_pct=None) → signal JAUNE toujours
```

**Après :**
```
Write path :
  POST price → background task persist_market_deltas_for_workspace()
             → jointure pg_trgm item/zone sur market_signals_v2
             → δ = abs(prix_fournisseur − prix_signal) / prix_signal
             → persisté dans price_line_bundle_values.market_delta_pct

Read path :
  M16 affichage → market_delta_pct FROM DB → compute_price_signal()
                → signal VERT (< 0.15) / JAUNE (0.15-0.30) / ROUGE (> 0.30)
```

### R1 — Bridge M14→M16

**Avant :**
```
evaluation_documents.scores_matrix → (jamais lu par M16)
criterion_assessments.cell_json ← saisie manuelle utilisateur
```

**Après :**
```
POST /api/workspaces/{ws}/m16/sync-from-m14
  → evaluation_documents.scores_matrix
  → mapping offer_document_id → bundle_id (via supplier_bundles)
  → mapping criterion_key → criterion_id (via dao_criteria.code)
  → Règle non-écrasement :
      cell_json IS NULL                 → INSERT (source: "m14")
      cell_json->>'score' IS NULL       → UPDATE (source: "m14")
      cell_json->>'score' IS NOT NULL   → SKIP (modification utilisateur)
  → BridgeResult : created/updated/skipped/unmapped
```

---

## Pipeline séquentiel recostruit

```
M12 (LLM extraction)
  ↓ M12Output (RH1 + RH2)
M13 (compliance check)
  ↓ ComplianceChecklist, elimination_log
M14 (évaluation scoring)
  ↓ EvaluationReport, evaluation_documents.scores_matrix ──────┐
Couche A (committees)                                           │ R1 ✅
  ↓ committee_decisions, decision_snapshots ──────┐            │
V5.2 Cognitive Layer                              │ R4 🔜      │
  ├─ criterion_assessments.cell_json ◄────────────────────────┘
  ├─ market_delta_pct ◄─ market_signals_v2 ◄─ Couche B ✅ (R3)
  ├─ seal_checks (quorum + poids) ✅ (R10)
  └─ PV scellé (W3)  ◄──────────────────────────────────────┘
```
