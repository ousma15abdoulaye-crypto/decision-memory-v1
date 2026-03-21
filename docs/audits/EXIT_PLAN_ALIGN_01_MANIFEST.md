# EXIT-PLAN-ALIGN-01 — Manifeste de livraison (paquet architectural)

**Référence :** EXIT-PLAN-ALIGN-01  
**Date livraison :** 2026-03-21  
**Statut :** LIVRÉ — matérialisation **système** (pas le rail annotation)

---

## 1. Objet

Ce paquet matérialise dans le dépôt la séquence **SYSMAP → SEC-MT → RUNTIME-DOC** avec des artefacts **opposables** (chemins de fichiers, commandes, constats vérifiables).

**Hors paquet (sous-système externe, compatibilité seulement) :** Label Studio, `services/annotation-backend/`, exports M12-v2, `validate_annotation.py`, `annotation_qa.py`, structured_preview bridge, STRICT_PREDICT, docs/adr M12, adoption downstream des exports annotation.

---

## 2. Documents canoniques (triptyque)

| Document | Rôle |
|----------|------|
| [`SYSMAP_DMS_EXIT_PLAN_01.md`](SYSMAP_DMS_EXIT_PLAN_01.md) | Cartographie : dualité `main:app` / `src.api.main:app`, sens de « pipeline », montage routers, points sensibles |
| [`SEC_MT_THREAT_MODEL_MINIMAL_EXIT_01.md`](SEC_MT_THREAT_MODEL_MINIMAL_EXIT_01.md) | Surfaces d'attaque, scénarios d'abus, barrières existantes, mandat suivant (inventaire IDOR) |
| [`RUNTIME_DOC_ALIGNMENT_MATRIX_EXIT_01.md`](RUNTIME_DOC_ALIGNMENT_MATRIX_EXIT_01.md) | Matrice **fermée** doc vs runtime ; décisions A/B/C par ligne |

---

## 3. Intégration dans la doc pivot

- [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) : section **Vérité d'exécution** + paragraphe A/B **corrigé** (chemins `src/couche_a/`, tests réels, renvoi à la matrice).

---

## 4. Ordre de lecture CTO (5 minutes)

1. SYSMAP §0 (deux apps FastAPI)  
2. RUNTIME-DOC matrice (lignes 7–10)  
3. SEC-MT §1 + §7 (prochain mandat)

---

## 5. Critères « réaligné » (observables)

- Tout mandat technique **cite** SYSMAP (ligne ou app).  
- Aucun mandat ne **mélange** annotation avec SEC ou cartographie.  
- Chaque **ÉCART** de la matrice a un **statut** CTO (doc / code / ADR / risque accepté) avant nouvelle couche ARCH.

---

## 6. Prochaine action produit (hors ce paquet)

Mandat **SEC-MT-01** : inventaires `audit_fastapi_auth_coverage.py` sur `main:app` **et** `src.api.main:app`, tableau fermé routes sensibles × auth/case_access.
