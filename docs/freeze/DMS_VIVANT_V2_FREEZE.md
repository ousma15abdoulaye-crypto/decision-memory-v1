# DMS VIVANT — PLAN V2 INTÉGRAL RECALIBRÉ

**Référence** : DMS-VIVANT-V2-FREEZE
**Classification** : Architecture Système — Document Opposable Gelé
**Historique** : Probe Repo → Fusion Opus/GPT → V1 → Audit 7 failles → Erratum CTO → V2 Intégral → **Sonde profonde repo → V2 Recalibré**
**Statut** : FREEZE CANDIDATE
**Date** : 2025-07-13 (V2) → 2026-04-03 (Recalibrage)
**Autorité de gel** : CTO

---

## TABLE DES MATIÈRES

| § | Titre |
|---|---|
| 0 | Historique décisionnel et delta V1→V2→V2-RECAL |
| 1 | Thèse architecturale |
| 2 | Principes non négociables — 16 règles |
| 3 | Architecture deux niveaux — Infrastructure + Intelligence |
| 4 | Matrice de souveraineté des artefacts (corrigée) |
| 5 | H0 — Fondations (recalibré) |
| 6 | H1 — Audit M13 + Agent Foundation (recalibré) |
| 7 | H2 — Mémoire Structurée + Orchestration |
| 8 | H3 — Intelligence — RAG Production-Grade |
| 9 | H4 — Vues Produit |
| 10 | Contrats d'interface inter-horizons |
| 11 | Gouvernance des gates |
| 12 | Matrice anti-collision |
| 13 | Inventaire fichiers — 132 fichiers |
| 14 | Séquence d'exécution (recalibrée) |
| 15 | Stop signals — 25 |
| 16 | Done binaire — 103 items |
| 17 | Risques et mitigations — 18 risques |
| 18 | Formulation canonique |

---

## §0 — HISTORIQUE DÉCISIONNEL ET DELTA V1→V2→V2-RECAL

### 0.1 Chaîne de décision

```
2025-07-12  Probe repo complet (fichiers, tables, triggers, docs gelés)
2025-07-12  Plan Opus (H0→H4, gates, code concret)
2025-07-12  Plan GPT (7 chantiers, matrice souveraineté, event fabric)
2025-07-12  Arbitrage — Plan V1 fusionné (114 fichiers, 87 done)
2025-07-13  Audit technique — 7 failles identifiées
2025-07-13  Verdict failles — 5 acceptées, 1 différée, 1 rejetée
2025-07-13  Erratum CTO — décision agentique, clarification P8, levée S1
2025-07-13  Plan V2 intégral gelable
2026-04-03  Sonde profonde repo — 23 écarts, 7 bloquants, 4 doublons
2026-04-03  CE DOCUMENT — V2 Recalibré gelable
```

### 0.2 Delta V2→V2-RECAL (sonde profonde)

| Élément | V2 original | V2 Recalibré | Justification |
|---|---|---|---|
| Migrations slots | 058–063 | **060–065** | 058 = idx m13_correction_log (existe), 059 = score_history M14 (existe). Head actuel = 059. |
| H0 durée | 5 jours | **3 jours** | m12_correction_writer acquis (7/7 méthodes, 26 tests). |
| H1 scope | M13 from scratch (60 fichiers) | **Audit-patch M13 + agent foundation** | M13 V5 DONE (ADR-M13-001, 42+ fichiers, 19 YAML). Écarts identifiés : RequirementsInstantiator partiel, BenchmarkStatusService stub, tests manquants. |
| H1 durée | 14 jours | **10 jours** | Core M13 acquis. |
| evaluation_documents write_owner | m13_regulatory_engine | **m14_evaluation_repository** | C'est M14 qui persiste cette table (m14_evaluation_repository.py). |
| market_signals bridge | market_signals | **market_signals_v2** | Table renommée en migration 043. |
| m12_correction_log.event_time | Supposé existant | **Absent** — proxy = created_at | Migration 054 n'a pas event_time. Ajout en migration 062. |
| Stop signals | 22 | **25** | +3 : chaine migration, table fantôme, write_owner violation. |
| Risques | 16 | **18** | +2 : pgvector Railway, M13 audit régression. |
| Durée totale | 9 semaines | **~8 semaines** | Acquis H0/H1. |

### 0.3 Décision architecturale CTO intégrée

```
DÉCISION ARCHITECTURALE — INTÉGRÉE V2

1. INFRASTRUCTURE (tables, triggers, event index, matrice souveraineté,
   correction logs, embeddings, projections)
   → BUILD AS PLANNED V1. Aucune modification.
   → C'est la mémoire long terme de l'agent, pas son pipeline.

2. NOYAU RÉGLEMENTAIRE (DGMP Mali seuils, obligations légales,
   RegimeResolver, RequirementsInstantiator, gate assembly rules)
   → DÉTERMINISTE OBLIGATOIRE. Lookup YAML. Pas d'inférence.

3. LOGIQUE DE TRAITEMENT (comment un dossier est analysé)
   → AGENTIQUE. Les passes 1A→1D et 2A deviennent des tools.
   → L'agent décide quels tools appeler selon complexité du dossier.

4. GATES INTER-HORIZONS (H0→H1→H2→H3→H4)
   → MAINTENUES BLOQUANTES. Discipline de build inchangée.
   → Séquencement intra-dossier = flexible (agent-driven).

5. LLM DANS M13
   → AUTORISÉ pour raisonnement (analyse clauses ambiguës,
     qualification dérogations complexes).
   → INTERDIT pour le noyau déterministe (seuils, procédures,
     documents requis = lookup YAML uniquement).
```

---

## §1 — THÈSE ARCHITECTURALE

### 1.1 Problème racine

DMS a des organes déconnectés. Les tables existent, les triggers existent, les docs existent — mais le tissu applicatif qui fait circuler le sang entre les organes est absent ou partiel. 8 tables append-only avec 8 schémas différents, aucune fédération. Un `m12_correction_log` documenté avec un writer fonctionnel (acquis) mais non branché dans les routes. Un `memory_entries` avec alimentation partielle (`add_memory()` générique). Un pgvector provisionné mais jamais utilisé.

### 1.2 Solution — Architecture deux niveaux

```
┌──────────────────────────────────────────────────────────┐
│                    NIVEAU INTELLIGENCE                    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │  AGENT LLM (orchestrateur de raisonnement)       │    │
│  │                                                    │    │
│  │  Décide quels tools appeler selon le dossier      │    │
│  │  Observé par Langfuse (traces, coût, qualité)     │    │
│  │  Plafonné en autonomie (matrice AUTO/ASSIST/HUMAN)│    │
│  └────────────┬───────────────────────────┬──────────┘    │
│               │ appelle                   │ appelle       │
│  ┌────────────▼─────────┐  ┌──────────────▼───────────┐  │
│  │  TOOLS DÉTERMINISTES │  │  TOOLS LLM-ASSISTED      │  │
│  │                      │  │                          │  │
│  │  classify_document() │  │  resolve_ambiguity()     │  │
│  │  resolve_regime()    │  │  assess_complex_clause() │  │
│  │  instantiate_reqs()  │  │  extract_unstructured()  │  │
│  │  assemble_gates()    │  │  propose_derogation()    │  │
│  │  map_principles()    │  │  find_similar_cases()    │  │
│  └──────────┬───────────┘  └────────────┬─────────────┘  │
│             │ lit/écrit                  │ lit/écrit      │
└─────────────┼────────────────────────────┼───────────────┘
              │                            │
┌─────────────▼────────────────────────────▼───────────────┐
│                  NIVEAU INFRASTRUCTURE                     │
│                                                           │
│  Tables append-only    Event index fédéré    Embeddings   │
│  Correction logs       Matrice souveraineté  Projections  │
│  Mercuriale/Dict       ARQ job queue         Langfuse     │
│  YAML configs          Golden dataset        RAGAS evals  │
│                                                           │
│  TOUT EST DÉTERMINISTE, VERSIONNÉ, TRAÇABLE               │
│  RIEN NE CHANGE QUAND L'AGENT ÉVOLUE                     │
└───────────────────────────────────────────────────────────┘
```

### 1.3 Séquence non négociable

```
ALIGNER (H0) → RÉGULER (H1) → MÉMORISER+ORCHESTRER (H2) → COMPRENDRE (H3) → MONTRER (H4)
```

Gates bloquantes entre chaque horizon. Le séquencement intra-dossier est agent-driven.

### 1.4 Ce que V2 refuse

| Refus | Raison |
|---|---|
| Réécriture Couche B / mercuriale / dictionnaire | Existant fonctionne. L'enrichir, pas le remplacer. |
| Event index qui remplace les tables sources | Fédérer, pas dupliquer. Pointeurs, pas copies. |
| Embedding via API externe (OpenAI, Cohere) | Modèle local uniquement. Souveraineté données. |
| `all-MiniLM-L6-v2` | Obsolète. Documents FR longs. BGE-M3 minimum. |
| RAG sans reranker | 25% précision perdue. Cross-encoder obligatoire. |
| Pipeline sans job queue | BackgroundTasks = perte silencieuse sur crash. ARQ obligatoire. |
| H3 sans golden dataset | "Tests passent" ≠ "système meilleur". RAGAS obligatoire. |
| Agent sans observabilité | Boîte noire. Langfuse obligatoire. |
| CandidateRule appliquée automatiquement | L'humain valide toujours. |
| Mode production sans benchmark ≥ 50 cases | Bootstrap = bootstrap. |
| Semantic caching en H3 | Luxe. Pas avant 1000+ queries/jour. H4+ si besoin. |

