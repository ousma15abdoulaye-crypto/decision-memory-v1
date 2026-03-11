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
║  main            : 630bcae                                          ║
║  tag m10a-done   : de6cfbd (merge PR #183)                          ║
║  branche active  : main                                             ║
║  branche cible   : feat/m10b-agent-native (à créer)                 ║
║                                                                      ║
║  ALEMBIC                                                             ║
║  ──────────────────────────────────────────────────────────────     ║
║  head actuel     : 044_decision_history                             ║
║  head cible M10B : 045_agent_native_foundation                      ║
║  historique      : 001 → 044 — FREEZE ABSOLU                        ║
║                                                                      ║
║  RAILWAY — DONNÉES RÉELLES CONFIRMÉES POST-M10A                      ║
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
║  M10B — ÉTAT COURANT                                                 ║
║  ──────────────────────────────────────────────────────────────     ║
║  Statut        : MANDAT APPROUVÉ — EN ATTENTE PROBE ÉTAPE 0         ║
║  Audit CTO     : 12 failles identifiées et corrigées                ║
║    BLOQUANTES  : fetchone()[0], RETURN NULL trigger STATEMENT,      ║
║                  __exit__ try/except isolé, row[n] indices tests,   ║
║                  CONTRACT-02 paramétrable, op.execute convention    ║
║    MAJEURES    : rollback pattern, savepoint obs, get_db_url,       ║
║                  skip condition tests                                ║
║  Fichiers      : 7 à créer/modifier (périmètre FERMÉ)               ║
║    045_agent_native_foundation.py                                   ║
║    src/couche_a/agents/__init__.py                                  ║
║    src/couche_a/agents/framework.py                                 ║
║    scripts/probe_m10b.py                                            ║
║    tests/test_m10b_agent_framework.py                               ║
║    docs/mandates/DETTE_M11.md                                       ║
║    docs/freeze/MRD_CURRENT_STATE.md  ← modifier UNIQUEMENT étape 7  ║
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
║  migrations Alembic 001 → 044                                       ║
║                                                                      ║
║  PROCHAINE ACTION — SÉQUENCE OBLIGATOIRE                             ║
║  ──────────────────────────────────────────────────────────────     ║
║  1. Commiter cet anchor sur main                                    ║
║     git add CONTEXT_ANCHOR.md                                       ║
║     git commit -m "chore: context anchor post-audit M10B"           ║
║     git push origin main                                            ║
║  2. git checkout -b feat/m10b-agent-native                          ║
║  3. python scripts/probe_m10b.py                                    ║
║  4. POSTER output ici → STOP → GO CTO → down_revision confirmé      ║
║  5. NE PAS enchaîner automatiquement sur ÉTAPE 1                    ║
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
