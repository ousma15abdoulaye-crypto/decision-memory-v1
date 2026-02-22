# ADR-0010 — Correctifs Prioritaires Post-Audit Qualitatif V3.3.2

**Identifiant** : ADR-0010  
**Statut** : PROPOSED — Validation CTO requise  
**Date** : 2026-02-22  
**Auteur** : Audit Système (Abdoulaye Ousmane — CTO décideur final)  
**Constitution** : V3.3.2 (canonique, frozen)  
**Précédents** : ADR-0001 · ADR-0002 · ADR-0005 · ADR-0006 · ADR-0008 · ADR-0009  
**Références** : `AUDIT_QUALITATIVE_V3.3.2_2026-02-22.md`  
**Objet** : Fixer 6 correctifs prioritaires identifiés à l'audit — convertis en décisions opposables

---

## 0. Préambule

L'audit qualitatif du 2026-02-22 (`AUDIT_QUALITATIVE_V3.3.2_2026-02-22.md`) a identifié :

- 6 violations actives de la Constitution dans le code mergé (V-01 à V-06)
- 6 pistes de solutions (ADR-Candidat-01 à 06)
- 1 risque stratégique critique : Couche B vide → moat différé

Le présent ADR convertit ces pistes en décisions formelles proposées.  
**Aucune n'est active tant que non validée CTO.**

---

## 1. DÉCISION D1 — Scoring Engine : append-only strict + éliminations réelles

**Problème (V-01 + V-02)** :  
- `_save_scores_to_db()` utilise `ON CONFLICT DO UPDATE SET` — UPSERT interdit (ADR-0006).  
- `_meets_criterion()` retourne `True` systématiquement — toutes éliminations désactivées (INV-9).

**Décision** :

1. Créer table `score_runs` (INSERT-only, trigger BEFORE UPDATE/DELETE) conforme ADR-0006 et ADR-0005 D2.
2. Créer vue `current_supplier_scores` (dernière entrée par `case_id + supplier_name + category`).
3. Remplacer UPSERT dans `_save_scores_to_db()` par INSERT dans `score_runs`.
4. Implémenter `_meets_criterion()` avec logique réelle :
   - Critère `type = 'essential'` + `seuil_elimination IS NOT NULL` → vérification effective.
   - Élimination persistée dans `supplier_eliminations` (append-only existant).
5. Ajouter test bloquant CI : `tests/scoring/test_scoring_append_only.py`.

**Migration** : `026_m_scoring_engine_append_only.py`  
**Scope milestone** : prérequis obligatoire avant `M-PRICE-CHECKING` DONE.  
**Règle opposable** : Aucun INSERT UPSERT dans les tables de traçabilité scoring.

---

## 2. DÉCISION D2 — Neutralité universelle : devise + poids tracés

**Problème (V-03 + V-04)** :  
- Poids fallback hardcodés sans traçabilité dans `_calculate_total_scores()`.  
- Devise `"XOF"` hardcodée — violation Constitution §1.2 (universalité).

**Décision** :

1. Ajouter colonne `currency` (TEXT NOT NULL DEFAULT 'XOF') à la table `cases` si absente — migration additive idempotente.
2. Le moteur de scoring lit `cases.currency` — jamais de constante hardcodée.
3. Tout fallback de poids doit injecter dans `calculation_details` :
   ```json
   {"fallback": true, "reason": "profile not found in scoring_configs — using hardcoded defaults"}
   ```
4. Test CI : `test_score_currency_from_case_not_hardcoded`.

**Migration** : `027_add_cases_currency.py` (additive, idempotente).

---

## 3. DÉCISION D3 — Canonisation `src/evaluation/profiles.py`

**Problème (V-05)** :  
`src/evaluation/` est un module flottant hors Couche A et hors Couche B — non documenté comme neutre.

**Décision** :

1. Déclarer `src/evaluation/` comme **module neutre de configuration partagée** — documenté dans `docs/ARCHITECTURE.md` et `docs/adrs/ADR-0002.md` (amendement).
2. Règle opposable : `src/couche_a/price_check/engine.py` **interdit d'importer** `src.evaluation.profiles` directement. Source unique de vérité pour les seuils prix = `scoring_configs` DB (ADR-0009 D2).
3. `evaluation/profiles.py` est autorisé uniquement comme seed-source pour la migration Alembic.
4. Test CI à créer : `test_price_check_engine_no_evaluation_profiles_import` (scan AST).

---

## 4. DÉCISION D4 — Tests boundary ADR-0009 : bloquants avant DONE

**Problème** :  
`tests/boundary/` n'existe pas. ADR-0009 D5 l'exige comme condition DONE de M-PRICE-CHECKING.

**Décision** :

1. Créer `tests/boundary/__init__.py`.
2. Créer `tests/boundary/test_couche_a_b_boundary.py` :
   - Scan AST de tous les fichiers `src/couche_a/**/*.py`.
   - Échec si un import vers `src.couche_b.*` ou `src.evaluation.*` est détecté dans un module décisionnel Couche A.
   - Exception documentée : `src/couche_a/price_check/engine.py` peut lire `scoring_configs` via SQL paramétré uniquement.
