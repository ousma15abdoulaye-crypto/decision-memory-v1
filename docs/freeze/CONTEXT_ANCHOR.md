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
║  main            : 010a353                                          ║
║  tag m10b-done   : 010a353 (merge PR #184 feat/m10b-agent-native)   ║
║  hash complet    : 010a353f2fee8185f4f574626a30cfbcea058b97         ║
║  branche active  : main                                             ║
║                                                                      ║
║  ALEMBIC                                                             ║
║  ──────────────────────────────────────────────────────────────     ║
║  head actuel     : 045_agent_native_foundation                      ║
║  historique      : 001 -> 045 — FREEZE 001-044                      ║
║                                                                      ║
║  RAILWAY — DONNÉES RÉELLES CONFIRMÉES POST-M10B                      ║
║  ──────────────────────────────────────────────────────────────     ║
║  procurement_dict_items : 1 490 items actifs                        ║
║  mercurials             : 27 396 lignes                             ║
║  mercurials.item_id     : UUID — VIDE — NON UTILISÉ                 ║
║                           jointure via item_canonical UNIQUEMENT    ║
║  mercurials_item_map    : 1 629 mappings                            ║
║  tracked_market_items   : 1 004 items                               ║
║  tracked_market_zones   : 19 zones                                  ║
║  zone_context_registry  : 6 contextes FEWS Mali                     ║
║                           ML-1  normal       ipc_1_minimal  +0%     ║
║                           ML-7  seasonal     ipc_2_stressed +8%     ║
║                           ML-8  security     ipc_3_crisis   +25%    ║
║                           ML-2  security     ipc_3_crisis   +18%    ║
║                           ML-9  security     ipc_4_emergency+32%    ║
║                           ML-6  security     ipc_4_emergency+50%    ║
║  geo_price_corridors    : 6 corridors actifs                        ║
║                           (Gao→Menaka : skip — zone manquante)      ║
║  seasonal_patterns      : 1 786 (v1.1_mercurials) ✓                ║
║  market_signals_v2      : 578 signaux                               ║
║                           formula_version 1.1                       ║
║                           residual_pct > 0 ✓                        ║
║                           CRITICAL détecté zones crise ✓            ║
║  market_surveys         : 0 lignes — DETTE-2                        ║
║  decision_history       : table créée (044) — 0 lignes — DETTE-3    ║
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
║  DETTES DOCUMENTÉES → DETTE_M11.md (ne pas traiter en M10B)         ║
║  ──────────────────────────────────────────────────────────────     ║
║  DETTE-1  14 zones sans severity_level                              ║
║           zones : bandiagara, bougouni, dioila, douentza,           ║
║                   kita, koulikoro, koutiala, mopti, nara,           ║
║                   nioro, san, segou, sikasso, taoudeni              ║
║           impact : ~400 signaux alert_level=NORMAL                  ║
║                    même en zone de crise → faux négatifs            ║
║  DETTE-2  market_surveys vide → signal quality plafonnée            ║
║  DETTE-3  decision_history vide → audit trail absent                ║
║  DETTE-4  seasonal_patterns partiels → residual_pct sous-estimé     ║
║  DETTE-5  Gao→Menaka corridor skip → zone-menaka-1 à mapper         ║
║                                                                      ║
║  FREEZE ABSOLU — NE JAMAIS MODIFIER                                  ║
║  ──────────────────────────────────────────────────────────────     ║
║  docs/freeze/SYSTEM_CONTRACT.md                                     ║
║  docs/freeze/DMS_V4.1.0_FREEZE.md                                   ║
║  docs/freeze/DMS_ORCHESTRATION_FRAMEWORK_V1.md                      ║
║  migrations Alembic 001 -> 044                                      ║
║                                                                      ║
║  PROCHAINE MILESTONE : M11                                          ║
║  Dettes : DETTE_M11.md (zones severity, surveys, decision_history)  ║
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
