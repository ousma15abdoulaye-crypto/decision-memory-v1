# DATA-M15 — Politique de données et d’export vers le jalon M15

**Statut :** mandat initial (à faire valider produit / CTO).  
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
| **Owner DATA-M15** | À désigner (CTO / data lead) — arbitrage final « export oui/non » |
| **Engineering** | Implémenter les **gates** techniques (filtres, checks, refus explicite) |
| **Terrain / annotation** | Ne promouvoir que des jeux **annotated_validated** conformes |

## 6. Prochaines étapes (quand DATA-M15 devient exécutable)

1. Référencer ce mandat depuis le **rapport M15** cible (`docs/reports/M15_validation_report.md` ou équivalent).
2. Lier chaque job d’export (script, ETL, API) à une **section** de ce doc (traceabilité).
3. Ajouter des **tests d’intégration** ou contrats qui refusent l’export si préconditions non remplies.

## 7. Références freeze / gouvernance

- `docs/freeze/DMS_V4.1.0_FREEZE.md` — M15, RÈGLE-10, RÈGLE-23, métriques.
- `docs/freeze/ANNOTATION_FRAMEWORK_DMS_v3.0.1.md` — états d’annotation, `evaluation_report`, M15.
- `docs/freeze/CONTEXT_ANCHOR.md` — synthèse gates M15.