---

## §2 — PRINCIPES NON NÉGOCIABLES — 16 RÈGLES

| # | Principe | Formulation | Scope | Vérification |
|---|---|---|---|---|
| P1 | Aligner avant d'écrire | Pas de code sans vérification matrice souveraineté | Tout | Matrice consultée dans chaque PR |
| P2 | Câbler avant de construire | Connecter l'existant avant d'ajouter du neuf | H0 | Audit H0 prouve la connexion |
| P3 | Fédérer, ne pas dupliquer | Event index pointe vers tables, ne copie pas payloads | H2 | `source_table + source_pk`, summary minimal |
| P4 | Le feedback est le produit | Sans corrections qui remontent, DMS ne vit pas | H0+ | Writer + pattern + candidate = chaîne complète |
| P5 | La mémoire est le moat | Ce que DMS accumule = avantage compétitif | H2+ | Chaque case enrichit la mémoire |
| P6 | Zéro doublon | Chaque donnée a UN propriétaire, UN chemin d'écriture | Tout | Matrice souveraineté l'impose |
| P7 | Bitemporal là où ça compte | Quand c'est arrivé ≠ quand on l'a su | H2 | `event_time ≠ ingestion_time` |
| P8 | Déterministe pour l'infra et le noyau réglementaire | Lookup YAML pour seuils, procédures, documents requis | H1+ | Tests déterministes, 0 variance |
| P9 | L'humain valide toujours les mutations de config | Aucune mutation auto de YAML | H2+ | CandidateRule → review → apply |
| P10 | Append-only par défaut | Tout nouveau log/event/trace est append-only | Tout | Tests DB vérifient triggers |
| P11 | Gates bloquantes entre horizons | Aucun H(n+1) sans H(n) validé | Tout | Done binaire vérifié |
| P12 | Code concret, pas concepts | Chaque composant a modèles, services, tests spécifiés | Tout | Ce document les contient |
| P13 | Vue produit = preuve de vie | Invisible de l'utilisateur = pas vivant | H4 | 3 vues fonctionnelles |
| P14 | Souveraineté documentaire | Doc gelé = état exact du repo | Tout | Alignement vérifié H0 |
| P15 | Observabilité obligatoire pour tout appel LLM | Chaque prompt tracé (tokens, latence, coût, qualité) | H3+ | Langfuse opérationnel |
| P16 | Evals avant production | Golden dataset + métriques objectives avant toute claim de qualité | H3 | RAGAS ≥ baseline sur golden set |

---

## §3 — ARCHITECTURE DEUX NIVEAUX

### 3.1 Niveau Infrastructure — Composants

```
PERSISTANCE
├── Tables append-only existantes (10)
│   ├── pipeline_runs / pipeline_step_runs
│   ├── score_runs
│   ├── committee_events / submission_registry_events
│   ├── decision_snapshots
│   ├── m12_correction_log
│   ├── m13_correction_log
│   ├── analysis_summaries
│   ├── score_history / elimination_log
│   └── audits
├── Tables CRUD existantes
│   ├── memory_entries
│   ├── procurement_dict_items / aliases
│   ├── mercurials / mercuriale_sources
│   ├── market_signals_v2 / decision_history
│   ├── imc_category_item_map
│   ├── evaluation_documents
│   └── m13_regulatory_profile_versions
├── Tables nouvelles (V2 — migrations 060–065)
│   ├── dms_event_index (fédéré, bitemporal, append-only) — 061
│   ├── candidate_rules (lifecycle: proposed→approved→applied) — 063
│   ├── rule_promotions (append-only) — 063
│   ├── dms_embeddings (vector 1024d, upsert) — 064
│   └── llm_traces (backup Langfuse) — 065
├── Matviews
│   └── market_coverage (auto-refresh trigger — 060)
├── Extensions
│   └── pgvector (activé en 064)
└── Agent tables existantes (045)
    ├── couche_a.agent_checkpoints
    └── couche_a.agent_runs_log

ORCHESTRATION
├── ARQ + Redis (job queue, retry, persistance)
└── Worker pool (embedding batch, pattern detection, pipeline)

OBSERVATION
├── Langfuse (traces LLM, évaluation, coût)
├── RAGAS (métriques qualité RAG)
└── Golden dataset (50 cases annotés, immuables)

CONFIGURATION
├── YAML réglementaires (SCI, DGMP Mali — 19 fichiers existants)
├── Event types registry (config/events/event_types.yaml)
├── Autonomy thresholds
└── Matrice souveraineté (document gelé)
```

### 3.2 Niveau Intelligence — Composants

```
AGENT ORCHESTRATEUR
├── Agent M12 (classification + linking)
│   ├── Tool: classify_document()      [déterministe]
│   ├── Tool: assess_validity()        [déterministe]
│   ├── Tool: signal_conformity()      [déterministe]
│   ├── Tool: link_process()           [déterministe]
│   └── Tool: resolve_ambiguity()      [LLM-assisted, conf ≤ 0.70]
├── Agent M13 (regulatory profiling) — services EXISTANTS wrappés
│   ├── Tool: resolve_regime()         [déterministe - lookup YAML]
│   ├── Tool: instantiate_requirements() [déterministe]
│   ├── Tool: assemble_gates()         [déterministe]
│   ├── Tool: assess_derogation()      [HYBRID — déterministe + LLM cas complexes]
│   ├── Tool: map_principles()         [déterministe]
│   └── Tool: analyze_clause()         [LLM-assisted]
├── RAG Pipeline
│   ├── Chunker sémantique (articles, lots, clauses)
│   ├── Embedder BGE-M3 (dense + sparse)
│   ├── Retriever hybride (vector + sparse + déterministe)
│   ├── Reranker BGE-reranker-v2-m3
│   └── Context assembler (pour LLM)
└── Learning Pipeline
    ├── Pattern detector (sur correction logs)
    ├── Candidate rule generator
    └── Auto-calibrator (paliers benchmark)
```

### 3.3 Frontière stricte entre niveaux

| Règle | Formulation | Conséquence |
|---|---|---|
| F1 | L'infrastructure ne dépend jamais de l'agent | Si l'agent change de modèle LLM, aucune migration DB |
| F2 | L'agent lit et écrit via les interfaces définies | Pas d'accès SQL direct depuis l'agent |
| F3 | Les tools déterministes sont testables sans LLM | `pytest` suffit, pas besoin de mock LLM |
| F4 | Les tools LLM-assisted sont observés par Langfuse | Chaque appel tracé |
| F5 | L'agent ne mute jamais les YAML directement | Il propose via CandidateRule |

### 3.4 Classification des tools

```python
class ToolClassification(str, Enum):
    DETERMINISTIC = "deterministic"
    LLM_ASSISTED = "llm_assisted"
    HYBRID = "hybrid"


class ToolManifest(BaseModel):
    tool_name: str
    classification: ToolClassification
    description: str
    input_schema: dict
    output_schema: dict
    confidence_floor: float
    confidence_ceiling: float
    llm_model: Optional[str] = None
    langfuse_trace_name: Optional[str] = None
    autonomy_level: Literal["AUTO", "ASSIST", "HUMAN"]

    model_config = ConfigDict(extra="forbid")
```

---

## §4 — MATRICE DE SOUVERAINETÉ DES ARTEFACTS (CORRIGÉE)

### 4.1 Format

```yaml
artifact_name:
  nature: source_of_truth | append_only_log | sealed_snapshot |
          read_projection | case_memory | market_memory |
          derived_summary | federated_index | vector_index |
          human_feedback_log | execution_trace | config_source |
          job_queue
  layer: couche_a | couche_b | procurement | transversal | memory | orchestration
  write_owner: "<service unique>"
  read_allowed: [<lecteurs autorisés>]
  temporal_model: ingestion_only | bitemporal | versioned | derived
  append_only: true | false
  migration_ref: "<numéro>"
```

### 4.2 Couche B — Mémoire Marché & Normalisation (11 artefacts)

