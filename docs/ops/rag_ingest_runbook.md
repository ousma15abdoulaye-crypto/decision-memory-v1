# Runbook — RAG corpus M12 (`dms_embeddings` + agent)

## Phases mandat (séparation des risques)

| Phase | Contenu | Critère « done » |
|-------|---------|------------------|
| **T1a** | Ingestion batch + retrieval DB (`find_similar_hybrid_async`) + tests mémoire / CLI | Embeddings présents, requêtes SQL/RLS OK, tests verts |
| **T1b** | Branchement handler agent sous `AGENT_RAG_ENABLED` | SSE document_corpus OK **après** T1a et D4.5 |

T1a et T1b ne se valident pas mutuellement : un retrieval sain n’implique pas un routage agent / latence SSE / guardrails OK.

## Règles binaires (production)

1. **Aucune activation du handler RAG en production sans T2** : migration **096** appliquée (`tenant_id` + RLS sur `public.dms_embeddings`). L’API refuse le flux RAG avec un message explicite si la colonne `tenant_id` est absente (garde-fou runtime `dms_embeddings_tenant_isolation_ready`).
2. **T1a seul** (ingest + retrieval sans agent, ou agent désactivé) : autorisé en local, staging isolé, ou corpus explicitement non sensible — pas de contournement de l’isolation tenant en prod multi-tenant.
3. **Observabilité** : **interdit** d’enregistrer le texte brut des chunks ou des passages dans Langfuse / spans / logs applicatifs structurés du retrieval. Autorisé : `query_length`, `k`, `hit_count`, `chunk_ids` (ids base), scores agrégés, durées, modèle.

## Prérequis

- PostgreSQL avec extension `vector` (migration **064**).
- Migration **096** appliquée : `tenant_id` + RLS sur `public.dms_embeddings`.
- `alembic heads` : une seule tête, révision **`096_dms_embeddings_tenant_rls`** (ou postérieure).
- `DATABASE_URL` pointant vers la base cible.
- Un UUID valide dans `public.tenants` pour `--tenant-id`.

### Convention `source_table` / `source_pk` (figée)

À répliquer telle quelle dans le script d’ingest :

- **`source_table`** : littéral fixe `m12_corpus_line` (constante `_SOURCE_TABLE` dans `scripts/ingest_embeddings.py`).
- **`source_pk`** : entier déterministe dérivé **uniquement** de `stable_m12_corpus_line_id(line)` puis `stable_source_pk(lid)` (voir docstring du script).
- **`chunk_index`** : ordinal **0-based** du chunk sur la ligne (découpeur sémantique). Une seule chaîne de dérivation — pas d’alternative « hash ou id » au choix.

## Ingestion batch (T1a)

```bash
# Simulation (aucune écriture)
python scripts/ingest_embeddings.py --input data/annotations/m12_corpus_from_ls.jsonl \
  --tenant-id <UUID_TENANT> --dry-run --limit 20

# Réel (BGE si BGE_MODEL_PATH défini, sinon stub hash — même backend que la requête RAG)
python scripts/ingest_embeddings.py --input data/annotations/m12_corpus_from_ls.jsonl \
  --tenant-id <UUID_TENANT>
```

Post-check :

```sql
SELECT count(*) FROM public.dms_embeddings WHERE tenant_id = '<UUID_TENANT>'::uuid;
```

## Index IVFFlat (volumétrie)

Voir [embeddings_index_runbook.md](embeddings_index_runbook.md) après premier chargement significatif.

## Séquence DevOps (staging → prod)

| Étape | Action |
|-------|--------|
| D4 | `alembic upgrade head` (096) sur l’environnement |
| D5 | Ingest JSONL + `count(*)` par tenant |
| **D4.5** | **Validation retrieval seule** (obligatoire avant agent) : requêtes connues, top-k attendu, **zéro fuite inter-tenant** (tests / requêtes sous `app.current_tenant`), latence mesurée, taux de hits acceptable |
| D6 | `AGENT_RAG_ENABLED=true` + redémarrage API |
| D7 | Tests manuels `POST /api/agent/prompt` (intent document_corpus) |
| D8 | Répéter sur prod (fenêtre bas trafic) avec **GO CTO** |

## Activation agent (T1b)

- Variable **`AGENT_RAG_ENABLED=true`** (Settings / Railway).
- Redémarrage du service API.
- Les questions orientées « corpus annoté » routent vers **`document_corpus`** (embeddings Mistral du routeur ≠ embeddings BGE du RAG).

### Contrat handler `document_corpus`

- **Autorisé** : contenu documentaire, références de procédure, présence/absence, extraction / reformulation descriptive, synthèse factuelle des passages.
- **Interdit** : recommandation fournisseur, classement, « meilleure offre », conclusion attributive, conseil de décision (aligné RÈGLE-09).

## Rollback

1. Désactiver **`AGENT_RAG_ENABLED`** (retour immédiat au message « RAG désactivé »).
2. En cas de régression schéma : **`alembic downgrade`** vers **095** uniquement avec **GO CTO** et sauvegarde.

## Definition of Done (compléments)

- [ ] Convention `source_table` / `source_pk` / `chunk_index` figée et documentée (script + ce runbook).
- [ ] Aucun texte brut de chunk dans Langfuse / logs structurés RAG (retrieval).
- [ ] Aucune exécution handler RAG sans colonne **`tenant_id`** sur **`dms_embeddings`** (garde-fou runtime).
- [ ] Retrieval seul validé (D4.5) avant branchement agent.
