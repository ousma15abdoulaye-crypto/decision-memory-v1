# P3.3 — Opening preflight (Commercial Normalizer)

**Référence mandat :** `MANDAT_P3.3_COMMERCIAL_NORMALIZER.md`  
**Date :** 2026-04-18  
**Branche ouverture :** `feat/p3-3-commercial-normalizer` (base `main` @ merge PR #427 / P3.2 schema)  
**Statut document :** porte d’entrée — **aucun code métier P3.3** dans ce fichier.

---

## BLOC P1 — Point d’entrée actuel du calcul commercial

| Élément | Fait dépôt |
|--------|------------|
| **Orchestration pipeline (Couche A)** | `src/couche_a/pipeline/service.py` — après agrégation extractions → `SupplierPackage` + `DAOCriterion`, instanciation `ScoringEngine()` puis `calculate_scores_for_case(...)`. |
| **API scoring cœur** | `src/couche_a/scoring/engine.py` — classe `ScoringEngine`, méthode `calculate_scores_for_case` (lit devise / pondérations DB, éliminations, puis agrège scores par catégorie). |
| **Point commercial effectif** | Même fichier — méthode privée `_calculate_commercial_scores(self, suppliers, profile, currency=...)`. |
| **Ordre d’appel utile** | `calculate_scores_for_case` → `_check_eliminatory_criteria` → `_build_evaluation_profile` → **`_calculate_commercial_scores`** → autres catégories → `_calculate_total_scores` → `_save_scores_to_db`. |

**Non-périmètre scoring « commercial » actuel (hors moteur lowest-price) :**

- `src/couche_a/services/analysis.py` — `_compute_scores` : `commercial_score` **placeholder** pénalité champs manquants (pré-analyse offre), **pas** un prix qualifié.
- `src/procurement/m14_engine.py` — `_analyze_price` : **analyse comparative** M14 (`PriceAnalysis`), alimentée par `offer` dict + contexte H3 ; **pas** le même chemin que `ScoringEngine` M3B.

---

## BLOC P2 — État réel des données prix disponibles

| Source | Champs / comportement observés | Preuve dépôt |
|--------|-------------------------------|---------------|
| **Package fournisseur (scoring M3B)** | `SupplierPackage.extracted_data` : `total_price` (souvent **chaîne** type `"12 345 678 XOF"`), `total_price_source`, `currency` (fusion docs, défaut fréquent `XOF` dans `merge_supplier_packages`). | `src/core/models.py` (`SupplierPackage`), `src/business/offer_processor.py` (`merge_supplier_packages`, `extract_offer_data_guided`). |
| **Extraction guidée** | Regex sur texte : libellés *prix total / montant total / total* + devise ; sinon **plus grand montant** + devise — **aucun** `tax_basis` / `price_level` au résultat. | `extract_offer_data_guided` — `src/business/offer_processor.py`. |
| **Lignes de prix structurées** | `LineItem` : `quantity`, `unit_price`, `line_total`, `line_total_check` (`OK` / `ANOMALY` / `NON_VERIFIABLE`), `evidence`, `confidence`. | `src/couche_a/extraction_models.py`. |
| **Persistance extraction** | Sérialisation `unit_price`, `line_total`, `line_total_check` vers stockage extraction (contrat pipeline). | `src/couche_a/extraction/persistence.py` (champs listés dans grep dépôt). |
| **M14** | `PriceAnalysis` : `total_price_declared`, `currency`, `price_basis` (`HT` / `TTC` / `unknown`), drapeaux mercuriale / devise. | `src/procurement/m14_evaluation_models.py`, remplissage `src/procurement/m14_engine.py::_analyze_price`. |
| **Contexte procédure H3** | `price_basis_detected`, indices mercuriale — construits côté handoff (`handoff_builder` / `procedure_models`). | `src/procurement/handoff_builder.py`, `src/procurement/procedure_models.py`. |
| **SQL M16 / comparatifs** | Lecture `price_line_bundle_values`, `price_line_comparisons` — **autre couche** (liste prix comparatif), non consommée aujourd’hui par `_calculate_commercial_scores`. | `src/services/m16_evaluation_service.py` (`list_price_lines`). |

**Constat :** le score commercial M3B utilise **surtout** `total_price` string + **premier float regex** ; les **lignes** structurées et la **base HT/TTC** M14 **ne sont pas** dans ce chemin.

---

## BLOC P3 — Ambiguïtés commerciales actuelles

1. **HT / TTC** : non distingués dans `_calculate_commercial_scores` ; `PriceAnalysis.price_basis` existe en M14 mais **n’est pas injecté** dans le scoring M3B.
2. **UNIT vs LINE_TOTAL vs OFFER_TOTAL** : `LineItem` porte unitaire + total ligne ; le scoring commercial agrège uniquement un scalaire dérivé de `total_price` global — **pas d’alignement** niveau prix.
3. **Quantité absente** : `LineItem.__post_init__` marque `NON_VERIFIABLE` mais la voie scoring **n’utilise pas** `line_items` pour le commercial M3B.
4. **Total incohérent** : `line_total_check == ANOMALY` **non bloquant** pour le chemin `_calculate_commercial_scores` (données ignorées).
5. **Prix nul** : heuristique `to_num` peut retourner `0.0` ; `min` / division **non protégés** explicitement pour zéro dans le snippet commercial (risque `ZeroDivisionError` ou score absurde si non filtré en amont).
6. **Prix négatif** : pas de garde-fou métier dédié sur le float extrait.
7. **Devise** : `cases.currency` côté scoring + défaut `XOF` côté merge extraction — **risque** devise doc ≠ devise dossier sans passerelle qualifiée au moment du prix.
8. **Bases multiples** : regex « plus grand montant » vs total étiqueté vs lignes sommées — **plusieurs candidats** possibles sans règle opposable unique.

---

## BLOC P4 — Point d’insertion exact P3.3

| Question | Proposition preflight |
|----------|------------------------|
| **Où entrer** | **Immédiatement avant** la conversion « string → float » dans `_calculate_commercial_scores`, idéalement via une fonction / module dédié appelé depuis ce seul point (et, phase ultérieure, tout autre consommateur **strictement** prix-offre agrégé). Alternative : normaliser en amont dans la construction de `extracted_data` — **plus invasif** ; à éviter en première itération sans arbitrage. |
| **Entrée** | Pour chaque `SupplierPackage` : `extracted_data` (`total_price`, `total_price_source`, `currency`), références documents dans `documents` / `offer_ids`, et **si disponible** dans le payload d’extraction attaché aux offres : liste `line_items` / champs financiers structurés + tout signal H3 / M14 déjà présent dans l’objet transmis au pipeline (sans élargir au comité). |
| **Sortie** | Soit **`QualifiedPrice`** (contrat BLOC P5) **par base utilisée pour le comparatif** (probablement une agrégation « offre » pour la méthode `price_lowest_100`, mais le normalizer doit **nommer** `price_level`), soit **`None`** + métadonnées d’échec / soit **exception** `PriceAmbiguousError` (BLOC P6). |
| **Ne pas toucher** | Pondérations DB, éliminations, scores capacité / durabilité / essentiels, **UI**, **PV**, **matrix summary**, **override comité**, rubric scoring P3.2 hors famille commercial, migrations. |

---

## BLOC P5 — Contrat `QualifiedPrice` (minimal canonique)

Aligné mandat §7.1, adapté aux **IDs encore parfois texte** dans le pipeline actuel :

| Champ | Type proposé | Note preflight |
|-------|--------------|----------------|
| `amount` | `float` | Montant **déjà** sur la base qualifiée (`tax_basis` + `price_level`). |
| `currency` | `str` | ISO / code métier ; **obligatoire** si règle « devise indispensable » active. |
| `tax_basis` | `Enum` littéraux `HT`, `TTC` | Interdit de scorer commercial si valeur absente (cf. I2). |
| `price_level` | `Enum` `UNIT`, `LINE_TOTAL`, `OFFER_TOTAL` | Interdit de scorer si absent (cf. I1). |
| `quantity` | `float \| None` | Renseigné si `price_level == UNIT` ou cohérence ligne requise. |
| `source_document_id` | `UUID \| str \| None` | Aujourd’hui les offres utilisent souvent **str** ; tolérer jusqu’à harmonisation UUID stricte. |
| `evidence_refs` | `list[UUID | str]` | Fragments / ids trace persistance extraction. |
| `confidence` | `float` | [0,1] ou échelle projet existante — **à caler** sur `ExtractionField` / M14 discretization. |
| `human_review_required` | `bool` | `True` si ambiguïté résiduelle ou I3 (amount ≤ 0). |
| `flags` | `list[str]` | Codes courts type `HT_TTC_UNRESOLVED`, `UNIT_TOTAL_MISMATCH`, `CURRENCY_FALLBACK`, etc. |

---

## BLOC P6 — Contrat d’erreur `PriceAmbiguousError`

| Aspect | Proposition |
|--------|-------------|
| **Nature** | Exception métier **dédiée** (module `src/procurement/` ou `src/couche_a/scoring/` — **à trancher** à l’implémentation pour dépendances circulaires). |
| **Levée** | Lorsque les déclencheurs §7.3 sont rencontrés **et** qu’aucune règle explicite ne permet de réduire l’ambiguïté sans inventer une vérité. |
| **Propagation** | Captée à la frontière `_calculate_commercial_scores` : **pas** de `ScoreResult` commercial « inventé » ; journalisation dans `calculation_details` ou équivalent + option `human_review_required` sur trace **sans** score chiffré (cf. I1–I3). |
| **Vs `None`** | `NULL > faux score` : absence de qualification → **pas** de note commerciale ; distinguer `PriceAmbiguousError` (**contradiction / données incompatibles**) de simple absence (`None`). |

---

## BLOC P7 — Invariants à tester (exemples + propriétés)

**Jeux d’exemples (Article 10.1)** — données d’entrée minimales synthétiques + oracle :

- HT clair, TTC clair, unitaire clair, total offre clair.
- Ambigu HT/TTC ; ambigu unit/total ; quantité manquante où requise ; prix zéro ; prix négatif ; devise absente si règle bloquante.

**Propriétés (Article 10.2)** — assertions automatisables sur la **sortie** du normalizer (pas sur le score pondéré global) :

- Aucun `QualifiedPrice` avec `amount <= 0` **sans** `human_review_required=True` et flag explicite (cf. I3 — ou interdiction totale de `QualifiedPrice` dans ce cas, **à trancher** : mandat I3 autorise flag + revue, pas score).
- Aucun `QualifiedPrice` sans `price_level` ni sans `tax_basis`.
- Aucune conversion silencieuse d’entrée « ambiguë » vers sortie « valide complète ».
- Si entrée prix source `NULL` / chaîne vide → pas de `QualifiedPrice` factice ; pas de zéro cosmétique (I5).

---

## BLOC P8 — Verdict

**`GO` (2026-04-18)** — validation CTO explicite (« Go preflight ») ; ouverture implémentation P3.3 autorisée sur `feat/p3-3-commercial-normalizer`.

**Rappel :** branch technique et point d’insertion **identifiés** ; contrats P5/P6 **figés en implémentation** ; risques P3 **cartographiés** dans les blocs ci-dessus.

---

*Fin du preflight d’ouverture P3.3.*
