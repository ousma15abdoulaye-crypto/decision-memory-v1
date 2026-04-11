# Runbook — RAG corpus M12 (`dms_embeddings` + agent)

## Prérequis

- PostgreSQL avec extension `vector` (migration **064**).
- Migration **096** appliquée : `tenant_id` + RLS sur `public.dms_embeddings`.
- `alembic heads` : une seule tête, révision **`096_dms_embeddings_tenant_rls`** (ou postérieure).
- `DATABASE_URL` pointant vers la base cible.
- Un UUID valide dans `public.tenants` pour `--tenant-id`.

## Ingestion batch

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

## Activation agent

- Variable **`AGENT_RAG_ENABLED=true`** (Settings / Railway).
- Redémarrage du service API.
- Les questions orientées « corpus annoté » doivent router vers l’intent **`document_corpus`** (embeddings Mistral du routeur ≠ embeddings BGE du RAG ; le RAG utilise uniquement `EmbeddingService`).

## Rollback

1. Désactiver **`AGENT_RAG_ENABLED`** (retour immédiat au message « RAG désactivé »).
2. En cas de régression schéma : **`alembic downgrade`** vers **095** uniquement avec **GO CTO** et sauvegarde.

## Séquence staging → prod (rappel)

| Étape | Action |
|-------|--------|
| 1 | `alembic upgrade head` sur staging |
| 2 | Ingest JSONL sur staging + `count(*)` |
| 3 | `AGENT_RAG_ENABLED=true` sur staging, test manuel `POST /api/agent/prompt` |
| 4 | Répéter sur prod (fenêtre bas trafic) avec GO CTO |
