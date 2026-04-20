# CONDITION 2 — CLOSED

**Date clôture** : 2026-04-17  
**Référence** : MANDAT_P3.2 Article 10, Condition 2  
**Statut** : ✅ CLOSED

---

## ISSUE GITHUB OUVERTE

**URL** : https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/issues/426#issue-4284409927

**Numéro** : #426

**Titre** : `[LEGACY] get_latest_score_run AttributeError dans pipeline service`

**Labels** : `legacy`, `p3.2-out-of-scope`

---

## CONTENU ISSUE

Conformément au document préparatoire `decisions/p32_condition2_issue_documented.md`, l'issue documente :

1. **Symptôme** : `AttributeError: module 'src.couche_a.pipeline.service' has no attribute 'get_latest_score_run'`
2. **Localisation** : `src/couche_a/pipeline/service.py`
3. **Analyse** : Fonction legacy du système scoring V1 (`ScoringEngine` + table `score_runs`)
4. **Statut** : Hors périmètre P3.2 (Article 10, Condition 2)
5. **Décision** : Renvoyé à P3.3 ou cleanup post-P3.2

---

## CLÔTURE

La Condition 2 du mandat P3.2 est **officiellement clôturée**.

L'issue GitHub #426 assure la traçabilité du bug legacy hors périmètre P3.2.

---

**Archivé. Opposable.**
