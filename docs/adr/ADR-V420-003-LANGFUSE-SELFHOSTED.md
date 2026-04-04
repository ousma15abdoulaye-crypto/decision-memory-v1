# ADR-V420-003 — Langfuse self-hosted sur Railway

**Statut** : ACCEPTÉ  
**Date** : 2026-04-04  
**Auteur** : Abdoulaye Ousmane — CTO  
**Référence** : DMS V4.2.0 ADDENDUM §VIII, ADR-H3-LANGFUSE-001 (existant)

---

## Contexte

L'ADR-H3-LANGFUSE-001 a déjà adopté Langfuse cloud pour la traçabilité LLM (M15/VIVANT V2).
V4.2.0 introduit un besoin de traçage par `workspace_id` + `tenant_id` — données métier
sensibles SCI Mali qui ne doivent pas transiter via un service cloud tiers.

## Décision

Déployer **Langfuse en self-hosted** via Docker sur Railway (service dédié), connecté au
PostgreSQL existant de DMS.

Ce document **complète** ADR-H3-LANGFUSE-001 pour le contexte workspace-first.

## Architecture

```
Railway Service "langfuse"
  Image : langfuse/langfuse:latest (Docker Hub officiel)
  PORT  : 3000 (interne Railway)
  DB    : DATABASE_URL DMS existant (schéma séparé `langfuse`)
  
DMS FastAPI
  LANGFUSE_HOST       : https://langfuse.railway.internal
  LANGFUSE_PUBLIC_KEY : (Railway secret)
  LANGFUSE_SECRET_KEY : (Railway secret)
```

## Traçage V4.2.0

Chaque trace Langfuse inclut :
```python
langfuse.trace(
    name="pass_minus_1",
    metadata={
        "workspace_id": workspace_id,
        "tenant_id": tenant_id,
        "pass": "pass_minus_1",
    }
)
```

Métriques tracées :
- Coût USD par workspace (OCR Mistral + classify Mistral Small)
- Latence par nœud LangGraph
- Taux d'échec OCR et fallback Azure
- HITL rate par tenant

## Raison : self-hosted vs cloud

| Critère | Self-hosted Railway | Cloud Langfuse |
|---|---|---|
| Données sensibles | Restent dans Railway | Envoyées cloud tiers |
| Coût | Inclus plan Railway Pro | $X/mois selon volume |
| Contrôle rétention | Total | Selon plan |
| Setup | Docker + Railway (1 service) | API key uniquement |

## Conséquences

- Semaine 1 Phase 1 : déployer service langfuse sur Railway
- Variables Railway à configurer : `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`
- Pas de nouvelle dépendance Python : `langfuse>=2.0.0` déjà dans requirements.txt (ADR-H3-LANGFUSE-001)
- PostgreSQL Langfuse : schéma `langfuse` dans la même DB (isolation par schéma)

---

*Complément à ADR-H3-LANGFUSE-001 pour le contexte workspace-first V4.2.0.*