3. Créer `tests/boundary/test_constitution_compliance.py` :
   - Vérifie que `PriceCheckResult` (schéma Pydantic) ne contient aucun champ : `rank`, `winner`, `recommendation`, `selected`, `best_offer`, `shortlist`.
   - Vérifie que les réponses des endpoints `/price-check/*` ne contiennent pas ces clés.
4. Ces deux tests sont **bloquants CI** — gate obligatoire dans `.github/workflows/`.

---

## 5. DÉCISION D5 — Auto-feed Couche B : capture `decision_history` dès Phase 3

**Problème stratégique** :  
Chaque dossier clôturé sans capture `decision_history` = donnée marché perdue définitivement. Le moat ne se construit pas tant que ce mécanisme est absent.

**Décision** :

1. Créer table `decision_history` (Couche B) conforme Constitution §6.3 — append-only, trigger.
2. Créer hook `post_case_close(case_id: str)` appelé automatiquement lors de l'insertion d'un `case_event` de type `closed`.
3. Le hook alimente `decision_history` avec :
   - `case_id`, `item_id`, `supplier_id`, `price_paid`, `quantity`, `decision_date`, `zone`.
   - Source : données de `supplier_scores` + `normalized_line_items`.
4. Contrainte absolue : le hook ne bloque JAMAIS la clôture du dossier.
   - Pattern : try/except complet, erreur loggée dans `audit_log`, jamais propagée vers Couche A.
5. Avancer M-MARKET-DATA-TABLES à Phase 2 (parallèle M-COMMITTEE-CORE) — nécessite validation CTO explicite du plan milestones.

**Migration** : incluse dans M-MARKET-DATA-TABLES avancé.  
**Impact stratégique** : premier pas vers le moat — chaque dossier clôturé devient une ligne de mémoire marché.

---

## 6. DÉCISION D6 — Priorité séquençage Couche B

**Problème** :  
Couche B est en Phase 5 du plan milestones — après 15+ milestones Couche A. Sans accumulation précoce de données, le Market Signal sera vide à son lancement et sans valeur pour les premiers clients.

**Décision** :

| Ajustement | Phase actuelle | Phase proposée |
|------------|---------------|----------------|
| M-MARKET-DATA-TABLES (tables mercuriale/history/surveys) | 5 | 2 (parallèle M-COMMITTEE-CORE) |
| Auto-feed `decision_history` (D5 ci-dessus) | 5 | 3 (après M-PIPELINE-A partiel) |
| M-MARKET-SURVEY-WORKFLOW | 5 | 4 |
| M-MARKET-SIGNAL-ENGINE complet | 5 | 5 (inchangé) |

**Règle** : Cet ajustement de séquençage ne peut être activé que par ADR CTO explicite modifiant `docs/MILESTONES_EXECUTION_PLAN_V3.3.2.md`. Le présent ADR-0010 D6 est une **proposition soumise à validation CTO**.

---

## 7. Alternatives rejetées

| Alternative | Raison du rejet |
|-------------|----------------|
| Laisser UPSERT dans scoring engine | Viole ADR-0006 — risque crash prod au 2ème recalcul sur trigger append-only |
| Conserver `_meets_criterion = True` | Masque une fonctionnalité critique — scoring sans éliminations = non conforme |
| Garder XOF hardcodé | Bloque universalité §1.2 — élimine les clients hors zone UEMOA |
| Différer auto-feed Couche B à Phase 5 | Perd les données de chaque dossier traité entre Phase 1 et Phase 5 — dette irréversible |
| Rendre les boundary tests non-bloquants | Contourne ADR-0009 D5 — dette non datée = non contrainte |

---

## 8. Conséquences

**Si ce plan est accepté :**
- M-PRICE-CHECKING démarre sur une base constitutionnellement saine (D1 → score_runs).
- La première donnée de mémoire marché est capturée dès le premier dossier clôturé en Phase 3 (D5).
- Les violations constitutionnelles V-01 à V-06 sont toutes adressées.
- Le projet peut honnêtement prétendre au statut de game changer à la fin des milestones V3.3.2.

**Si ce plan est partiellement accepté (minimum vital) :**
- D1 (append-only scoring) + D4 (boundary tests) sont **non-négociables** avant M-PRICE-CHECKING DONE.
- D5 (auto-feed) est hautement recommandé pour protéger le moat.

---

## 9. Références

| Référence | Objet |
|-----------|-------|
| ADR-0005 D2 | score_runs (events) + vue current_supplier_scores — décidé, non implémenté |
| ADR-0006 §1 | Zéro UPDATE métier — trigger obligatoire |
| ADR-0008 Étape 7 | Suite complète avant DONE — inclut ruff/black/0 failed |
| ADR-0009 D2/D3/D5 | scoring_configs source unique / read-only #7 / boundary tests |
| Constitution §1.2 | Universalité — aucune limitation géographique hardcodée |
| Constitution §3.2 | Les 3 sources Market Signal — auto-feed obligatoire |
| `AUDIT_QUALITATIVE_V3.3.2_2026-02-22.md` | Audit source de ce document |

---

*Ce document est PROPOSED. Il n'est pas opposable tant que non validé CTO.*  
*Une fois validé, il sera promu ACCEPTED et inclus dans le registre freeze.*
