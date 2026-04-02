# ANNOTATION_BACKEND_MIGRATION_STRATEGY — Strangler fig (4 phases)

**Cible** : [`services/annotation-backend/backend.py`](../../../services/annotation-backend/backend.py)  
**Date** : 2026-03-24

---

## Principe

Remplacer le monolithe **sans** big bang : le endpoint Label Studio `/predict` reste le contrat externe jusqu’à la phase finale.

---

## Phase 1 — Runtime M12 (statu quo garanti)

- `backend.py` reste l’unique exécuteur ML pour Label Studio.
- Gate M12 : [DMS_M12_CORPUS_GATE_EXECUTION.md](../../m12/DMS_M12_CORPUS_GATE_EXECUTION.md).
- Aucune dépendance obligatoire vers `src/annotation/passes/*`.

**Critère de sortie** : 15 × `annotated_validated` prouvés.

---

## Phase 2 — Bibliothèques de passes (hors LS)

- Implémenter Pass 0 / 0.5 / 1 comme **fonctions pures** (entrée dict / str, sortie `AnnotationPassOutput`).
- Tests unitaires + intégration **sans** montage FastAPI.
- `backend.py` **inchangé** fonctionnellement (ou micro-fixes bugfix seulement).

**Critère de sortie** : couverture tests passes ; CI verte ; aucune régression golden `validate_annotation.py`.

---

## Phase 3 — Orchestrateur interne + adapter dans `backend.py`

- Introduire un orchestrateur (module dédié) qui enchaîne Pass 0 → 0.5 → 1 puis délègue au flux Mistral existant.
- `backend.py` appelle l’orchestrateur **derrière** `/predict` (feature flag env `ANNOTATION_USE_PASS_ORCHESTRATOR=1`).
- Dual-run optionnel : comparer ancien vs nouveau sur échantillon (logs uniquement, pas de double écriture LS).

**Critère de sortie** : flag activé en staging ; métriques latence / erreurs documentées.

**Statut Phase 3** : **GO** — implémentation sous [`ADR-M12-PHASE3-BACKEND-WIRING.md`](../../adr/ADR-M12-PHASE3-BACKEND-WIRING.md) ; gel Cursor révisé (`.cursor/rules/dms-annotation-backend-freeze.mdc`) pour mandat CTO explicite.

### Phase 3 — Plan de câblage opérationnel

Quand les passes et l'orchestrateur sont prouvés (CI verte, métriques calibrées, macro-F1 >= 0.70) :

1. **`backend.py` — insertion point** : dans la route `/predict`, après extraction du texte brut et avant l'appel Mistral, insérer un appel conditionnel :
   ```python
   if use_pass_orchestrator():
       record, state = orchestrator.run_passes_0_to_1(raw_text, ...)
       # Utiliser record.pass_outputs pour enrichir le contexte Mistral
   ```
2. **Feature flag** : `ANNOTATION_USE_PASS_ORCHESTRATOR` (défaut `0`, Railway env variable).
3. **Dual-run** : en mode flag=1, logger la sortie orchestrateur ET la sortie monolithe, comparer en post-run (pas de double écriture LS). Variable optionnelle `ANNOTATION_ORCHESTRATOR_DUAL_LOG`.
4. **Rollback** : flag à `0` = retour instantané au monolithe.
5. **Prérequis** : mandat CTO + ADR Phase 3 (le gel générique annotation est levé pour ce chantier nommé).

---

## Phase 4 — Thin adapter LS

- `backend.py` se limite à : parse LS payload → orchestrateur complet (y compris post-LLM validation existante) → format réponse LS E-66.
- Logique métier volumineuse extraite vers `src/annotation/` (passes + orchestrateur + helpers).

**Critère de sortie** : `backend.py` < 300 lignes ou équivalent modularisé ; une seule voie canonique sous flag par défaut `1`.

---

## Anti-patterns interdits

- Réécriture complète de `/predict` sans Phase 2 testée.
- Deux formats JSON d’annotation divergents en production.
- Suppression des garde-fous sécurité (`PSEUDONYM_SALT`, spot-check, validation Pydantic) sans ADR.
