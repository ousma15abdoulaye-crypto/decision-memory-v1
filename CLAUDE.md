# DMS — Contexte Souverain Agent
## LIRE EN PREMIER — OBLIGATOIRE AVANT TOUT MANDAT

## HIÉRARCHIE DES SOURCES DE VÉRITÉ
Réf. **opposable** : `docs/freeze/CONTEXT_ANCHOR.md` — **RÈGLE-ANCHOR-10** (hiérarchie des autorités).

Ordre de primauté (du plus fort au plus faible) :
1. **Plan Directeur DMS V4.1** (document source). *Dans ce dépôt, le corps normatif gelé qui en matérialise le contenu est* **`docs/freeze/DMS_V4.1.0_FREEZE.md`** *(IMMUTABLE — jamais modifié hors processus ADR / GO CTO).*
2. **`docs/freeze/CONTEXT_ANCHOR.md`** — condensé opposable (E-01 à E-67).
3. **Mandats CTO** — instructions de session écrites.
4. **`docs/freeze/PIPELINE_REFONTE_FREEZE.md`** — cadrage pipeline annotation ; **ne prime jamais** sur 1–3.
5. **`CLAUDE.md`** (ce fichier) — aide-mémoire agent session ; **aucune autorité** au-dessus de 1–3.
6. **LLM (exécutant)** — zéro autorité propre (RÈGLE-ANCHOR-10 §4).

En cas de conflit : l’autorité de rang supérieur **prime** ; l’agent **STOP** et signale le CTO si le conflit implique le Plan Directeur ou l’anchor.
Conflit avec **`DMS_V4.1.0_FREEZE.md`** → STOP immédiat + GO CTO obligatoire.
L’agent **ne tranche jamais** un conflit entre sources d’autorité.

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
- **Merge vers `main` (ordre CTO)** : les **agents** exécutent **`.cursor/rules/dms-agent-mandate-protocol.mdc`** — **surveiller la PR** jusqu’à **CI vert**, traiter **Copilot / revue** et re-pousser, vérifier **`alembic heads` = une seule ligne** (**STOP-1** sinon), puis **merger** ; apply **Railway / prod** = runbook + GO CTO (non contourné par le merge Git).

## SIGNAUX STOP UNIVERSELS
STOP-1 : alembic heads > 1 ligne
STOP-2 : correction nécessite modifier migration existante
STOP-3 : logique métier ambiguë
STOP-4 : fichier hors périmètre doit être modifié
STOP-5 : conflit entre sources de vérité
