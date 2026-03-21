# DATA-M15 — Politique de données et d’export vers le jalon M15

**Statut :** mandat **exécutable** (gates techniques minimales + squelette rapport) — validation produit / owner à finaliser.  
**Problème résolu :** un pipeline « propre » qui alimente M15 avec du **bruit** ou des artefacts **hors politique** reste un échec ; ce document fixe le **périmètre exportable** et les **préconditions** avant toute intégration outillée.

## 1. Définition opérationnelle de M15 (rappel)

M15 = preuve terrain **100 dossiers** avec **métriques opposables** (freeze V4.1.0 / enterprise target). Les seuils chiffrés (couverture, unresolved, `annotated_validated`, etc.) restent ceux du **gèle** courant — DATA-M15 ne les recopie pas : il les **référence** comme barrières d’export.

## 2. Principe directeur

> **Rien n’est « exporté vers M15 » par défaut.** Tout flux sortant (corpus, rapports, snapshots, métriques agrégées) doit être **nommé**, **versionné** et **filtré** selon les règles ci-dessous.

## 3. Classes de données — autorisé / interdit / conditionnel

| Classe | Vers M15 | Condition |
|--------|----------|-----------|
| Annotations au seul état **annotated_validated** | Oui | Comptage et seuils freeze (ex. ≥ 50 avant M15 selon périmètre) |
| Annotations draft / rejected / non validées | **Non** | Bruit pour métriques opposables |
| **`evaluation_report`** (famille E) | **Non** avant M15 | Verrouillage explicite freeze (MC-4) |
| Exports CBA/PV / snapshots **scellés** et traçables | Conditionnel | Uniquement si dossier / comité dans état autorisé par la Constitution |
| Données personnelles non pseudonymisées | **Non** | Respect politique pseudonymisation / ADR dédiés |
| Agrégats anonymisés (métriques M15 report) | Oui | Pas de ré-identification ; méthode documentée |

## 4. « Bruit » (non-exportable)

- Sorties modèle ou pipeline sans **validation humaine** lorsque la gouvernance exige `annotated_validated`.
- Champs marqués **AMBIGUOUS / ABSENT** au-delà des seuils M15 (voir ADR M11 / freeze).
- Toute donnée issue d’un **tenant** ou dossier **hors périmètre** du programme M15 (liste blanche de `case_id` / org à maintenir).

## 5. Rôles et ownership

| Rôle | Responsabilité |
|------|----------------|
| **Owner DATA-M15** | **TBD** — cible désignation **2026-06-30** (CTO / data lead) ; jusqu’alors arbitrage provisoire : pair eng. + produit. |
| **Engineering** | Implémenter les **gates** techniques (filtres, checks, refus explicite) |
| **Terrain / annotation** | Ne promouvoir que des jeux **annotated_validated** conformes |

## 6. Exécution — checklist et jobs d’export

### 6.1 Rapport et traçabilité

- [ ] **TICKET-DM15-01** — Remplir [`docs/reports/M15_validation_report.md`](../reports/M15_validation_report.md) au gel M15 (signatures, périmètre, résultats gates).
- [ ] **TICKET-DM15-02** — Lister la **liste blanche** `case_id` / orgs dans un artefact versionné (réf. interne, hors repo si sensible).

### 6.2 Jobs / scripts (inventaire)

| Artefact | Rôle vis-à-vis M15 | Section DATA-M15 |
|----------|-------------------|------------------|
| [`scripts/export_ls_to_dms_jsonl.py`](../../scripts/export_ls_to_dms_jsonl.py) | Export LS → JSONL m12-v2 ; QA `annotated_validated` (`--enforce-validated-qa` défaut) ; **gate M15** `--m15-gate` (exit≠0 si validated + `export_ok=false`) | §3, §4 |
| [`scripts/m15_export_gate.py`](../../scripts/m15_export_gate.py) | Logique réutilisable `collect_m15_gate_violations` | §3 |
| [`tests/test_export_ls_m12_v2.py`](../../tests/test_export_ls_m12_v2.py) | Contrats export M12 / schéma | §6.3 |
| [`tests/test_m15_export_gate.py`](../../tests/test_m15_export_gate.py) | Tests unitaires gate M15 | §6.3 |

*(Autres ETL / API sortantes : ajouter une ligne ici lorsqu’elles alimentent le corpus M15.)*

### 6.3 Gates techniques livrées (minimal)

1. **Export JSONL** : combinaison `--require-ls-attestations` + QA financière / evidence (déjà dans `ls_annotation_to_m12_v2_line`).
2. **`--m15-gate`** : refus d’écrire le fichier si une annotation **annotated_validated** a `export_ok=false` (voir script ci-dessus).
3. **Tests** : `pytest tests/test_m15_export_gate.py`.

## 7. Références freeze / gouvernance

- `docs/freeze/DMS_V4.1.0_FREEZE.md` — M15, RÈGLE-10, RÈGLE-23, métriques.
- `docs/freeze/ANNOTATION_FRAMEWORK_DMS_v3.0.1.md` — états d’annotation, `evaluation_report`, M15.
- `docs/freeze/CONTEXT_ANCHOR.md` — synthèse gates M15.
