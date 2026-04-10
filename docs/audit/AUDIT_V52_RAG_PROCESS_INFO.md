# Audit V5.2 — RAG process_info_handler (E-20)

## Ecart E-20 : process_info_handler sans RAG reel

### Statut : Dette documentee — mandat CTO requis

### Probleme identifie
`src/agent/handlers/process_info.py` repond aux questions reglementaires
(seuils ECHO, decrets, plafonds) avec des reponses statiques/hardcodees.
Aucune ancrage dans une base documentaire (PDF decrets, circulaires, etc.).

### Impact
- Reponses potentiellement obsoletes si les seuils changent
- Pas de reference documentaire opposable
- Agent ne peut pas citer ses sources sur process_info

### Architecture cible (V5.3)

```
process_info query
    → semantic_router (PROCESS_INFO)
    → rag_retriever.query(query, top_k=5)
        → pgvector embeddings sur table regulatory_documents
    → LLM synthesis avec sources citees
    → SSE stream avec metadata sources
```

### Tables a creer (migration separee)

- `regulatory_documents` : id, title, content, embedding VECTOR(1024), category, source_url
- `regulatory_chunks` : id, document_id, chunk_idx, content, embedding VECTOR(1024)

### Prerequis mandat CTO

1. Definition corpus documentaire (decrets, circulaires, seuils ECHO)
2. Pipeline ingestion PDF → chunks → embeddings
3. Migration pgvector regulatory_documents
4. ADR architecture RAG process_info

### Ecart ouvert depuis
P3 — Phase P3 Observabilite + Agent (radiographie O11)
