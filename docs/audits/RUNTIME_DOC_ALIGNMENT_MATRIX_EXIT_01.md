# RUNTIME-DOC — Matrice d’alignement (EXIT-PLAN-ALIGN-01)

**Référence :** EXIT-PLAN-ALIGN-01 · Mandat RUNTIME-DOC-ALIGN  
**Date :** 2026-03-21  
**Révision :** 2026-03-21 — lignes dual-app + committee + README  
**Statut :** inventaire **fermé** pour ce passage — chaque ligne a une preuve ; hors `docs/freeze/` et hors V4 (non modifiés par ce livrable).

**Exclu du détail :** rail annotation (LS, M12, `annotation-backend`, validate/QA) — **compatibilité** seulement (sous-système distinct).

---

## Légende

| Statut | Signification |
|--------|----------------|
| **ALIGNÉ** | Doc et runtime cohérents sur l’essentiel |
| **ÉCART** | Divergence nommée ; action = doc, code, ou ADR |
| **PARTIEL** | Vrai avec nuances / exceptions |
| **UNKNOWN** | Non vérifié dans ce passage |

---

## Matrice

| # | Affirmation doc (source) | Runtime observé | Statut | Preuve / note |
|---|--------------------------|-----------------|--------|----------------|
| 1 | `docs/ARCHITECTURE.md` : Couche A/B sans import Python direct | `price_check` charge `normalize_batch` via `importlib` + SQL sur `couche_b.mercuriale_raw_queue` | **ÉCART** | [`src/couche_a/price_check/engine.py`](../../src/couche_a/price_check/engine.py) |
| 2 | `docs/CONTRACT_A_B.md` : couplage A↔B **HTTP uniquement** | Monolithe + **PostgreSQL partagé** ; lecture/écriture cross-schema en code | **ÉCART** | `main.py` / accès DB ; même fichier price_check |
| 3 | Gate : pas d’import Couche B dans Couche A (invariant étendu) | Test `test_no_couche_b_import_in_couche_a` **skippé** | **ÉCART** | [`tests/invariants/test_no_couche_b_import_in_couche_a.py`](../../tests/invariants/test_no_couche_b_import_in_couche_a.py) |
| 4 | Routers montés = capacités disponibles | `src/api/main.py` : routers **optionnels** absents si ImportError → démarrage OK | **PARTIEL** | [`src/api/main.py`](../../src/api/main.py) |
| 5 | Middlewares M1 (rate limit, headers) actifs | App modulaire : try/except — peuvent être absents | **PARTIEL** | `src/api/main.py` |
| 6 | « Pipeline » unique | Plusieurs orchestrations (SYSMAP §1) | **ÉCART** | [`SYSMAP_DMS_EXIT_PLAN_01.md`](SYSMAP_DMS_EXIT_PLAN_01.md) |
| 7 | Une seule application FastAPI / point d’entrée clair | **Deux** apps : `main:app` et `src.api.main:app` ; prod Railway = `main:app` | **ÉCART** | [`main.py`](../../main.py), [`src/api/main.py`](../../src/api/main.py), [`start.sh`](../../start.sh) |
| 8 | `docs/ARCHITECTURE.md` : chemins `src/scoring/`, `src/pipeline/` … | Code effectif sous `src/couche_a/` (et autres) | **ÉCART** | Comparaison [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) §73–80 vs arborescence `src/` |
| 9 | Comité exposé HTTP | Router [`committee/router.py`](../../src/couche_a/committee/router.py) **non** inclus dans `main.py` ni `src/api/main.py` | **ÉCART** | Absence de `include_router` committee dans les deux `main` |
| 10 | README : commande de lancement API | Aligné sur `uvicorn main:app` (même vérité que Railway) | **ALIGNÉ** | [`README.md`](../../README.md) — révision 2026-03-21 + SYSMAP §7 |

---

## Décisions possibles par ligne (sans exécution obligatoire ici)

| Ligne | Option A | Option B | Option C |
|-------|-----------|-----------|-----------|
| 1–2 | Mettre à jour **doc** pour refléter DB + exceptions nommées | Refactor **code** vers contrat HTTP (chantier lourd) | **ADR** « contrat runtime effectif » |
| 3 | **Unskip** + allowlist explicite modules `couche_b` autorisés | Retirer test obsolète (avec ADR) | — |
| 4–5 | Fail-fast prod si router critique manquant | Documenter dégradé + feature flags | — |
| 6 | Terminologie SYSMAP dans docs pivots | — | — |
| 7 | **Déprécier** une des apps ou documenter déploiement dual contrôlé | Fusionner montages (chantier ARCH) | — |
| 8 | Corriger `ARCHITECTURE.md` (chemins) | — | — |
| 9 | Monter committee sur l’app prod **ou** doc « API interne / non exposée » | — | — |
| 10 | *(Aligné — voir README)* | — | — |

---

## Conditions de clôture RUNTIME-DOC

- Chaque ligne **ÉCART** a un **statut** : corrigé doc / corrigé code / ADR ouvert / risque accepté **nommé** (CTO).
- Pas de nouvelle page narrative sans **ancrage** fichier.
- Aucune ligne ne mélange le rail **annotation** avec les écarts ci-dessus (systèmes indépendants).
