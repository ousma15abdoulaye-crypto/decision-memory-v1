# DMS — Contexte Souverain Agent
## LIRE EN PREMIER — OBLIGATOIRE AVANT TOUT MANDAT

## HIÉRARCHIE DES SOURCES DE VÉRITÉ
1. docs/freeze/DMS_V4.1.0_FREEZE.md          — IMMUABLE — supérieur à tout
2. docs/freeze/CONTEXT_ANCHOR.md              — état courant — E-01 à E-67
3. docs/freeze/PIPELINE_REFONTE_FREEZE.md     — pipeline annotation
4. CLAUDE.md (ce fichier)                     — gouvernance agent session
En cas de conflit → source de rang inférieur cède.
En cas de conflit avec 1 → STOP immédiat + GO CTO obligatoire.
L'agent ne tranche jamais un conflit de sources.

## KILL LIST — REJET IMMÉDIAT
- confidence hors {0.6, 0.8, 1.0}
- confidence=0.0 dans squelette JSON prompt (E-65)
- to_name="text" dans backend.py (E-66) — valeur correcte = "document_text"
- null libre hors ABSENT / NOT_APPLICABLE / AMBIGUOUS
- text_len seul comme critère OCR (E-22)
- router sans routing_evidence + routing_failure_reason
- statut "validated" seul — valeur correcte = "annotated_validated"
- schema_validator.py modifié sans GO CTO explicite
- winner / rank / recommendation / best_offer (RÈGLE-09 V4.1.0)
- implémentation sans mandat CTO émis explicitement (E-67)
- travail direct sur branche main
- fichier hors périmètre modifié sans GO CTO

## ERREURS CAPITALISÉES
Lire docs/freeze/CONTEXT_ANCHOR.md — E-01 à E-67 — intégralement.
Ces erreurs ont coûté des sessions entières. Elles ne se reproduisent pas.

## FLUX CANONIQUE PIPELINE
ingestion → router → extracteur spécialisé → validator → Label Studio

## STATUTS CANONIQUES
annotated_validated | review_required | rejected

## CONFIDENCE AUTORISÉE
{0.6, 0.8, 1.0} — aucune autre valeur
NOT_APPLICABLE → confidence=1.0 par convention (E-65 LOI 4)

## VALEURS D'ABSENCE
ABSENT | NOT_APPLICABLE | AMBIGUOUS

## FREEZE ACTIFS
schema-freeze-v1.0    : DMSExtractionResult — intouchable sans GO CTO
validator-freeze-v1.0 : schema_validator.py — intouchable sans GO CTO

## FICHIERS INTOUCHABLES SANS MANDAT DÉDIÉ
alembic/versions/                     — JAMAIS sans mandat alembic dédié
services/annotation-backend/prompts/schema_validator.py
docs/freeze/DMS_V4.1.0_FREEZE.md     — JAMAIS — immuable

## STACK
FastAPI + PostgreSQL + Railway + Mistral API + Label Studio
OpenRouter pour orchestration LLM — Windows PowerShell
wc et cat absents — utiliser Get-Content + Measure-Object

## RÈGLES PÉRIMÈTRE
- Modifier uniquement les fichiers listés dans le mandat
- Fichier hors liste → STOP + signaler CTO immédiatement (RÈGLE-ORG-07)
- 1 mandat = 1 branche = 1 PR (RÈGLE-01)
- Jamais travailler sur main
- Merge = humain uniquement (RÈGLE-ORG-10)

## SIGNAUX STOP UNIVERSELS
STOP-1 : alembic heads > 1 ligne
STOP-2 : correction nécessite modifier migration existante
STOP-3 : logique métier ambiguë
STOP-4 : fichier hors périmètre doit être modifié
STOP-5 : conflit entre sources de vérité
