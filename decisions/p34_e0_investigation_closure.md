# DMS — P3.4 Étape 0 : notes d’investigation (clôture E0.2, E0.5, E0.6, E0.7)

**Date** : 2026-04-19  
**HEAD de référence** : `417f1149`  
**Branche** : `feat/p3-4-matrixrow-builder-summary`  
**Statut** : investigation uniquement — **aucun code métier** ajouté par ce livrable  
**Référence preflight** : `decisions/p34_opening_preflight.md`

---

## E0.2 — Usages `PipelineV5Result` (grep) et impact extension

**Recherche** : `PipelineV5Result` dans le dépôt (hors preflight lui-même).

| Fichier | Usage |
|---------|--------|
| `src/services/pipeline_v5_service.py` | Définition classe **L212–L241** ; `run_pipeline_v5` → `PipelineV5Result` **L1067**, instanciation **L1069** |
| `src/api/routers/pipeline_v5.py` | `response_model=PipelineV5Result` ; type de retour route `run-pipeline` |
| `tests/unit/test_phase1_gate_b_bundle_qualification.py` | Import + construction `PipelineV5Result(...)` pour tests Gate B |
| `frontend-v51/components/workspace/workspace-ingestion-panel.tsx` | Interface TS **locale** `PipelineV5Result` — **dupliquée**, non générée depuis OpenAPI |
| `docs/ops/*.md` | Citations documentaires |

**Impact champs `matrix_rows` / `matrix_summary`** :

- **Backend** : Pydantic sérialise les nouveaux champs en JSON API ; consommateurs existants qui ignorent les champs inconnus restent compatibles en lecture JSON typique.
- **`extra="forbid"`** : les champs doivent être **déclarés explicitement** sur le modèle avec valeurs par défaut sûres (ex. `default_factory=list` / `None`) pour ne pas casser les instanciations existantes (`PipelineV5Result(workspace_id=...)`).
- **Frontend** : l’interface TS ne liste pas encore ces propriétés — pas bloquant TypeScript si l’API est typée loose ; **vérification manuelle** lors d’une évolution UI qui consommerait la réponse complète (hors périmètre P3.4 minimal si pas de changement front).
- **Tests** : ajuster les assertions **uniquement** si un test compare `model_dump()` entier ou exige un schéma figé ; grep ne montre qu’un usage test constructeur minimal.

**Conclusion E0.2** : surface d’impact **faible** ; vigilance sur **default_factory** pour listes et sur **OpenAPI / front** en itération ultérieure.

---

## E0.5 — Audit `??` (fichiers non suivis)

**Méthode** : `git status --porcelain` ; lignes `??` ; regroupement par premier segment de chemin.

**Volume** : **~87** chemins non suivis (ordre de grandeur stable sur ce clone).

**Répartition indicative** (non exhaustive) :

| Zone | Ordre de grandeur | Nature |
|------|-------------------|--------|
| `decisions/` | ~18 | docs mandats / sandbox — **ne pas mélanger à la PR P3.4** sans tri |
| `docs/ops/` | ~9 | rapports ops locaux |
| `tests/` | ~8 | fichiers de test / probes non suivis |
| `src/` | ~6 | modules expérimentaux locaux |
| `scripts/` | ~6 | scripts ad hoc |
| Racine | divers | `.md` rapports, `.py` probes, `.json` métriques, `.ps1`, etc. |
| `data/` | présent | imports / bundles — **hors PR** |
| `.cursor/`, `.claude/`, `.github/` | quelques-uns | config locale / workflows non suivis |

**Décision opposable (alignée preflight + Context Anchor §13)** :

1. **Aucun `git add .`** sur cette branche.
2. **PR P3.4** : uniquement chemins **nommés** au mandat (`matrix_models.py`, `matrix_builder_service.py`, patch `pipeline_v5_service.py`, tests dédiés, docs P3.4 si commitées explicitement).
3. **`.gitignore` / purge `??`** : **chantier séparé** ; une PR dédiée « hygiene / gitignore » si l’équipe le priorise — **pas** glissée dans la PR P3.4.
4. Les `??` ne bloquent pas le travail : l’index des fichiers **suivis** reste la vérité pour CI.