```yaml
procurement_dict_items:
  nature: source_of_truth
  layer: couche_b
  write_owner: dictionary_service
  read_allowed: [all]
  temporal_model: versioned
  append_only: false
  migration_ref: "MRD series"

procurement_dict_aliases:
  nature: source_of_truth
  layer: couche_b
  write_owner: dictionary_service
  read_allowed: [all]
  temporal_model: versioned
  append_only: false
  migration_ref: "MRD series"

dict_collision_log:
  nature: append_only_log
  layer: couche_b
  write_owner: dictionary_service_trigger
  read_allowed: [audit, dictionary_service, calibration]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "MRD series"

mercurials:
  nature: source_of_truth
  layer: couche_b
  write_owner: mercuriale_ingestion
  read_allowed: [all]
  temporal_model: versioned
  append_only: false
  migration_ref: "024, 040"

mercuriale_sources:
  nature: source_of_truth
  layer: couche_b
  write_owner: mercuriale_ingestion
  read_allowed: [all]
  temporal_model: versioned
  append_only: false
  migration_ref: "024"

mercuriale_raw_queue:
  nature: append_only_log
  layer: couche_b
  write_owner: mercuriale_ingestion
  read_allowed: [mercuriale_ingestion, audit]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "024"

market_signals_v2:  # CORRIGÉ — était "market_signals" dans V2
  nature: market_memory
  layer: couche_b
  write_owner: signal_engine
  read_allowed: [api, couche_a, event_index, retrieval, price_check]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "043"

market_coverage:
  nature: read_projection
  layer: couche_b
  write_owner: auto_refresh_trigger  # trigger AFTER INSERT market_signals_v2
  read_allowed: [api, couche_a, retrieval]
  temporal_model: derived
  append_only: false
  migration_ref: "042, 060"
  notes: "MATERIALIZED VIEW. Auto-refresh après INSERT market_signals_v2 (trigger 060)."

decision_history:
  nature: market_memory
  layer: couche_b
  write_owner: price_check_engine
  read_allowed: [api, couche_a, retrieval, event_index]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "044"

imc_category_item_map:
  nature: source_of_truth
  layer: couche_b
  write_owner: imc_service
  read_allowed: [all]
  temporal_model: versioned
  append_only: false
  migration_ref: "046"

vendors:
  nature: source_of_truth
  layer: couche_b
  write_owner: vendor_service
  read_allowed: [all]
  temporal_model: versioned
  append_only: false
  migration_ref: "041"
```

### 4.3 Couche A — Pipeline & Exécution (9 artefacts)

```yaml
pipeline_runs:
  nature: execution_trace
  layer: couche_a
  write_owner: pipeline_orchestrator
  read_allowed: [api, audit, event_index, benchmark]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "032"

pipeline_step_runs:
  nature: execution_trace
  layer: couche_a
  write_owner: pipeline_orchestrator
  read_allowed: [api, audit, event_index, benchmark]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "033"

analysis_summaries:
  nature: derived_summary
  layer: couche_a
  write_owner: pipeline_analysis
  read_allowed: [api, retrieval, event_index]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "035"
  notes: "pipeline_run_id nullable (blocked paths). Rendre systématique en H0."

memory_entries:
  nature: case_memory
  layer: couche_a
  write_owner: case_memory_writer  # V2 : CaseMemoryWriter remplace add_memory() générique
  read_allowed: [api, annotation, retrieval, embedding_service, agent]
  temporal_model: ingestion_only
  append_only: false
  migration_ref: "002"
  notes: "content_json JSONB porte le payload structuré CaseMemoryEntry."

score_runs:
  nature: append_only_log
  layer: couche_a
  write_owner: scoring_engine
  read_allowed: [api, audit, event_index]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "026"

committee_events:
  nature: append_only_log
  layer: couche_a
  write_owner: committee_service
  read_allowed: [api, audit, event_index]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "028"

submission_registry_events:
  nature: append_only_log
  layer: couche_a
  write_owner: submission_service
  read_allowed: [api, audit, event_index]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "036"

decision_snapshots:
  nature: sealed_snapshot
  layer: couche_a
  write_owner: committee_service  # seal_committee_decision()
  read_allowed: [api, audit, retrieval, event_index]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "029"

audits:
  nature: append_only_log
  layer: couche_a
  write_owner: audit_triggers
  read_allowed: [all]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "010, 038"
```

### 4.4 Couche A — Agents (2 artefacts existants)

```yaml
agent_checkpoints:
  nature: execution_trace
  layer: couche_a
  write_owner: agent_framework  # src/couche_a/agents/framework.py
  read_allowed: [agent_framework, audit]
  temporal_model: ingestion_only
  append_only: false
  migration_ref: "045"

agent_runs_log:
  nature: execution_trace
  layer: couche_a
  write_owner: agent_framework
  read_allowed: [agent_framework, audit, event_index]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "045"
```

### 4.5 Procurement — M12/M13/M14 (5 artefacts)

```yaml
m12_correction_log:
  nature: human_feedback_log
  layer: procurement
  write_owner: m12_correction_writer  # ACQUIS — src/procurement/m12_correction_writer.py
  read_allowed: [pattern_detector, benchmark, event_index, calibrator, agent]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "054"
  notes: "event_time absent — ajouté en migration 062 (bitemporal). Proxy = created_at."

m13_correction_log:
  nature: human_feedback_log
  layer: procurement
  write_owner: m13_correction_writer  # À CRÉER en H1
  read_allowed: [pattern_detector, benchmark, event_index, calibrator, agent]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "057, 058"

evaluation_documents:
  nature: case_memory
  layer: procurement
  write_owner: m14_evaluation_repository  # CORRIGÉ — était "m13_regulatory_engine" dans V2
  read_allowed: [m14, api, audit, agent]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "056"
  notes: "M14 persiste scores_matrix, justifications. RLS via cases.tenant_id."

score_history:
  nature: append_only_log
  layer: procurement
  write_owner: m14_engine
  read_allowed: [api, audit, event_index]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "059"

elimination_log:
  nature: append_only_log
  layer: procurement
  write_owner: m14_engine
  read_allowed: [api, audit, event_index]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "059"
```

### 4.6 Transversal — Créés par V2 (4 artefacts)

```yaml
dms_event_index:
  nature: federated_index
  layer: transversal
  write_owner: bridge_triggers + event_index_service
  read_allowed: [all]
  temporal_model: bitemporal
  append_only: true
  migration_ref: "061"  # CORRIGÉ — était 059
  notes: >
    Index de navigation, PAS source de vérité.
    source_table + source_pk pour jointure vers payload complet.
    summary JSONB minimal pour queries transversales.
    aggregate_version pour optimistic locking (nullable).
    idempotency_key pour safe retry (nullable).

candidate_rules:
  nature: append_only_log
  layer: transversal
  write_owner: candidate_rule_generator
  read_allowed: [learning_console, calibrator, cto, agent]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "063"  # CORRIGÉ — était 061
  notes: "Status transitions: proposed → approved/rejected → applied"

rule_promotions:
  nature: append_only_log
  layer: transversal
  write_owner: promotion_service
  read_allowed: [learning_console, audit, calibrator]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "063"  # CORRIGÉ — était 061

llm_traces:
  nature: append_only_log
  layer: transversal
  write_owner: langfuse_integration
  read_allowed: [learning_console, audit, calibrator]
  temporal_model: ingestion_only
  append_only: true
  migration_ref: "065"  # CORRIGÉ — était 063
  notes: "Backup local des traces Langfuse. Champs critiques uniquement."
```

### 4.7 Memory — Créé en H3 (1 artefact)

```yaml
dms_embeddings:
  nature: vector_index
  layer: memory
  write_owner: embedding_service
  read_allowed: [rag_service, similar_cases, retrieval, agent]
  temporal_model: ingestion_only
  append_only: false
  migration_ref: "064"  # CORRIGÉ — était 062
  notes: "Upsert par source_type+source_id. BGE-M3 1024d. Nécessite pgvector."
```

### 4.8 Orchestration — Créé en H2 (1 artefact logique)

```yaml
arq_job_queue:
  nature: job_queue
  layer: orchestration
  write_owner: arq_workers
  read_allowed: [api, monitoring]
  temporal_model: ephemeral
  append_only: false
  notes: "Redis-backed. Jobs transitoires. Résultats persistés dans tables."
```

### 4.9 Totaux

```
Artefacts existants : 26 (24 V2 original + score_history + elimination_log de 059)
Artefacts nouveaux V2 : 7
Total : 33 artefacts sous gouvernance
```

### 4.10 Règle d'usage

```
AVANT TOUT WRITE DANS UNE TABLE :
1. Ouvrir DMS_ARTIFACT_SOVEREIGNTY_MATRIX.yaml
2. Trouver la table cible
3. Vérifier que le service = write_owner
4. Si non → STOP + validation CTO pour mise à jour matrice
5. Si table absente → STOP + ajouter avec classification

AVANT TOUTE NOUVELLE TABLE :
1. Prouver qu'aucun artefact existant ne peut porter le besoin
2. Classifier selon le format matrice
3. Valider CTO
4. Ajouter à la matrice AVANT le code
```

---

## §5 — H0 : FONDATIONS (RECALIBRÉ)

**Durée** : 3 jours (réduit de 5 — writer M12 acquis)
**Objectif** : câbler ce qui existe, classifier ce qui est, prouver terrain sain
**Nouvelles tables** : 0
**Nouvelles migrations** : 1 (060 — trigger auto-refresh)
**Gate de sortie** : 7 conditions

### H0.1 — Matrice de souveraineté

**Livrables** :

```
docs/freeze/DMS_ARTIFACT_SOVEREIGNTY_MATRIX.yaml
docs/freeze/DMS_ARTIFACT_SOVEREIGNTY_MATRIX.md
```

Contenu : §4 de ce document extrait en YAML + markdown lisible. Gelé dans le repo.

**Effort** : 0.5j

### H0.2 — `m12_correction_writer` — ACQUIS

**Statut** : FAIT. `src/procurement/m12_correction_writer.py` — 7/7 méthodes, 26 tests.

