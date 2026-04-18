# CONDITION 2 — ISSUE LEGACY DOCUMENTÉE

**Date** : 2026-04-17  
**Référence** : MANDAT_P3.2 Article 10, Condition 2  

---

## ISSUE À OUVRIR SUR GITHUB

**Titre** : `[LEGACY] get_latest_score_run AttributeError dans pipeline service`

**Body** :

```markdown
## Contexte

Bug legacy identifié lors de l'ouverture du mandat P3.2 Scoring Engine.

## Symptôme

```
AttributeError: module 'src.couche_a.pipeline.service' has no attribute 'get_latest_score_run'
```

## Localisation

- Fichier : `src/couche_a/pipeline/service.py` 
- Fonction manquante : `get_latest_score_run`

## Analyse

Cette fonction fait partie du système de scoring **legacy V1** (`ScoringEngine` + table `score_runs`).

Le pipeline V5 (`pipeline_v5_service.py`) **n'utilise pas** ce système legacy — il a été remplacé par le bridge M14→criterion_assessments.

## Statut

- **Hors périmètre P3.2** (Article 10, Condition 2 — ouverture documentée uniquement)
- **Renvoyé à P3.3** ou cleanup post-P3.2

## Décision

P3.2 **n'implémente pas** `get_latest_score_run`. Le moteur P3.2 opère exclusivement sur `criterion_assessments` (décision `decisions/p32_no_score_runs.md`).

## Action immédiate

Aucune — issue ouverte pour traçabilité conformément au mandat P3.2 Article 10.

## Référence

- Mandat : MANDAT_P3.2_SCORING_ENGINE_PILOTE_V2
- Article 10, Condition 2
- Article 14.2 (legacy documenté hors périmètre)

## Labels

`legacy`, `p3.2-out-of-scope`, `pipeline`
```

---

## ACTION CTO

**Ouvrir manuellement l'issue GitHub avec le contenu ci-dessus.**

Le CLI `gh` rencontre une erreur dans l'environnement actuel. L'agent documente l'issue ici pour que le CTO puisse l'ouvrir via l'interface web GitHub.

---

**Condition 2 documentée — action CTO requise pour ouverture GitHub.**