**Conclusion E0.5** : risque maîtrisé par **discipline `git add` explicite** ; pas d’action code requise pour P3.4.

---

## E0.6 — `run_id` / `pipeline_run_id` dans `run_pipeline_v5`

**Recherche** : `run_id`, `pipeline_run_id` dans `src/services/pipeline_v5_service.py`.

**Résultat** : **aucune occurrence** — le pipeline V5 actuel ne génère ni ne propage d’identifiant d’exécution stable.

**Décision binaire (Réserve CTO #A, tranchée)** :

- **Réutilisation** : *impossible* sans introduire un identifiant amont (hors scope immédiat E0).
- **Génération locale** : **OUI** — au moment où `build_matrix_rows` (ou l’appelant juste après le bridge) s’exécute, générer **`pipeline_run_id = uuid4()`** une seule fois par invocation de construction matrice, et l’injecter **identiquement** dans chaque `MatrixRow` et dans `MatrixSummary` produits par cette invocation.

**Règle opposable** : une exécution de construction matrice = **un** UUID réel ; pas de `None`, pas de sentinelle textuelle générique.

**Implémentation suggérée (E3)** : créer `run_uuid = uuid.uuid4()` dans `run_pipeline_v5` **après** succès du bridge, passer `pipeline_run_id=run_uuid` à `build_matrix_rows` / `build_matrix_summary` (signature à définir en E1).

**Conclusion E0.6** : **génération `uuid4()` au point d’intégration pipeline** (recommandé plutôt qu’à l’intérieur du seul builder, pour une seule source par run complet).

---

## E0.7 — Convention de chemin pour `matrix_models.py`

**Recherche** : emplacement des modèles liés **évaluation / offres / matrice M14** et P3.3 prix.

| Artefact | Fichier |
|----------|---------|
| `EvaluationReport`, `OfferEvaluation`, types M14 matrice | `src/procurement/m14_evaluation_models.py` |
| `QualifiedPrice` (P3.3) | `src/couche_a/scoring/qualified_price.py` |
| Moteur scoring v5 / bridge | `src/services/pipeline_v5_service.py`, `src/services/m14_bridge.py` |

**Constat** : la **ligne sémantique « rapport d’évaluation fournisseur / matrice »** est portée par **`src/procurement/`** (`m14_evaluation_models.py`). Les types **prix qualifié** P3.3 vivent dans **`couche_a/scoring/`** (couche normalisation/score), pas dans procurement.

**Décision pour P3.4** : placer **`src/procurement/matrix_models.py`** — **même paquet** que `m14_evaluation_models.py`, car `MatrixRow` / `MatrixSummary` sont des **vues canoniques** du même domaine « évaluation comparative » que le rapport M14, distinctes du moteur de normalisation prix.

**Alternative documentée** : si le nombre de types P3.4 explose (sous-modèles `OverrideRef`, etc.), introduire un sous-paquet `src/procurement/matrix/` — **YAGNI** pour la première livraison.

**Conclusion E0.7** : **`src/procurement/matrix_models.py`** (alignement hiérarchique avec `m14_evaluation_models.py`).

---

## Synthèse exécutive (revue CTO Senior ≤ 5 min)

| ID | Verdict |
|----|---------|
| E0.2 | Impact extension **contrôlé** ; defaults Pydantic à soigner |
| E0.5 | **`??`** volumineux ; mitigé par **add explicite** ; `.gitignore` **hors PR P3.4** |
| E0.6 | **Pas de `run_id` existant** → **`uuid4()` une fois par run** au point d’intégration pipeline |
| E0.7 | **`src/procurement/matrix_models.py`** |

**Feu vert E1.1** : du point de vue investigation agent, les quatre tâches E0 restantes sont **livrées** dans ce document — **soumis à revue légère CTO Senior** conforme mandat.