Méthodes : `write()`, `write_batch()`, `count_total()`, `count_by_field()`, `count_by_document()`, `get_recent()`, `rate_last_30d()`.

**Effort** : 0j (vérification gate seulement)

### H0.3 — `market_coverage` auto-refresh

**Livrable** :

```
alembic/versions/060_market_coverage_auto_refresh.py
tests/db_integrity/test_market_coverage_auto_refresh.py
```

**Migration** : trigger `AFTER INSERT ON market_signals_v2 FOR EACH STATEMENT` → `REFRESH MATERIALIZED VIEW CONCURRENTLY market_coverage`. Exception catchée pour ne pas bloquer l'INSERT.

**Pré-requis** : unique index `idx_market_coverage_pk` sur `(item_id, zone_id)` — EXISTE (migration 042).

**down_revision** : `059_m14_score_history_elimination_log`

**Effort** : 0.5j

### H0.4 — `memory_entries` pipeline writer

**Livrables** :

```
src/annotation/memory/case_memory_writer.py
tests/annotation/memory/test_case_memory_writer.py
```

**Modèle** :

```python
class CaseMemoryEntry(BaseModel):
    case_id: str = Field(..., min_length=1)
    documents_count: int = Field(..., ge=0)
    document_kinds: list[str]
    document_subtypes: list[str] = []
    framework_detected: str
    framework_confidence: float = Field(..., ge=0.0, le=1.0)
    other_frameworks: list[str] = []
    procurement_family: str
    estimated_value: Optional[float] = None
    currency: Optional[str] = None
    zone_scope: list[str] = []
    suppliers_detected: list[str] = []
    buyer_detected: Optional[str] = None
    procedure_reference: Optional[str] = None
    links_count: int = 0
    unresolved_count: int = 0
    m12_confidence_avg: float = Field(..., ge=0.0, le=1.0)
    m12_confidence_min: float = Field(..., ge=0.0, le=1.0)
    review_flags: list[str] = []
    created_at: str

    model_config = ConfigDict(extra="forbid")
```

Upsert dans `memory_entries` par `case_id` (entry_type = `"case_summary"`). Le payload structuré est sérialisé dans `content_json` JSONB — pas besoin de migration schéma.

Builder `build_from_m12_output()` inclus. Hook `PostPass1DCallback` pour branchement ultérieur.

**Effort** : 1j

### H0.5 — Audit tables semi-mortes

**Livrables** :

```
scripts/probe_h0_table_health.py
docs/audit/H0_TABLE_HEALTH_REPORT.md
```

Probe : `decision_snapshots` (count, without_case_id, last_write), `analysis_summaries` (count, without_pipeline_run_id, orphaned), `memory_entries` (count, last_write).

Actions selon résultats documentées dans le rapport.

**Effort** : 0.5j

### H0.6 — Probe gates M13

**Livrable** : `scripts/probe_m13_h0_gates.py`

3 conditions : `evaluation_documents` existe, RLS policy couvre `regulatory_profile`, FSM accepte Pass 2A.

**Effort** : 0.25j

### H0.7 — Alignement doc/git

**Livrable** : mise à jour `MRD_CURRENT_STATE.md` si nécessaire.

**Effort** : 0.25j

### H0 — Gate de sortie

| # | Condition | Vérificateur |
|---|---|---|
| G0.1 | Matrice souveraineté gelée dans repo | `ls docs/freeze/DMS_ARTIFACT_SOVEREIGNTY_MATRIX.yaml` |
| G0.2 | `m12_correction_writer` tests passent (ACQUIS) | `pytest tests/procurement/test_m12_correction_writer.py` |
| G0.3 | `market_coverage` refresh automatique | `pytest tests/db_integrity/test_market_coverage_auto_refresh.py` |
| G0.4 | `CaseMemoryWriter` tests passent | `pytest tests/annotation/memory/test_case_memory_writer.py` |
| G0.5 | Health report produit et reviewé | Fichier existe + CTO review |
| G0.6 | Probe M13 : 3/3 | `python scripts/probe_m13_h0_gates.py` |
| G0.7 | Doc/git synchrones | Vérification manuelle |

**Toutes les 7 conditions TRUE avant H1.**

### H0 — Fichiers

| # | Fichier | Type | Statut |
|---|---|---|---|
| 1 | `docs/freeze/DMS_ARTIFACT_SOVEREIGNTY_MATRIX.yaml` | Doc | À créer |
| 2 | `docs/freeze/DMS_ARTIFACT_SOVEREIGNTY_MATRIX.md` | Doc | À créer |
| 3 | `docs/audit/H0_TABLE_HEALTH_REPORT.md` | Doc | À créer |
| 4 | `src/procurement/m12_correction_writer.py` | Code | **ACQUIS** |
| 5 | `src/annotation/memory/case_memory_writer.py` | Code | À créer |
| 6 | `alembic/versions/060_market_coverage_auto_refresh.py` | Migration | À créer |
| 7 | `tests/procurement/test_m12_correction_writer.py` | Test | **ACQUIS** |
| 8 | `tests/annotation/memory/test_case_memory_writer.py` | Test | À créer |
| 9 | `tests/db_integrity/test_market_coverage_auto_refresh.py` | Test | À créer |
| 10 | `scripts/probe_h0_table_health.py` | Script | À créer |
| 11 | `scripts/probe_m13_h0_gates.py` | Script | À créer |
| **Total H0** | **9 à créer + 2 acquis = 11** | | **3 jours** |

---

## §6 — H1 : AUDIT M13 + AGENT FOUNDATION (RECALIBRÉ)

**Durée** : 10 jours (réduit de 14 — M13 core acquis)
**Précondition** : H0 Gate 7/7

### 6.1 — Phase A : Audit-Patch M13 (4 jours)

M13 V5 est DONE (ADR-M13-001, 42+ fichiers, 19 YAML). Écarts identifiés par sonde :

| Écart | Fichier impacté | Action |
|---|---|---|
| RequirementsInstantiator : eval weights non chargés depuis YAML | `src/procurement/requirements_instantiator.py` | Charger technical_weight, financial_weight, sustainability_weight |
| RequirementsInstantiator : approval_chain toujours `[]` | `src/procurement/requirements_instantiator.py` | Lookup YAML si disponible |
| BenchmarkStatusService = stub (retourne zeros) | `src/procurement/benchmark_status_service.py` | Brancher metrics réelles depuis correction_logs + pipeline_runs |
| DerogationAssessor : security heuristic narrow | `src/procurement/derogation_assessor.py` | Élargir avec signal M12 security_context |
| OCDS coverage statique | `src/procurement/ocds_coverage_builder.py` | Rendre case-driven (optionnel si non gate) |
| Tests manquants : assembler phases | `tests/procurement/test_compliance_gate_assembler.py` | Créer |
| Tests manquants : derogations | `tests/procurement/test_derogation_assessor.py` | Créer |
| Tests manquants : principles mapper | `tests/procurement/test_principles_mapper.py` | Créer |
| Tests manquants : DGMP single-framework | `tests/procurement/test_regime_resolver.py` | Ajouter cas DGMP |
| Tests manquants : benchmark service | `tests/procurement/test_benchmark_status_service.py` | Créer |
| m13_correction_writer absent | `src/procurement/m13_correction_writer.py` | Créer (pattern m12_correction_writer) |
| m13_correction_writer tests | `tests/procurement/test_m13_correction_writer.py` | Créer |

### 6.2 — Phase B : Agent Foundation (4 jours)

**Livrables** :

```
src/agents/tools/tool_manifest.py
src/agents/tools/regulatory_tools.py
src/agents/tools/__init__.py
tests/agents/tools/test_regulatory_tools.py
tests/agents/tools/test_tool_manifest.py
data/golden/README.md
scripts/eval_against_golden.py
```

Les services M13 existants (RegimeResolver, RequirementsInstantiator, ComplianceGateAssembler, DerogationAssessor, PrinciplesMapper) sont wrappés en tools avec `ToolManifest`. Les tools LLM-assisted (analyze_clause, assess_complex_derogation) sont en placeholder `review_required: True`.

### 6.3 — Phase C : Validation (2 jours)

- Probe 60/60 fichiers M13 (`scripts/probe_m13_files.py` existant)
- Case réel SCI traverse M12→M13 complet
- Tool registry ≥ 6 tools enregistrés
- Golden dataset ≥ 10 cases annotés

### H1 — Gate de sortie

| # | Condition |
|---|---|
| G1.1 | Probe M13 fichiers : tous présents |
| G1.2 | Tous les tests M13 passent (existants + nouveaux) |
| G1.3 | Un case SCI réel traverse M12→M13 complet |
| G1.4 | `RegulatoryComplianceReport` persisté dans `evaluation_documents` |
| G1.5 | 9 principes dans la map, SUSTAINABILITY présent |
| G1.6 | `m13_correction_writer` opérationnel |
| G1.7 | Tool registry contient ≥ 6 tools enregistrés |
| G1.8 | Golden dataset structure posée, ≥ 10 cases annotés |
| G1.9 | Tools déterministes testables sans LLM (pytest suffit) |

### H1 — Fichiers

