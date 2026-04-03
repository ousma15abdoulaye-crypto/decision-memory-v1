# DMS Artifact Sovereignty Matrix — V2 Recalibré

**Référence** : `DMS_VIVANT_V2_FREEZE.md` §4
**Date** : 2026-04-03
**Source de vérité** : `DMS_ARTIFACT_SOVEREIGNTY_MATRIX.yaml` (ce fichier est un rendu lisible)

## Totaux

| Catégorie | Artefacts |
|---|---|
| Couche B — Marché & Normalisation | 11 |
| Couche A — Pipeline & Exécution | 9 |
| Couche A — Agents | 2 |
| Procurement — M12/M13/M14 | 5 |
| Transversal — V2 | 4 |
| Memory — V2 | 1 |
| Orchestration — V2 | 1 |
| **Total** | **33** |

## Règle d'usage

1. **AVANT TOUT WRITE** : ouvrir le YAML, trouver la table, vérifier `write_owner`
2. **Si service ≠ write_owner** : STOP + validation CTO
3. **Si table absente** : STOP + classifier + valider CTO + ajouter AVANT le code

## Couche B — Mémoire Marché & Normalisation

| Artefact | Nature | Write Owner | Append-Only | Migration |
|---|---|---|---|---|
| `procurement_dict_items` | source_of_truth | dictionary_service | non | MRD |
| `procurement_dict_aliases` | source_of_truth | dictionary_service | non | MRD |
| `dict_collision_log` | append_only_log | dictionary_service_trigger | oui | MRD |
| `mercurials` | source_of_truth | mercuriale_ingestion | non | 024, 040 |
| `mercuriale_sources` | source_of_truth | mercuriale_ingestion | non | 024 |
| `mercuriale_raw_queue` | append_only_log | mercuriale_ingestion | oui | 024 |
| `market_signals_v2` | market_memory | signal_engine | oui | 043 |
| `market_coverage` | read_projection | auto_refresh_trigger | non | 042, 060 |
| `decision_history` | market_memory | price_check_engine | oui | 044 |
| `imc_category_item_map` | source_of_truth | imc_service | non | 046 |
| `vendors` | source_of_truth | vendor_service | non | 041 |

## Couche A — Pipeline & Exécution

| Artefact | Nature | Write Owner | Append-Only | Migration |
|---|---|---|---|---|
| `pipeline_runs` | execution_trace | pipeline_orchestrator | oui | 032 |
| `pipeline_step_runs` | execution_trace | pipeline_orchestrator | oui | 033 |
| `analysis_summaries` | derived_summary | pipeline_analysis | oui | 035 |
| `memory_entries` | case_memory | case_memory_writer | oui | 002, 010 |
| `score_runs` | append_only_log | scoring_engine | oui | 026 |
| `committee_events` | append_only_log | committee_service | oui | 028 |
| `submission_registry_events` | append_only_log | submission_service | oui | 036 |
| `decision_snapshots` | sealed_snapshot | committee_service | oui | 029 |
| `audits` | append_only_log | audit_triggers | oui | 010, 038 |

## Couche A — Agents

| Artefact | Nature | Write Owner | Append-Only | Migration |
|---|---|---|---|---|
| `agent_checkpoints` | execution_trace | agent_framework | non | 045 |
| `agent_runs_log` | execution_trace | agent_framework | oui | 045 |

## Procurement — M12 / M13 / M14

| Artefact | Nature | Write Owner | Append-Only | Migration | Notes |
|---|---|---|---|---|---|
| `m12_correction_log` | human_feedback_log | m12_correction_writer | oui | 054 | event_time ajouté en 062 |
| `m13_correction_log` | human_feedback_log | m13_correction_writer | oui | 057, 058 | |
| `evaluation_documents` | case_memory | m14_evaluation_repository | oui | 056 | RLS via cases.tenant_id |
| `score_history` | append_only_log | m14_engine | oui | 059 | |
| `elimination_log` | append_only_log | m14_engine | oui | 059 | |

## Transversal — V2

| Artefact | Nature | Write Owner | Append-Only | Migration | Notes |
|---|---|---|---|---|---|
| `dms_event_index` | federated_index | bridge_triggers + event_index_service | oui | 061 | Bitemporal, partitionné |
| `candidate_rules` | append_only_log | candidate_rule_generator | oui | 063 | proposed→approved→applied |
| `rule_promotions` | append_only_log | promotion_service | oui | 063 | |
| `llm_traces` | append_only_log | langfuse_integration | oui | 065 | Backup Langfuse |

## Memory — V2

| Artefact | Nature | Write Owner | Append-Only | Migration | Notes |
|---|---|---|---|---|---|
| `dms_embeddings` | vector_index | embedding_service | non (upsert) | 064 | BGE-M3 1024d, pgvector |

## Orchestration — V2

| Artefact | Nature | Write Owner | Append-Only | Migration | Notes |
|---|---|---|---|---|---|
| `arq_job_queue` | job_queue | arq_workers | non | Redis | Éphémère |
