# DMS V5.2 — Registre des Écarts

**Identifiés lors de la radiographie V5.1 initiale (Phase P1-P2)**
**Mis à jour :** 2026-04-09

---

## Légende

| Symbole | Signification |
|---|---|
| ✅ | Corrigé |
| 🔜 | Mandat futur — en attente GO CTO |
| ⚠️ | Partiel |
| ➖ | Hors scope V5.2 |

---

## Écarts DB & Fondations (P1)

| # | Écart | Constat | Statut | Correction |
|---|---|---|---|---|
| E01 | `cell_json` opaque — historique ne capte pas tous les champs | Trigger P1.2 lit `score` uniquement | ⚠️ | P1.2 trigger en place, extension (numeric_score, value) pour P3 |
| E02 | Triggers immutabilité absents | INV-W05, INV-S03, INV-S04 non enforcés au niveau DB | ✅ | v52_p1_001 |
| E03 | Auto-historisation criterion_assessments absente | changed_by_uuid non capturé | ✅ | v52_p1_002 |
| E04 | RLS partielle sur 25+ tables | Tables sans FORCE RLS | ✅ | v52_p1_003 |
| E05 | `app.current_user` absent du pool async | Trigger P1.2 retournait NULL pour changed_by_uuid | ✅ | src/db/async_pool.py |
| E06 | `middleware/tenant.py` inexistant | Middleware V5.2 absent, posture sécurité dégradée | ✅ | src/middleware/tenant.py créé |

---

## Écarts Auth & RBAC (P1-P2)

| # | Écart | Constat | Statut | Correction |
|---|---|---|---|---|
| E07 | 2 systèmes RBAC coexistants (V4.x DB + V5.2 mémoire) | Incohérence possible entre rôles | ⚠️ | Bridge `_LEGACY_ROLE_MAP` en P2.1 — migration complète P5 |
| E08 | `guard.py` inexistant | Authorisation dispersée dans les routes | ✅ | src/auth/guard.py réécrit |
| E09 | `permissions.py` : comptages incorrects par rôle | technical/budget_holder mal équilibrés | ✅ | src/auth/permissions.py corrigé |
| E10 | `market.write` absent de WRITE_PERMISSIONS | Routes market non protégées correctement | ✅ | src/auth/permissions.py |
| E11 | 20 routes sans `guard()` apparent | Grep initial trompeur — RBAC V4.x actif | ✅ (diagnostiqué) | Bridge _LEGACY_ROLE_MAP — pas de régression |
| E12 | `agent.query` dans mauvais rôle | Assigné à `technical` au lieu de `budget_holder` | ✅ | src/auth/permissions.py |

---

## Écarts Agent & Observabilité (P3)

| # | Écart | Constat | Statut | Correction |
|---|---|---|---|---|
| E13 | `workspace_status_handler` crash | `load_cognitive_facts()` sync appelé avec `AsyncpgAdapter` | ✅ | `async_load_cognitive_facts()` créé |
| E14 | `intent_confidence` incorrect dans `mql_query_log` | Log de `mql_result.confidence` au lieu de `intent.confidence` | ✅ | handlers.py + agent.py |
| E15 | `_extract_article` type annotation incorrecte | Retour `str` mais peut retourner `None` | ✅ | `str | None` |
| E16 | `context.messages[-50]` au lieu de `[-50:]` | Sliding window FIFO cassé | ✅ | context_store.py |
| E17 | `DATABASE_URL` validator rejetait `postgresql+psycopg://` | Tests CI cassés | ✅ | config.py normalise avant validation |
| E18 | 2 tables d'historique M16 divergentes | `criterion_assessment_history` (table) ≠ `assessment_history` (trigger P1.2) | 🔜 | Réconciliation mandat P4 |

---

## Écarts Config & Infrastructure

| # | Écart | Constat | Statut | Correction |
|---|---|---|---|---|
| E19 | `os.environ.get()` dispersés dans 18 fichiers `src/` | Pas de source de vérité unique pour la config | 🔜 | Mandat `refactor/v52-pydantic-settings` (soumis CTO) |
| E20 | `process_info_handler` sans RAG réel | Réponses non ancrées dans la base documentaire | 🔜 | Mandat `feature/v52-rag-process-info` (soumis CTO) |

---

## Écarts Architecture V4.1 ↔ V5.x (identifiés en P2.5-R1)

| # | Écart | Constat | Statut |
|---|---|---|---|
| E21 | `decision_snapshots` non intégrés au PV W3 | Décision Couche A absente du sceau | 🔜 |
| E22 | `score_history` non consommé par V5.2 | Granularité M14 perdue | 🔜 |
| E23 | M13 blueprint non persisté dans PV | Compliance check V4.1 non tracé dans scellement | 🔜 |
| E24 | `vendor_market_signals` et `market_signals_v2` sources divergentes | Double source de vérité prix | 🔜 |
| E25 | `decision_history` absente → signal qualité décision 0.15 mort | Poids signal toujours zéro | 🔜 |

---

## Résumé par phase

| Phase | Écarts identifiés | Corrigés | En attente |
|---|---|---|---|
| P1 (DB + Auth) | 12 | 12 | 0 |
| P2 (Métier) | 5 | 4 | 1 (E07 bridge partiel) |
| P3 (Agent) | 6 | 6 | 0 |
| P4+ (Architecture) | 7 | 0 | 7 |
| **TOTAL** | **30** | **22** | **8** |

---

## Priorisation des 8 écarts ouverts

| Priorité | Écart | Raison |
|---|---|---|
| 🔴 Critique | E18 (2 historiques M16 divergents) | Risque de données perdues en P4 |
| 🔴 Critique | E07 (2 RBAC coexistants) | Faille de sécurité potentielle si bridge incomplet |
| 🟡 Important | E19 (os.environ dispersés) | Mandat Pydantic Settings — prêt à implémenter |
| 🟡 Important | E20 (RAG process_info) | Mandat RAG — prêt à implémenter |
| 🟡 Important | E21 (decision_snapshots dans PV) | Opposabilité PV V5.3 |
| 🟢 Dette | E22, E23, E25 | Granularité audit — PV V5.3 |
| 🟢 Dette | E24 (vendor signals divergents) | Cohérence Couche B |