| Composant | Fichiers | Total |
|---|---|---|
| Audit-patch M13 (modifs) | ~6 fichiers modifiés | 6 |
| Nouveaux tests M13 | 5 fichiers | 5 |
| m13_correction_writer + test | 2 fichiers | 2 |
| Agent tool manifest + wrappers + tests | 5 fichiers | 5 |
| Golden dataset + eval script | 2 fichiers | 2 |
| **Total H1** | | **~20 fichiers** |

---

## §7 — H2 : MÉMOIRE STRUCTURÉE + ORCHESTRATION

**Durée** : 12 jours
**Précondition** : H1 Gate 9/9

### 7.1 — Event Index Fédéré

**Migration** : `061_dms_event_index.py` (down_revision: `060_market_coverage_auto_refresh`)

```sql
CREATE TABLE dms_event_index (
    id BIGSERIAL,
    event_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    event_domain TEXT NOT NULL,
    source_table TEXT NOT NULL,
    source_pk BIGINT NOT NULL,
    case_id TEXT,
    supplier_id TEXT,
    item_id TEXT,
    document_id TEXT,
    aggregate_type TEXT NOT NULL,
    aggregate_id TEXT,
    event_type TEXT NOT NULL,
    aggregate_version BIGINT,
    idempotency_key TEXT,
    event_time TIMESTAMPTZ NOT NULL,
    ingestion_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    summary JSONB NOT NULL DEFAULT '{}',
    source_hash TEXT,
    schema_version TEXT NOT NULL DEFAULT '1.0',
    PRIMARY KEY (id, ingestion_time)
) PARTITION BY RANGE (ingestion_time);

CREATE TABLE dms_event_index_2025_h2 PARTITION OF dms_event_index
    FOR VALUES FROM ('2025-07-01') TO ('2027-01-01');

CREATE INDEX idx_event_case ON dms_event_index (case_id, event_time) WHERE case_id IS NOT NULL;
CREATE INDEX idx_event_type ON dms_event_index (event_type, event_time);
CREATE INDEX idx_event_domain ON dms_event_index (event_domain, event_time);
CREATE UNIQUE INDEX idx_event_source ON dms_event_index (source_table, source_pk, ingestion_time);
CREATE UNIQUE INDEX idx_event_aggregate_version
    ON dms_event_index (aggregate_type, aggregate_id, aggregate_version)
    WHERE aggregate_version IS NOT NULL;
CREATE UNIQUE INDEX idx_event_idempotency ON dms_event_index (idempotency_key)
    WHERE idempotency_key IS NOT NULL;
CREATE INDEX idx_event_summary ON dms_event_index USING GIN (summary jsonb_path_ops);
```

Append-only triggers + 11 bridge triggers (m12_correction_log, m13_correction_log, pipeline_runs, pipeline_step_runs, score_runs, committee_events, submission_registry_events, decision_snapshots, analysis_summaries, **market_signals_v2**, agent_runs_log).

**Bridge m12_correction_log note** : utilise `created_at` comme proxy event_time jusqu'à migration 062.

### 7.2 — Bitemporal Additions

**Migration** : `062_bitemporal_columns.py` (down_revision: `061_dms_event_index`)

```sql
ALTER TABLE m12_correction_log ADD COLUMN IF NOT EXISTS event_time TIMESTAMPTZ;
UPDATE m12_correction_log SET event_time = created_at WHERE event_time IS NULL;

ALTER TABLE decision_snapshots ADD COLUMN IF NOT EXISTS event_time TIMESTAMPTZ;
UPDATE decision_snapshots SET event_time = created_at WHERE event_time IS NULL;

ALTER TABLE market_signals_v2 ADD COLUMN IF NOT EXISTS event_time TIMESTAMPTZ;
UPDATE market_signals_v2 SET event_time = created_at WHERE event_time IS NULL;

ALTER TABLE decision_history ADD COLUMN IF NOT EXISTS event_time TIMESTAMPTZ;
UPDATE decision_history SET event_time = created_at WHERE event_time IS NULL;
```

### 7.3 — Feedback Loop + CandidateRule

**Migration** : `063_candidate_rules.py` (down_revision: `062_bitemporal_columns`)

```sql
CREATE TABLE candidate_rules (
    id SERIAL PRIMARY KEY,
    rule_id TEXT UNIQUE NOT NULL,
    origin TEXT NOT NULL,
    target_config TEXT NOT NULL,
    change_type TEXT NOT NULL,
    change_detail JSONB NOT NULL,
    source_pattern_id TEXT,
    source_corrections_count INT,
    source_field_path TEXT,
    status TEXT NOT NULL DEFAULT 'proposed',
    proposed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    reviewed_by TEXT,
    review_notes TEXT,
    applied_at TIMESTAMPTZ,
    CONSTRAINT valid_status CHECK (status IN ('proposed','approved','rejected','applied'))
);

CREATE TABLE rule_promotions (
    id SERIAL PRIMARY KEY,
    candidate_rule_id TEXT NOT NULL REFERENCES candidate_rules(rule_id),
    promotion_type TEXT NOT NULL,
    config_file_path TEXT NOT NULL,
    config_diff TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    applied_by TEXT NOT NULL,
    rollback_possible BOOLEAN DEFAULT TRUE,
    rollback_diff TEXT
);

CREATE INDEX idx_candidate_rules_status ON candidate_rules (status);
```

### 7.4 — Services H2

```
src/memory/event_index_service.py
src/memory/event_index_models.py
src/memory/pattern_detector.py
src/memory/pattern_models.py
src/memory/candidate_rule_generator.py
src/memory/deterministic_retrieval.py
src/memory/retrieval_models.py
src/workers/arq_config.py
src/workers/arq_tasks.py
config/events/event_types.yaml
```

### 7.5 — ARQ + Redis

Nouvelle dépendance : `arq>=0.26.0` dans `requirements.txt`.
Redis déjà présent (`redis==5.2.1`). docker-compose déjà configuré.

### H2 — Gate de sortie

| # | Condition |
|---|---|
| G2.1 | `dms_event_index` créé, partitionné, append-only vérifié |
| G2.2 | 11 bridge triggers actifs |
| G2.3 | INSERT `m12_correction_log` → event dans index (end-to-end) |
| G2.4 | `aggregate_version` + `idempotency_key` contraints fonctionnent |
| G2.5 | `case_timeline()` retourne résultats sur case réel |
| G2.6 | Bitemporal colonnes sur 4 tables |
| G2.7 | `PatternDetector` détecte ≥ 1 pattern |
| G2.8 | ≥ 1 `CandidateRule` status=proposed |
| G2.9 | Retrieval déterministe retourne ≥ 1 cas similaire |
| G2.10 | Aucun payload complet dans summary (audit) |
| G2.11 | ARQ workers démarrables, Redis connecté |
| G2.12 | `event_types.yaml` gelé ≥ 35 event types |

### H2 — Fichiers

| # | Fichier | Type |
|---|---|---|
| 1 | `alembic/versions/061_dms_event_index.py` | Migration |
| 2 | `alembic/versions/062_bitemporal_columns.py` | Migration |
| 3 | `alembic/versions/063_candidate_rules.py` | Migration |
| 4 | `src/memory/event_index_service.py` | Code |
| 5 | `src/memory/event_index_models.py` | Code |
| 6 | `src/memory/pattern_detector.py` | Code |
| 7 | `src/memory/pattern_models.py` | Code |
| 8 | `src/memory/candidate_rule_generator.py` | Code |
| 9 | `src/memory/deterministic_retrieval.py` | Code |
| 10 | `src/memory/retrieval_models.py` | Code |
| 11 | `src/workers/arq_config.py` | Code |
| 12 | `src/workers/arq_tasks.py` | Code |
| 13 | `config/events/event_types.yaml` | Config |
| 14 | `tests/memory/test_event_index_service.py` | Test |
| 15 | `tests/memory/test_pattern_detector.py` | Test |
| 16 | `tests/memory/test_candidate_rule_generator.py` | Test |
| 17 | `tests/memory/test_deterministic_retrieval.py` | Test |
| 18 | `tests/db_integrity/test_event_index_append_only.py` | Test |
| 19 | `tests/db_integrity/test_bridge_triggers.py` | Test |
| 20 | `tests/workers/test_arq_tasks.py` | Test |
| **Total H2** | **20 fichiers** | **12 jours** |

---

## §8 — H3 : INTELLIGENCE — RAG PRODUCTION-GRADE

**Durée** : 16 jours
**Précondition** : H2 Gate 12/12

### 8.1 — Migrations H3

**Migration** : `064_dms_embeddings.py` (down_revision: `063_candidate_rules`)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE dms_embeddings (
    id SERIAL PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    embedding_dense vector(1024) NOT NULL,
    embedding_sparse JSONB DEFAULT '{}',
    content_text TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source_type, source_id)
);

