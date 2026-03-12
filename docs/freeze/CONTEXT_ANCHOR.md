# CONTEXT ANCHOR OFFICIEL — VERSION OPPOSABLE

```
╔══════════════════════════════════════════════════════════════════════╗
║  CONTEXT ANCHOR — DMS v4.1                                          ║
║  Dernière mise à jour : 2026-03-11                                  ║
║  Autorité : CTO / AO — Abdoulaye Ousmane                           ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  GIT                                                                 ║
║  ──────────────────────────────────────────────────────────────     ║
║  main            : 010a353 (merge M10B) — M11 en PR #185             ║
║  tag m10b-done   : 010a353 (merge PR #184 feat/m10b-agent-native)   ║
║  tag m11-done    : 14f762f (PR #185 feat/m11-signal-integrity)      ║
║  hash complet    : git rev-parse m11-done                           ║
║  branche active  : feat/m11-signal-integrity                        ║
║                                                                      ║
║  ALEMBIC                                                             ║
║  ──────────────────────────────────────────────────────────────     ║
║  head actuel     : 045_agent_native_foundation                      ║
║  historique      : 001 -> 045 — FREEZE 001-044                      ║
║                                                                      ║
║  RAILWAY — DONNÉES RÉELLES CONFIRMÉES POST-M11                       ║
║  ──────────────────────────────────────────────────────────────     ║
║  procurement_dict_items : 1 490 items actifs                        ║
║  mercurials             : 27 396 lignes                             ║
║  mercurials.item_id     : UUID — VIDE — NON UTILISÉ                 ║
║                           jointure via item_canonical UNIQUEMENT    ║
║  mercurials_item_map    : 1 629 mappings                            ║
║  tracked_market_items   : 1 004 items                               ║
║  tracked_market_zones   : 19 zones                                  ║
║  zone_context_registry  : 20 contextes (6+14 DETTE-1) ✓              ║
║                           ML-1,7,8,2,9,6 + 14 zones severity        ║
║  geo_price_corridors    : 7 corridors (Gao→Menaka ML-9/32%) ✓       ║
║  seasonal_patterns      : 1 786 (v1.1_mercurials) ✓                ║
║  market_signals_v2      : 1 106 signaux (post M11 compute) ✓        ║
║                           formula_version 1.1, residual_pct > 0     ║
║                           CRITICAL zones ipc_3+/ipc_4+ uniquement   ║
║  market_surveys         : 13 110 lignes ✓ DETTE-2 résolue          ║
║  decision_history       : 115 lignes ✓ DETTE-3 résolue             ║
║  dict_collision_log     : 0 sur Railway (résolu M10A)               ║
║  couche_a               : agent_checkpoints, agent_runs_log (045)   ║
║                                                                      ║
║  CONTRACT-02 — DÉFINITIF                                             ║
║  ──────────────────────────────────────────────────────────────     ║
║  INTERDIT Railway  : migrations, ALTER, DROP, DELETE                ║
║  AUTORISÉ Railway  : compute, seeds validés CTO, probe               ║
║  Flag Railway      : DMS_ALLOW_RAILWAY=1                            ║
║                                                                      ║
║  JOINTURE MERCURIALS — DÉFINITIVE ET FIGÉE                           ║
║  ──────────────────────────────────────────────────────────────     ║
║  mercurials.item_id (UUID) = artefact legacy — IGNORÉ               ║
║  Chemin obligatoire :                                                ║
║    item_canonical → mercurials_item_map → dict_item_id              ║
║  Jointure : LOWER(TRIM(item_canonical)) des deux côtés              ║
║                                                                      ║
║  M10B — DONE 2026-03-11                                              ║
║  ──────────────────────────────────────────────────────────────     ║
║  Statut        : MERGE PR #184 — tag m10b-done pose                 ║
║  couche_a       : schema + agent_checkpoints + agent_runs_log       ║
║  pg_notify      : fn_dms_event_notify, trg_notify_market_*          ║
║  framework.py   : AgentRunContext, AgentMemory (ADR-010)           ║
║                                                                      ║
║  M11 — DONE 2026-03-11 (PR #185 en attente merge)                   ║
║  ──────────────────────────────────────────────────────────────     ║
║  Statut        : tag m11-done pose — 8 tests passés                 ║
║  DETTE-1       : 14 zones severity_level seedées ✓                  ║
║  DETTE-2       : market_surveys 13 110 lignes ✓                     ║
║  DETTE-3       : decision_history 115 lignes ✓                      ║
║  DETTE-4       : seasonal_patterns 1 786 > baseline ✓                ║
║  DETTE-5       : Gao→Menaka corridor ML-9/32% ✓                     ║
║                                                                      ║
║  FREEZE ABSOLU — NE JAMAIS MODIFIER                                  ║
║  ──────────────────────────────────────────────────────────────     ║
║  docs/freeze/SYSTEM_CONTRACT.md                                     ║
║  docs/freeze/DMS_V4.1.0_FREEZE.md                                   ║
║  docs/freeze/DMS_ORCHESTRATION_FRAMEWORK_V1.md                      ║
║  migrations Alembic 001 -> 044                                      ║
║                                                                      ║
║  PROCHAINE MILESTONE : M12                                          ║
║  Dettes : DETTE_M12.md (API signaux, alertes CRITICAL, validation)  ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Règle — À remplir à la fin de chaque merge

Mettre à jour ce fichier avec les valeurs réelles :
- main, tag, branche active
- alembic head
- données Railway (counts)
- statut milestone courant
- prochaine action
