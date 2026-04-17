# Audit Enterprise-Grade P1→P3.1B — Post-merge PR #424

**Émis** : 2026-04-17 (mandat CTO)  
**Base vérifiée** : `4a33337cc548165cf3c18f0e7b4628c01ed7b8d2` (merge PR #424)  
**Branche audit** : `fix/p3-audit-enterprise`  
**Périmètre** : aucune fonctionnalité P3.2 ; pas d’anticipation ScoringEngine.

---

## Étape 0 — Sync base

| Contrôle | Résultat |
|----------|----------|
| `HEAD` = `4a33337c…` | OK (fast-forward `origin/main`) |

---

## Étape 1 — Suite complète + lint

| Contrôle | Résultat |
|----------|----------|
| `pytest tests/unit/ -q` | **416 passed** (≥ 415 attendu) |
| `ruff check src tests services` | **0 erreur** |
| `black --check` (fichiers `.py` suivis sous `src/`, `tests/`, `services/`) | **0 reformat** |
| `ruff check .` / `black --check .` | Non utilisés comme gate : incluent des artefacts hors périmètre CI (ex. fichiers non suivis à la racine). Gate alignée **CI** : `src`, `tests`, `services`. |
| `mypy` (local) | **NON EXÉCUTÉ** — module `mypy` absent dans l’environnement Python de la session agent. À lancer en CI / venv projet : `mypy src/procurement/document_ontology.py src/procurement/eligibility_gate.py …` |

---

## Étape 2 — Audit P1 (classification documentaire)

**Constat normatif vs mandat** : le mandat cite un enum `DocumentKind` à 9 valeurs (`TECHNICAL_OFFER`, `FINANCIAL_OFFER`, …). Le dépôt utilise **`DocumentKindParent`** / **`DocumentKindSubtype`** / couches M12 dans `src/procurement/document_ontology.py` (liste fermée `StrEnum`, `@unique`). Ce n’est pas une incohérence de code : **autre vocabulaire contractuel** ; traçabilité annotation / recognizer.

**Fichiers P1 pertinents (échantillon)** : `document_ontology.py`, `annotation/document_classifier.py`, passes 1a/1b/1c, `pipeline_v5_service.py` (imports `DocumentKindParent`, …).

**Tests ciblés** : les filtres `-k "p1 or classification or document_kind"` ne matchent presque aucun nom de test ; jeux explicites exécutés :

- `tests/unit/test_phase1_gate_b_bundle_qualification.py` + `test_phase2_m12_document_typing.py` + `test_p3_eligibility_gate.py` → **35 passed** (couverture Gate B + typage documents + gate).

**Verdict P1** : **OK** — enums fermés et tests de phase présents ; alignement libellé mandat / ontology à traiter au **plan directeur** si unification des noms est requise.

---

## Étape 3 — Audit P2 (qualification bundles / Gate B)

**Code** : `bundle_scoring_role`, `NON_SCORABLE_GATE_B_STATUSES` dans `eligibility_gate.py` ; `pipeline_v5_service` enchaîne Gate B puis P3.1B.

**Tests** : `pytest tests/unit/ -k "p2 or bundle or scorable or gate_b"` → **33 passed**.

**Verdict P2** : **OK** — invariants Gate B / SCORABLE couverts par la suite existante ; aucune correction code requise à l’audit statique.

---

## Étape 4 — Audit P3.1 / P3.1B (EligibilityGate)

**Fichiers** : `eligibility_gate.py`, `eligibility_models.py`, `eligibility_gate_extractor.py`, `pipeline_v5_service.py` (`run_p3_1b_eligibility_gate_phase`, merge exclusions, `EXCLUSION_REASONS`).

**Tests** : `tests/unit/test_p3_1b_pipeline_integration.py` → **20 passed** (mandat mentionnait 19 ; +1 test sur la branche actuelle).

**Verdict P3** : **OK** — R1–R7 portés par la suite d’intégration ; pas de changement requis.

---

## Étape 5 — Intégration `run_pipeline_v5` (`pipeline_v5_service`)

Ordre logique vérifié en lecture : construction offres / Gate B → phase P3.1B (`run_p3_1b_eligibility_gate_phase`) → pont M14 / matrices (fichier volumineux ; détail dans tests `test_p3_1b_pipeline_integration.py`).

**Verdict INT** : **OK** — régression non détectée ; tests unitaires verts.

---

## Étape 6 — Smoke pilote (DB réelle / CLI)

**Statut** : **NON EXÉCUTÉ**

**Raison** : pas d’accès Railway / `dms.pipeline.run_pipeline_v5` avec `--workspace` / `--dossier` depuis cet environnement (pas de `DATABASE_URL` prod, pas de dossier pilote monté, CLI non invoquée). À exécuter post-merge par l’équipe avec secrets et corpus pilote.

---

## Synthèse statuts

```
[P1]  STATUS: ✅ OK (vocabulaire enum ≠ libellé mandat ; code cohérent)
[P2]  STATUS: ✅ OK
[P3]  STATUS: ✅ OK
[INT] STATUS: ✅ OK
[SMK] STATUS: NON-EXÉCUTÉ (infra / accès DB réelle)
```

```
=== VERDICT ENTERPRISE-GRADE ===
Chaîne P1→P3.1B : VALID (sur preuves : tests unitaires + revue statique)
Smoke test pilote : NON-EXÉCUTÉ
Commits de correction : 0 (audit sans régression détectée)
Suite tests post-audit : 416 passed / 0 failed (tests/unit/)
Blocants P3.2 : AUCUN identifié dans le périmètre audité
```

---

## Recommandations hors mandat (noter, ne pas coder P3.2)

- Unifier la **nomenclature** « DocumentKind 9 valeurs » mandat vs `DocumentKindParent` M12 dans la doc de référence si une seule taxonomie doit s’imposer.
- Exécuter **mypy** dans l’environnement CI officiel sur les modules P1/P3/pipeline.
- Lancer le **smoke** `--dry-run` sur `sci_mali` + dossier pilote 2 vendors dès qu’un runbook + secrets sont disponibles.