CREATE INDEX idx_embeddings_source ON dms_embeddings (source_type, source_id);
CREATE INDEX idx_embeddings_hash ON dms_embeddings (content_hash);
CREATE INDEX idx_embeddings_sparse ON dms_embeddings USING GIN (embedding_sparse);
```

**Migration** : `065_llm_traces.py` (down_revision: `064_dms_embeddings`)

```sql
CREATE TABLE llm_traces (
    id SERIAL PRIMARY KEY,
    trace_id TEXT NOT NULL,
    trace_name TEXT NOT NULL,
    case_id TEXT,
    document_id TEXT,
    model TEXT,
    tokens_in INT,
    tokens_out INT,
    latency_ms INT,
    cost_usd FLOAT,
    quality_score FLOAT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_llm_traces_case ON llm_traces (case_id);
CREATE INDEX idx_llm_traces_name ON llm_traces (trace_name);
```

### 8.2 — Nouvelles dépendances (requirements.txt)

```
FlagEmbedding>=1.3.0
sentence-transformers>=3.0.0
langfuse>=2.0.0
ragas>=0.2.0
pgvector>=0.3.0
```

### 8.3 — Services H3

| Composant | Fichier | Rôle |
|---|---|---|
| Chunker sémantique | `src/memory/chunker.py` + `chunker_models.py` | Découpe docs par section logique (article, lot, clause) |
| Embedding BGE-M3 | `src/memory/embedding_service.py` + `embedding_models.py` | Dense 1024d + sparse, local, 0 API externe |
| Reranker | `src/memory/reranker.py` | Cross-encoder BGE-reranker-v2-m3, local |
| RAG Service | `src/memory/rag_service.py` + `rag_models.py` | Pipeline complet chunk→embed→retrieve→rerank→assemble. Conf ≤ 0.70, review_required=True systématiquement |
| Langfuse | `src/memory/langfuse_integration.py` + `config/langfuse/langfuse_config.yaml` | Self-hosted Railway, trace chaque appel LLM |
| RAGAS | `src/evals/ragas_evaluator.py` + `golden_dataset_loader.py` | Métriques faithfulness, relevance, recall, precision |
| Auto-calibrator | `src/memory/auto_calibrator.py` + `calibration_models.py` | Paliers 60→500, propose recalibrations |

### H3 — Gate de sortie

| # | Condition |
|---|---|
| G3.1 | `dms_embeddings` table créée, `vector(1024)` |
| G3.2 | BGE-M3 chargé et fonctionnel (local, 0 API externe) |
| G3.3 | Chunker sémantique découpe un DAO réel en sections logiques |
| G3.4 | ≥ 100 embeddings dense+sparse dans la table |
| G3.5 | `find_similar_hybrid()` retourne résultats pertinents |
| G3.6 | Reranker améliore le top-5 vs sans reranker |
| G3.7 | IVFFlat index créé après premier batch |
| G3.8 | RAG service résout ≥ 1 ambiguïté réelle |
| G3.9 | RAG confidence ≤ 0.70 vérifié par test |
| G3.10 | RAG `review_required` = True systématiquement |
| G3.11 | Langfuse opérationnel, traces visibles |
| G3.12 | `llm_traces` table alimentée (backup local) |
| G3.13 | Golden dataset ≥ 50 cases annotés |
| G3.14 | RAGAS evaluation exécutée, baseline définie |
| G3.15 | Aucune régression RAGAS vs baseline |
| G3.16 | Auto-calibrator détecte ≥ 1 dégradation ou confirme santé |

### H3 — Fichiers

| # | Fichier | Type |
|---|---|---|
| 1 | `alembic/versions/064_dms_embeddings.py` | Migration |
| 2 | `alembic/versions/065_llm_traces.py` | Migration |
| 3 | `src/memory/chunker.py` | Code |
| 4 | `src/memory/chunker_models.py` | Code |
| 5 | `src/memory/embedding_service.py` | Code |
| 6 | `src/memory/embedding_models.py` | Code |
| 7 | `src/memory/reranker.py` | Code |
| 8 | `src/memory/rag_service.py` | Code |
| 9 | `src/memory/rag_models.py` | Code |
| 10 | `src/memory/langfuse_integration.py` | Code |
| 11 | `src/memory/auto_calibrator.py` | Code |
| 12 | `src/memory/calibration_models.py` | Code |
| 13 | `src/evals/ragas_evaluator.py` | Code |
| 14 | `src/evals/golden_dataset_loader.py` | Code |
| 15 | `config/langfuse/langfuse_config.yaml` | Config |
| 16 | `tests/memory/test_chunker.py` | Test |
| 17 | `tests/memory/test_embedding_service.py` | Test |
| 18 | `tests/memory/test_reranker.py` | Test |
| 19 | `tests/memory/test_rag_service.py` | Test |
| 20 | `tests/memory/test_langfuse_integration.py` | Test |
| 21 | `tests/memory/test_auto_calibrator.py` | Test |
| 22 | `tests/evals/test_ragas_evaluator.py` | Test |
| 23 | `scripts/run_ragas_eval.py` | Script |
| **Total H3** | **23 fichiers** | **16 jours** |

---

## §9 — H4 : VUES PRODUIT

**Durée** : 10 jours
**Précondition** : H2 Gate 12/12 (H3 pas requis — parallélisable)

### 9.1 — Case Timeline

Agrège events de `dms_event_index` par case. Groupés par phase.

### 9.2 — Market Memory Card

Pour item/zone/fournisseur : prix historiques, signaux, couverture, historique décisionnel.

### 9.3 — Learning Console

Corrections récentes, patterns détectés, candidate rules, taux, drift, RAGAS metrics.

### 9.4 — Routes API

```
GET  /views/case/{case_id}/timeline
GET  /views/market/{item_id}?zone=...
GET  /views/learning/console
GET  /views/learning/patterns
GET  /views/learning/rules?status=...
POST /views/learning/rules/{rule_id}/approve
POST /views/learning/rules/{rule_id}/reject
GET  /views/learning/ragas-history
```

### H4 — Gate de sortie

| # | Condition |
|---|---|
| G4.1 | Case Timeline visible sur case réel ≥ 5 events |
| G4.2 | Market Card visible sur item réel avec prix + signaux |
| G4.3 | Learning Console montre corrections + patterns + mode |
| G4.4 | Approve/reject routes fonctionnelles |
| G4.5 | Toutes les vues lisent sources canoniques (pas de cache custom) |
| G4.6 | RAGAS history visible si H3 complété |

### H4 — Fichiers

| # | Fichier | Type |
|---|---|---|
| 1 | `src/api/views/case_timeline.py` | Code |
| 2 | `src/api/views/case_timeline_models.py` | Code |
| 3 | `src/api/views/market_memory_card.py` | Code |
| 4 | `src/api/views/market_memory_models.py` | Code |
| 5 | `src/api/views/learning_console.py` | Code |
| 6 | `src/api/views/learning_console_models.py` | Code |
| 7 | `src/api/routes/views.py` | Code |
| 8 | `tests/api/views/test_case_timeline.py` | Test |
| 9 | `tests/api/views/test_market_memory_card.py` | Test |
| 10 | `tests/api/views/test_learning_console.py` | Test |
| **Total H4** | **10 fichiers** | **10 jours** |

---

## §10 — CONTRATS D'INTERFACE INTER-HORIZONS

### H0 → H1

| Produit par H0 | Consommé par H1 | Contrat |
|---|---|---|
| Matrice souveraineté | Toute PR M13 audit | Consulté avant chaque write |
| `m12_correction_writer` (ACQUIS) | BenchmarkStatusService | `rate_last_30d()` |
| `evaluation_documents` confirmé | M14 EvaluationDocumentRepository | Table + RLS |
| `CaseMemoryWriter` | M13 lit case summaries | JSON schema stable dans content_json |

### H1 → H2

| Produit par H1 | Consommé par H2 | Contrat |
|---|---|---|
| `m13_correction_log` + writer | Event bridge + PatternDetector | Table schema |
| `evaluation_documents` peuplé | Event bridge | JSON schema `regulatory_profile` |
| 19 YAML configs (ACQUIS) | CandidateRule target_config | Chemins fichiers stables |
| Tool registry ≥ 6 tools | Agent orchestration | `ToolManifest` schema stable |
| Golden dataset ≥ 10 cases | Accumulation continue | `GoldenCase` schema stable |

### H2 → H3

| Produit par H2 | Consommé par H3 | Contrat |
|---|---|---|
| `dms_event_index` | RAG lookup corrections | Query interface stable |
| `PatternDetector` | Auto-calibrator | `CorrectionPattern` model |
| `DeterministicRetrieval` | RAG fallback | `find_similar()` interface |
| `memory_entries` peuplé (via CaseMemoryWriter) | Embedding service | JSON schema `CaseMemoryEntry` |
| ARQ workers | Embedding batch, pipeline | `WorkerSettings` config |
| Golden dataset ≥ 30 cases | RAGAS evaluation | `GoldenCase` schema |

### H2 → H4

| Produit par H2 | Consommé par H4 | Contrat |
|---|---|---|
| `dms_event_index` | Case Timeline | Query interface |
| `PatternDetector` | Learning Console | `CorrectionPattern` model |
| `candidate_rules` table | Learning Console, routes | Table schema |

---

## §11 — GOUVERNANCE DES GATES

### Protocole

```
1. Exécutant déclare "horizon terminé"
2. Done binaire vérifié item par item
3. Tests automatisés exécutés (pytest)
4. Probes exécutés (scripts)
5. CTO vérifie sur données réelles (pas mock)
6. CTO signe GATE PASSED ou GATE BLOCKED + raisons
7. Si BLOCKED : corrections, retour étape 1
8. Si PASSED : horizon suivant peut démarrer
```

### Protocole de rollback

Si horizon échoue après 3 tentatives :
1. Documenter dans `docs/audit/`
2. Réduire scope (retirer composants bloquants)
3. Livrer scope réduit
4. Reporter bloquants à horizon suivant
5. Ne jamais bloquer indéfiniment

### Matrice

| Gate | Conditions | Blocker absolu |
|---|---|---|
| H0→H1 | 7 conditions | Matrice gelée + CaseMemoryWriter testée + probe 3/3 |
| H1→H2 | 9 conditions | Case réel traversé + tools enregistrés + M13 gaps patchés |
| H2→H3 | 12 conditions | Event index + pattern + retrieval + ARQ |
| H2→H4 | = H2 gate | Parallélisable avec H3 |
| H3→DONE | 16 conditions | RAG + reranker + Langfuse + RAGAS baseline |
| H4→DONE | 6 conditions | Vues fonctionnelles données réelles |

---

## §12 — MATRICE ANTI-COLLISION

| Livrable | Artefact existant | Stratégie | Risque |
|---|---|---|---|
| `CaseMemoryWriter` | `memory_entries` (002) | Écrit JSON structuré dans content_json | Compatibilité JSON |
| `market_coverage` refresh | Matview (042) + script | Trigger AFTER INSERT market_signals_v2 | Performance batch |
| `dms_event_index` | 10 tables append-only | Fédère via bridges, proxy created_at pour event_time | Bridge triggers migration |
| Bitemporal columns | 4 tables existantes | Ajoute nullable event_time | Backfill données anciennes |
| `PatternDetector` | correction_logs (054, 057) | Lit uniquement | Aucun |
| `CandidateRuleGenerator` | YAML configs (19 fichiers) | Propose modifications | P9 protège |
| `candidate_rules` | Aucun existant | Nouvelle table | Aucun |
| `dms_embeddings` | pgvector provisionné mais jamais utilisé | Première utilisation | RAM Railway |
| `EmbeddingService` BGE-M3 | Aucun | Nouveau | RAM ~2GB |
| `CrossEncoderReranker` | Aucun | Nouveau | RAM additionnel |
| `SemanticChunker` | Aucun | Nouveau | Regex FR coverage |
| `RAGService` | correction_logs + embeddings | Lit, n'écrit pas | Conf plafonnée 0.70 |
| `LangfuseIntegration` | Aucun | Nouveau | Railway container |
| `llm_traces` | `audits` table (010) | Séparé — scope LLM uniquement | Clarification frontière |
| ARQ workers | BackgroundTasks existant (routers.py) | Remplace progressivement | Migration progressive |
| RAGAS evaluator | golden JSONL + validate_annotation.py | Complète | Golden dataset effort |
| Tool wrappers | Services M13 existants (m13_engine.py) | Wrappent | Interface stable |
| Case Timeline | `dms_event_index` (061) | Lit | Aucun |
| Market Card | Couche B tables | Lit | Aucun |
| Learning Console | Tout | Lit, écrit rien | Aucun |

---

## §13 — INVENTAIRE FICHIERS COMPLET

### Totaux par horizon

| Horizon | Migrations | Code | Config/Docs | Tests | Scripts | Total |
|---|---|---|---|---|---|---|
| H0 | 1 | 1 | 3 | 2 | 2 | **9 (+ 2 acquis)** |
| H1 | 0 | ~8 (patches + nouveaux) | 1 | ~10 | 1 | **~20** |
| H2 | 3 | 9 | 1 | 7 | 0 | **20** |
| H3 | 2 | 12 | 1 | 7 | 1 | **23** |
| H4 | 0 | 7 | 0 | 3 | 0 | **10** |
| **Total** | **6** | **~37** | **6** | **~29** | **4** | **~82 nouveaux + acquis** |

---

## §14 — SÉQUENCE D'EXÉCUTION (RECALIBRÉE)

```
SEMAINE 1      ─── H0 : FONDATIONS (3j) ──────────────────────
  Lun          Matrice souveraineté (draft + CTO review)
  Mar          CaseMemoryWriter (code + tests)
  Mer          Auto-refresh trigger 060 + probes + alignement
               ══════ GATE H0 : 7/7 → CTO signe ══════

SEMAINE 2-3    ─── H1 : AUDIT M13 + AGENT (10j) ─────────────
  S2 Lun-Mer   Audit-patch M13 (RequirementsInstantiator, Benchmark, Derogation)
  S2 Jeu-Ven   Tests manquants M13 + m13_correction_writer
  S3 Lun-Mer   ToolManifest + regulatory tool wrappers
  S3 Jeu-Ven   Golden dataset foundation + validation
               ══════ GATE H1 : 9/9 → CTO signe ══════

SEMAINE 4-5    ─── H2 : MÉMOIRE + ORCHESTRATION (12j) ────────
  S4 Lun-Mar   Migration 061 event index + bridges
  S4 Mer       Migration 062 bitemporal
  S4 Jeu-Ven   EventIndexService + tests
  S5 Lun       Migration 063 candidate_rules
  S5 Mar-Mer   PatternDetector + CandidateRuleGenerator
  S5 Jeu       DeterministicRetrieval
  S5 Ven       ARQ workers + tests
               ══════ GATE H2 : 12/12 → CTO signe ══════

SEMAINE 6-8    ─── H3 : INTELLIGENCE (16j) ────────────────────
  S6 Lun-Mar   Migration 064 embeddings + 065 llm_traces + deps
  S6 Mer-Ven   SemanticChunker + EmbeddingService BGE-M3
  S7 Lun-Mer   Reranker + RAGService complet
  S7 Jeu-Ven   Langfuse integration + traces
  S8 Lun-Mer   RAGAS evaluator + golden dataset completion (50 cases)
  S8 Jeu-Ven   Auto-calibrator + batch embedding production
               ══════ GATE H3 : 16/16 → CTO signe ══════

SEMAINE 6-8    ─── H4 : VUES PRODUIT (10j, parallèle H3) ─────
  S6 Lun-Mer   Case Timeline
  S6 Jeu-Ven   Market Memory Card
  S7 Lun-Mar   Learning Console
  S7 Mer-Ven   Routes API + intégration + données réelles
               ══════ GATE H4 : 6/6 → CTO signe ══════

SEMAINE 8      ─── VALIDATION FINALE ──────────────────────────
  Lun          Probe complet tous fichiers
  Mar          RAGAS final run sur golden dataset
  Mer          End-to-end : document → pipeline → RAG → vue
  Jeu          Audit matrice souveraineté vs repo réel
  Ven          DMS VIVANT → CTO signe FREEZE
```

**Total : ~8 semaines.**

---

## §15 — STOP SIGNALS — 25

| # | Signal | Horizon | Conséquence |
|---|---|---|---|
| S1 | Nouvelle table sans vérification matrice souveraineté | Tout | **STOP** |
| S2 | Schema change table existante sans migration Alembic | Tout | **STOP** |
| S3 | Duplication artefact existant | Tout | **STOP** |
| S4 | Event index remplace table au lieu de fédérer | H2 | **STOP** |
| S5 | Payload complet dans `dms_event_index.summary` | H2 | **STOP** |
| S6 | Embedding via API externe | H3 | **STOP** |
| S7 | CandidateRule appliquée sans validation humaine | H2+ | **STOP** |
| S8 | LLM dans noyau réglementaire M13 (seuils, procédures, docs requis) | H1 | **STOP** |
| S9 | H1 démarré sans H0 Gate 7/7 | H1 | **STOP** |
| S10 | H2 démarré sans H1 Gate 9/9 | H2 | **STOP** |
| S11 | H3 démarré sans H2 Gate 12/12 | H3 | **STOP** |
| S12 | Embeddings `vector(384)` au lieu de `vector(1024)` | H3 | **STOP** |
| S13 | RAG sans cross-encoder reranker | H3 | **STOP** |
| S14 | Appel LLM sans trace Langfuse | H3+ | **STOP** |
| S15 | H3 validé sans RAGAS baseline définie | H3 | **STOP** |
| S16 | RAGAS régression > 0.02 vs baseline sur golden set | H3+ | **STOP** |
| S17 | Mode production sans benchmark ≥ 50 cases | H1 | **STOP** |
| S18 | Bridge trigger manquant après ajout table append-only | H2+ | **STOP** |
| S19 | Migration sans downgrade fonctionnel | Tout | **STOP** |
| S20 | Write dans artefact sans être `write_owner` matrice | Tout | **STOP** |
| S21 | Appel API réel dans tests | Tout | **STOP** |
| S22 | Vue produit sans données réelles | H4 | **STOP** |
| S23 | Migration V2 avec down_revision ≠ chaîne attendue (head=059) | Tout | **STOP** |
| S24 | Bridge trigger sur `market_signals` au lieu de `market_signals_v2` | H2 | **STOP** |
| S25 | `evaluation_documents` write depuis M13 engine directement | Tout | **STOP** |

---

## §16 — DONE BINAIRE — 103 ITEMS

### H0 — Fondations (7 items)

- [ ] Matrice souveraineté gelée `docs/freeze/`
- [ ] `m12_correction_writer` : write retourne ID, tests passent, append-only (**ACQUIS**)
- [ ] `market_coverage` auto-refresh après INSERT `market_signals_v2`
- [ ] `CaseMemoryWriter` : `build_from_m12_output()` + write, tests passent
- [ ] Health report produit, anomalies documentées
- [ ] Probe M13 : 3/3 (evaluation_documents + RLS + FSM)
- [ ] Doc/git synchrones

### H1 — Audit M13 + Agent Foundation (20 items)

- [ ] RequirementsInstantiator chargement eval weights depuis YAML
- [ ] BenchmarkStatusService branché sur données réelles
- [ ] DerogationAssessor sécurité élargi (signal M12)
- [ ] Tests manquants M13 : assembler phases, derogations, principles, DGMP, benchmark (5 fichiers)
- [ ] `m13_correction_writer` opérationnel
- [ ] Probe M13 fichiers : tous présents
- [ ] Tous les tests M13 passent (existants + nouveaux)
- [ ] Un case SCI réel traverse M12→M13 complet
- [ ] `RegulatoryComplianceReport` persisté dans `evaluation_documents`
- [ ] 9 principes dans la map, SUSTAINABILITY présent
- [ ] `RegimeResolver` résout SCI et DGMP Mali
- [ ] Threshold matching avec override par famille
- [ ] Framework MIXED → plus strict, UNKNOWN → output dégradé
- [ ] Gate assembly 4 phases
- [ ] Dérogations humanitarian + sole_source + security
- [ ] Tool registry ≥ 6 tools enregistrés
- [ ] Tools déterministes testables sans LLM
- [ ] Tools LLM-assisted retournent placeholder `review_required: True`
- [ ] Golden dataset ≥ 10 cases annotés
- [ ] `ToolManifest` schema gelé

### H2 — Mémoire + Orchestration (20 items)

- [ ] `dms_event_index` créé, partitionné, append-only
- [ ] `aggregate_version` + `idempotency_key` contraints
- [ ] 11 bridge triggers actifs
- [ ] INSERT `m12_correction_log` → event dans index (e2e)
- [ ] `case_timeline()` résultats sur case réel
- [ ] Bitemporal colonnes 4 tables
- [ ] Aucun payload complet dans summary
- [ ] `event_types.yaml` gelé ≥ 35 types
- [ ] `PatternDetector` ≥ 1 pattern
- [ ] Patterns classifiés severity
- [ ] `CandidateRuleGenerator` ≥ 1 rule status=proposed
- [ ] `candidate_rules` + `rule_promotions` tables
- [ ] `DeterministicRetrieval` ≥ 1 cas similaire
- [ ] Similarité explicable (reasons + differences)
- [ ] ARQ workers démarrables, Redis connecté
- [ ] `process_pipeline_case` task retry fonctionnel
- [ ] `run_pattern_detection` cron configuré
- [ ] Golden dataset ≥ 30 cases annotés
- [ ] Matrice anti-collision vérifiée chaque livrable H2
- [ ] Tous tests H2 passent

### H3 — Intelligence (20 items)

- [ ] `dms_embeddings` table `vector(1024)` + `embedding_sparse` JSONB
- [ ] BGE-M3 chargé, local, 0 API externe
- [ ] Chunker sémantique découpe DAO réel en sections logiques
- [ ] ≥ 100 embeddings dense+sparse
- [ ] `find_similar_hybrid()` résultats pertinents
- [ ] Reranker `bge-reranker-v2-m3` améliore top-5
- [ ] IVFFlat index créé après batch
- [ ] RAG service résout ≥ 1 ambiguïté réelle
- [ ] RAG confidence ≤ 0.70 (test)
- [ ] RAG `review_required` = True systématiquement (test)
- [ ] Langfuse opérationnel, traces visibles
- [ ] `llm_traces` table alimentée
- [ ] Chaque appel LLM tracé (tokens, latence, coût)
- [ ] Golden dataset ≥ 50 cases annotés
- [ ] RAGAS evaluation exécutée
- [ ] RAGAS baseline définie et sauvegardée
- [ ] Aucune régression RAGAS vs baseline
- [ ] Auto-calibrator ≥ 1 dégradation ou confirme santé
- [ ] Paliers calibration documentés
- [ ] Tous tests H3 passent

### H4 — Vues Produit (8 items)

- [ ] Case Timeline visible case réel ≥ 5 events
- [ ] Timeline agrège sources multiples (pipeline + feedback + regulatory)
- [ ] Market Card visible item réel avec prix + signaux
- [ ] Market Card montre fraîcheur + incertitude
- [ ] Learning Console corrections + patterns + mode
- [ ] Approve/reject routes fonctionnelles
- [ ] Vues lisent sources canoniques (pas cache custom)
- [ ] Tous tests H4 passent

### DMS Vivant — Critères finaux (8 items)

- [ ] Document traverse M12→M13 en < 60s (ARQ pipeline)
- [ ] Correction humaine → loguée → bridgée → pattern détectable
- [ ] Nouveau case montre 5 cas similaires (déterministe ou RAG)
- [ ] Benchmark recalibre aux paliers
- [ ] CandidateRules s'accumulent et sont reviewées
- [ ] Mercuriale refresh, signaux propagent
- [ ] Utilisateur voit timeline + mémoire marché + apprentissage
- [ ] 0 table orpheline, 0 artefact sans `write_owner`

---

## §17 — RISQUES ET MITIGATIONS — 18

| # | Risque | Prob. | Impact | Mitigation |
|---|---|---|---|---|
| R1 | `market_coverage` REFRESH trop lent | Moy. | Moy. | `pg_cron` 15min si > 2s |
| R2 | Bridge triggers lag | Faible | Haute | Monitor `pg_stat_user_tables` |
| R3 | BGE-M3 RAM > Railway tier | Moy. | Haute | Plan payant 8GB ou batch+unload |
| R4 | `memory_entries` JSON incompatible | Faible | Moy. | Probe H0 vérifie schema |
| R5 | `dms_event_index` trop gros | Faible | Moy. | Partition mensuelle, purge 24m |
| R6 | Corrections insuffisantes pour patterns | Haute | Moy. | Seuil 3 (pas 10) |
| R7 | RAG hallucine | Moy. | Haute | Conf plafonnée 0.70, review=True |
| R8 | Bridges cassent triggers existants | Faible | Haute | Staging DB tests avant prod |
| R9 | pgvector non activé Railway | Faible | Bloque H3 | Probe H0 vérifie extension |
| R10 | YAML configs erreurs seuils | Moy. | Haute | Benchmark 20+ cases |
| R11 | CandidateRule backlog infini | Moy. | Faible | Console alerte si > 20 pending |
| R12 | H3/H4 parallélisation conflits | Faible | Moy. | H4 = 0 migration |
| R13 | Reranker RAM additionnel vs embedder | Moy. | Moy. | Batch séquentiel, pas concurrent |
| R14 | Golden dataset annotation bottleneck | Haute | Haute | Start en H1, cible 10 par semaine |
| R15 | Langfuse Railway container limits | Moy. | Moy. | Template officiel Railway, monitor RAM |
| R16 | ARQ Redis connection perdue | Faible | Moy. | Reconnection automatique ARQ, health check 30s |
| R17 | pgvector non supporté par Railway PostgreSQL managed | Moy. | Bloque H3 | Probe H0 : `SELECT * FROM pg_available_extensions WHERE name = 'vector'` |
| R18 | M13 audit-patch casse tests existants | Faible | Moy. | Run full test suite après chaque patch |

---

## §18 — FORMULATION CANONIQUE

DMS VIVANT V2 Recalibré est un plan architectural en 5 horizons (H0→H4) qui transforme un système de traitement ponctuel à organes déconnectés en un système cumulatif à deux niveaux — infrastructure déterministe (tables, event index fédéré bitemporal, correction logs, embeddings, job queue, observabilité) et intelligence agentique (tools déterministes + LLM-assisted, RAG production-grade avec chunking sémantique, BGE-M3 dense+sparse, cross-encoder reranker, observabilité Langfuse, évaluation RAGAS).

Le recalibrage intègre l'état réel du repo post-M14 : 23 écarts identifiés, 7 bloquants résolus (renumerotation migrations 060–065, correction write_owners, market_signals_v2, M13 gaps patchés), 4 doublons/collisions éliminés. Le writer M12 et le core M13 sont acquis — H0 passe de 5j à 3j, H1 de 14j à 10j.

L'infrastructure ne dépend jamais de l'agent. Si le modèle LLM change demain, aucune migration DB. Chaque artefact (33 sous gouvernance) a un propriétaire unique vérifié par la matrice de souveraineté. Chaque appel LLM est tracé. Chaque correction humaine remonte en pattern détectable proposable comme CandidateRule. Chaque décision est visible de l'utilisateur via 3 vues produit.

~82 fichiers nouveaux + acquis existants. 6 migrations (060–065). 103 items done binaire. 25 stop signals. 18 risques documentés avec mitigations. 16 principes non négociables.

~8 semaines. Gates bloquantes. CTO valide chaque transition.

**Le statut passe de FREEZE CANDIDATE à FREEZE quand H0 Gate 7/7 est validée par le CTO et que la matrice de souveraineté est gelée dans le repo.**
