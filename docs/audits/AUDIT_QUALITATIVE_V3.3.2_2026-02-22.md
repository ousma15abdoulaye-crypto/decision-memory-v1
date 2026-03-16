# AUDIT QUALITATIF — Decision Memory System V3.3.2
**Date** : 22 février 2026  
**Rôle** : Auditeur Système · Tech Lead · Procurement Strategist  
**Périmètre** : V3.3.2 freeze — ADR-0001 à ADR-0009 — Couche A & B — M-SCORING → M-PRICE-CHECKING (ADR-0009)  
**Méthode** : Lecture exhaustive code source, tests, migrations, ADRs, Constitution — zéro modification de fichier  
**Ton** : Brutal, honnête, opposable

---

## RÉSUMÉ EXÉCUTIF — VERDICT BRUT

Le DMS est un **projet architecturalement sain** avec une discipline de gouvernance rare à ce stade
(Constitution gelée, ADRs versionés, protocole militaire, invariants CI). La vision est claire, le
cadre est béton. **Mais** l'honnêteté oblige à ce constat :

> **La promesse de game changer repose sur la Couche B (Market Signal). La Couche B est quasi absente
> du code. Tant qu'elle ne sera pas construite, le DMS est un générateur de CBA/PV performant —
> meilleur qu'Excel, mais pas un changement de paradigme.**

La Couche A est à **~55 % des milestones de production**. La Couche B est à **~5 %**.  
ADR-0009 (M-PRICE-CHECKING) est **bien rédigé mais non implémenté**.  
Trois violations actives de la Constitution ont été identifiées dans le code livré.

---

## TABLE DES MATIÈRES

1. [Ce que le projet fait exceptionnellement bien](#1-ce-que-le-projet-fait-exceptionnellement-bien)
2. [Audit ADR-0009 — M-Price-Checking](#2-audit-adr-0009--m-price-checking)
3. [Audit Couche A — L'ouvrier cognitif](#3-audit-couche-a--louvrier-cognitif)
4. [Audit Couche B — Le Moat](#4-audit-couche-b--le-moat)
5. [Cohérence Vision ↔ Développement](#5-cohérence-vision--développement)
6. [Le projet sera-t-il unique sur son créneau ?](#6-le-projet-sera-t-il-unique-sur-son-créneau-)
7. [Violations actives de la Constitution](#7-violations-actives-de-la-constitution)
8. [Pistes de solutions → ADR candidats](#8-pistes-de-solutions--adr-candidats)
9. [Matrice de priorité](#9-matrice-de-priorité)
10. [Conclusion](#10-conclusion)

---

## 1. CE QUE LE PROJET FAIT EXCEPTIONNELLEMENT BIEN

| Aspect | Constat factuel | Score |
|--------|----------------|-------|
| **Gouvernance documentaire** | Constitution V3.3.2 gelée, 9 invariants opposables, 9 ADRs versionés | ★★★★★ |
| **Protocole d'exécution** | ADR-0008 Militaire V1.2 — 8 étapes, aucun saut, signaux d'arrêt universels | ★★★★★ |
| **Append-only opérationnalisé** | ADR-0006 : triggers DB, vues `current_*`/`effective_*`, zéro UPDATE métier | ★★★★★ |
| **Frontière Couche A/B** | Interdiction d'import Couche B dans Couche A — vérifiée en CI | ★★★★☆ |
| **Stack technique** | FastAPI + PostgreSQL strict + Alembic SQL brut — aucun ORM, aucune base secondaire | ★★★★★ |
| **Tests constitutionnels** | `tests/invariants/` avec 9 fichiers de conformité — concept unique et puissant | ★★★★★ |
| **Milestones complétés** | M-SCHEMA-CORE, M-DOCS-CORE, M-EXTRACTION-ENGINE, M-EXTRACTION-CORRECTIONS, M-CRITERIA-TYPING, M-NORMALISATION-ITEMS, M-CRITERIA-FK — 7 milestones DONE avec `.done` files | ★★★★☆ |
| **ADR-0009 rédaction** | Requalification M-SCORING → M-PRICE-CHECKING constitutionnellement irréprochable. Blocants D1/D2/D3 identifiés avec précision | ★★★★★ |
| **Résistance à la dérive** | `no_scoring_no_ranking_no_recommendations=true` dans `src/core/config.py` — la règle est codée | ★★★★★ |

---

## 2. AUDIT ADR-0009 — M-PRICE-CHECKING

### 2.1 Qualité de l'ADR — Verdict : EXCELLENT

ADR-0009 est **le meilleur ADR du corpus**. Il démontre une maturité architecturale réelle :

- **D1/D2/D3** identifiés avant tout code — conforme au protocole militaire Étape 0.
- Requalification M-SCORING → M-PRICE-CHECKING : décision courageuse et constitutionnellement nécessaire. La pression était forte de garder "scoring" mais la Constitution ne laissait pas le choix.
- Nomenclature verdict `WITHIN_REF / ABOVE_REF / NO_REF` : lisible, non décisionnelle, opposable.
- **DECISION 3 (Read-only strict #7)** : la décision est posée. Mais voir §3.3 — le scoring engine existant est en contradiction.
- Tests boundary obligatoires (L6a/L6b) intégrés dans le scope du milestone — bonne pratique.

### 2.2 État d'implémentation — Verdict : ZÉRO

| Livrable ADR-0009 | Existence dans le code | Statut |
|-------------------|----------------------|--------|
| `src/couche_a/price_check/schemas.py` | ❌ ABSENT | Non démarré |
| `src/couche_a/price_check/engine.py` | ❌ ABSENT | Non démarré |
| `src/api/routers/price_check.py` | ❌ ABSENT | Non démarré |
| `alembic/versions/025_alter_scoring_configs.py` | ❌ ABSENT | Non démarré |
| `tests/price_check/test_price_check_engine.py` | ❌ ABSENT | Non démarré |
| `tests/boundary/test_couche_a_b_boundary.py` | ❌ ABSENT | Non démarré |
| `tests/boundary/test_constitution_compliance.py` | ❌ ABSENT | Non démarré |

**Diagnostic** : ADR-0009 est ACCEPTED. Le milestone #7 (M-PRICE-CHECKING) n'a pas démarré.
C'est normal si la séquence est respectée — mais voir §2.3.

### 2.3 Tension D1 — `scoring_configs` vs ADR-0009

ADR-0009 Decision 2 exige les colonnes `price_ratio_acceptable` et `price_ratio_eleve` dans `scoring_configs`.

La migration 007 crée bien `scoring_configs` avec `profile_code` — mais avec `commercial_weight`, `capacity_weight`, etc. — **pas** de `price_ratio_acceptable` / `price_ratio_eleve`.

Le D1 est donc **confirmé** : la migration 025 est obligatoire avant tout code PriceCheckEngine.

### 2.4 Tension D2 — `evaluation/profiles.py` hors-Couche A

`src/evaluation/profiles.py` contient 10 profils d'évaluation hardcodés (GENERIC, HEALTH, CONSTR, IT, TRAVEL...).
Ces profils incluent des `weight` par catégorie — **sans** `price_ratio_acceptable` / `price_ratio_eleve`.

Ce fichier :
- Existe **hors** de `src/couche_a/` et hors de `src/couche_b/` — localisation ambiguë.
- Contient de la configuration qui, selon ADR-0009 Decision 2, doit venir de `scoring_configs` (DB).
- N'est pas adressé par un ADR existant comme "module neutre documenté".

**Risque** : un agent peut consommer `get_profile_for_category()` dans le PriceCheckEngine sans passer par la DB — contournement silencieux du D1.

---

## 3. AUDIT COUCHE A — L'OUVRIER COGNITIF

### 3.1 Milestones Couche A — État factuel

| Milestone | Statut | Preuve |
|-----------|--------|--------|
| M-SCHEMA-CORE | ✅ DONE | `.milestones/M-SCHEMA-CORE.done` |
| M-DOCS-CORE | ✅ DONE | `.milestones/M-DOCS-CORE.done` |
| M-EXTRACTION-ENGINE | ✅ DONE | `.milestones/M-EXTRACTION-ENGINE.done` |
| M-EXTRACTION-CORRECTIONS | ✅ DONE | `.milestones/M-EXTRACTION-CORRECTIONS.done` |
| M-CRITERIA-TYPING | ✅ DONE | `.milestones/M-CRITERIA-TYPING.done` |
| M-NORMALISATION-ITEMS | ✅ DONE | `.milestones/M-NORMALISATION-ITEMS.done` |
| M-CRITERIA-FK | ✅ DONE | `.milestones/M-CRITERIA-FK.done` |
| **M-SCORING-ENGINE** → **M-PRICE-CHECKING** | ⏳ EN COURS / ADR ACCEPTED | ADR-0009 ACCEPTED, code absent |
| M-COMMITTEE-CORE | ❌ À FAIRE | — |
| M-CBA-GEN | ❌ À FAIRE | — |
| M-PV-GEN | ❌ À FAIRE | — |
| M-PIPELINE-A-E2E | ❌ À FAIRE | — |

**Verdict** : La Couche A fondation est solide (7/7 milestones Phase 0-1 DONE). Phase 2 (scoring → comité → génération) n'est pas commencée. **Sans scoring terminé, aucune génération CBA/PV n'est possible de façon constitutionnelle.**

### 3.2 Violations dans le Scoring Engine existant

Le fichier `src/couche_a/scoring/engine.py` contient trois violations identifiables à la lecture :

#### VIOLATION-A1 — UPSERT sur table `supplier_scores` (ADR-0006)

```python
# src/couche_a/scoring/engine.py ligne ~350
INSERT INTO supplier_scores ...
ON CONFLICT (case_id, supplier_name, category)
DO UPDATE SET score_value = EXCLUDED.score_value, ...
```

**Gravité : CRITIQUE.** ADR-0006 RÈGLE §1 alinéa 4 : "UPDATE direct sur table métier = INTERDIT, bloqué DB-level par trigger." Cette ligne crée un UPDATE déguisé. Si un trigger enforce l'append-only sur `supplier_scores`, ce code cassera en prod. Si pas de trigger, la table n'est pas append-only — violation INV-6.

**Note** : Ce problème était connu (ADR-0005 D2 "UPSERT sur table append-only") mais la correction n'a pas été portée au scoring engine.

#### VIOLATION-A2 — Stub d'élimination silencieux (INV-9)

```python
def _meets_criterion(self, supplier, criterion) -> bool:
    # TODO: Implement actual criterion checking logic
    # For now, assume all suppliers meet criteria (no eliminations)
    return True
```

**Gravité : CRITIQUE.** Toutes les éliminations sont désactivées. Aucun fournisseur n'est jamais éliminé. Le moteur produit des scores sans gate éliminatoire. Ce n'est pas un "stub temporaire" — c'est un mensonge sur la conformité du scoring au moment du merge.

Le `.milestones/` ne montre pas M-SCORING-ENGINE.done — mais si ce code a été mergé sans ce stub documenté en `.done`, c'est une violation du Protocole Militaire (Étape 7 — suite complète).

#### VIOLATION-A3 — Poids hardcodés non traçables (INV-9)

```python
weights = {
    "commercial": 0.50,
    "capacity": 0.30,
    "sustainability": 0.10,
    "essentials": 0.10,
}
```

Ces poids sont des **fallback hardcodés sans traçabilité**. INV-9 : "Aucun coefficient d'ajustement non déclaré." La Constitution exige que le fallback soit tracé dans les notes de résultat. Ces valeurs s'appliquent silencieusement si le profil DB ne surcharge pas — violation directe de ADR-0009 DECISION 2 (fallback obligatoirement tracé).

#### VIOLATION-A4 — Devise hardcodée XOF (§1.2 Constitution)

```python
calculation_details={"price": price, "lowest_price": lowest_price, "currency": "XOF"}
```

La Constitution §1.2 affirme l'universalité du système (DAO/RFQ/RFP, tous pays). XOF hardcodé signifie que le moteur ne fonctionne correctement que pour la zone UEMOA. Une offre en USD, EUR ou TZS serait mal documentée. Violation du principe d'universalité.

### 3.3 Ce que la Couche A fait bien

- La séparation `extraction → normalisation → critères` est rigoureusement implémentée.
- Les corrections append-only (ADR-0006/0007) sont prouvées avec triggers DB et tests CI bloquants.
- Le dictionnaire Sahel V1 avec 9 familles et seeds est fonctionnel.
- La normalisation inclut résolution d'alias + conversion d'unités + flag validation humaine.
- `test_couche_a_b_boundary.py` dans `tests/invariants/` empêche les imports croisés.

---

## 4. AUDIT COUCHE B — LE MOAT

### 4.1 État factuel — Verdict : EMBRYONNAIRE

| Composant Couche B | Attendu (Constitution §3) | Présent dans le code |
|--------------------|--------------------------|----------------------|
| `mercuriale` (source 1) | Tables, ingest, freshness policy | Skeleton `src/couche_b/mercuriale/` — parser.py, schemas.py, aucune table créée |
| `decision_history` (source 2) | Auto-feed post-décision, 24 mois | ❌ ABSENT |
| `market_surveys` (source 3) | Workflow terrain, min 3 cotations, 90 jours | ❌ ABSENT |
| `MarketSignalProvider` | Agrégation 3 sources, règles dégradation | ❌ ABSENT |
| Panneau UI Market Signal | Read-only, indicateurs ⚠️/🔴/⬛ | ❌ ABSENT |
| Fuzzy matching dictionnaire | Levenshtein + token-based < 100ms | `resolvers.py` — partiel (pg_trgm uniquement) |

**Milestones Couche B DONE** : Zéro.  
`M-PARSING-MERCURIALE.done` existe — mais c'est une brique basique, pas le Market Signal complet.

### 4.2 Le Moat — Analyse stratégique brutale

La Constitution §0 dit : *"Établir un standard de référence du procurement moderne en Afrique."*

Le moat du DMS n'est **pas** la génération de CBA/PV. Des outils Excel bien structurés font ça. Le moat est :

1. **La mémoire des prix réels** (source 2 — `decision_history`) : "on a payé X pour Y chez Z en telle zone en telle date." Cela prend **des années** à constituer. Plus tôt on commence à capturer, plus tôt le moat existe.
2. **L'agrégation 3 sources en temps réel** : Market Survey + Mercuriale + Historique — aucun outil concurrent en Afrique de l'Ouest ne fait ça.
3. **La traçabilité décisionnelle comme actif organisationnel** — l'organisation ne dépend plus d'une personne.

**Sans Couche B fonctionnelle, le DMS est un outil puissant mais remplaçable.** Avec Couche B, c'est un actif stratégique irremplaçable au bout de 12-18 mois d'utilisation.

### 4.3 Risque critique — Collecte de données différée

Chaque dossier traité sans capture `decision_history` est une donnée marché perdue. L'organisation cliente perd du terrain sur son propre historique. La Constitution §3.2 source 2 précise "auto-feed post-décision" — ce mécanisme n'existe pas. Chaque processus finalisé ne remonte pas automatiquement dans la Couche B.

**Ce n'est pas une feature optionnelle. C'est une dette de mémoire qui grandit à chaque dossier.**

### 4.4 Ce que la Couche B fait bien

- Le schéma `procurement_dictionary` est seedé avec 9 familles Sahel (migration 022).
- `resolvers.py` — fuzzy matching pg_trgm fonctionnel pour vendor/item/zone.
- La frontière B → A est inviolable par design (INV-3, tests CI).
- La Constitution interdit à B de prescrire ou modifier A — principe implémenté et testé.

---

## 5. COHÉRENCE VISION ↔ DÉVELOPPEMENT

### 5.1 Analyse de cohérence par invariant

| Invariant | Vision Constitution | Réalité code | Écart |
|-----------|--------------------|--------------|----|
| INV-1 — Réduction charge cognitive | `T_DMS < T_manuel × 0.2` | Extraction et normalisation fonctionnelles mais scoring incomplet → pipeline non mesurable | ⚠️ Partiel |
| INV-2 — Primauté Couche A | Couche A autonome sans Couche B | Couche A peut générer sans B (pipeline extraction OK) mais scoring non terminé → pas de CBA complet | ⚠️ Partiel |
| INV-3 — Mémoire non prescriptive | Aucun champ Couche B ne modifie un score | Respecté — tests CI confirment | ✅ |
| INV-4 — Online-first | Pas de mode offline | Respecté | ✅ |
| INV-5 — CI verte obligatoire | Aucun merge CI rouge | Architecture CI solide — MAIS scoring engine livré avec stub silencieux | ⚠️ Tension |
| INV-6 — Append-only | INSERT seul autorisé | Extraction corrections ✅ / Scoring engine UPSERT ❌ | ❌ Violation |
| INV-7 — ERP-agnostique | Aucune dépendance ERP | Respecté — API REST pure | ✅ |
| INV-8 — Survivabilité | Compréhensible par senior en 48h | README, ADRs, Constitution — documentation abondante | ✅ |
| INV-9 — Fidélité au réel | Scores = formule, aucun ajustement caché | Poids hardcodés non tracés, devise XOF hardcodée | ❌ Violation |

### 5.2 Cohérence ADR ↔ Code

| ADR | Décision clé | Respect dans le code |
|-----|-------------|---------------------|
| ADR-0001 | Plan milestones, discipline agents | Respecté — séquence Phase 0 exécutée rigoureusement |
| ADR-0002 | Frontières Couche A/B | Respecté dans la structure — `evaluation/profiles.py` localisation ambiguë |
| ADR-0005 | D2 — Scoring: score_runs (events) + vue current_supplier_scores | **Non appliqué** — scoring engine utilise encore UPSERT |
| ADR-0006 | Zéro UPDATE métier | **Violé** dans scoring engine (UPSERT) |
| ADR-0008 | Protocole militaire, signaux d'arrêt | Appliqué pour les milestones Phase 0-1 |
| ADR-0009 | M-PRICE-CHECKING — Read-only #7 | Non démarré — mais ADR correct et complet |

---

## 6. LE PROJET SERA-T-IL UNIQUE SUR SON CRÉNEAU ?

### Réponse honnête : OUI, mais sous conditions strictes

**Conditions réunies aujourd'hui (avantage concurrentiel réel) :**
- Architecture à deux couches avec frontière inviolable — **personne ne fait ça en Afrique de l'Ouest** pour le procurement.
- Constitution gelée avec invariants CI — niveau de rigueur architecturale rarement vu hors GAFA/licornes.
- Ancrage terrain (Code Marchés Mali, Manuel SCI, mercuriale Sahel) — connaissance métier rare en SaaS procurement Afrique.
- Traçabilité append-only décisionnelle — actif juridique réel (opposabilité des décisions).

**Conditions manquantes pour le game changer (à construire) :**

1. **Market Signal opérationnel** — sans lui, le DMS reste un outil, pas une mémoire.  
   *Timeline estimée pour première valeur réelle : 3-4 mois après démarrage Couche B.*

2. **Auto-feed post-décision** — capture automatique des prix payés.  
   *C'est le mécanisme qui transforme chaque dossier en actif de connaissance.*

3. **PriceCheckEngine fonctionnel** (ADR-0009) — premier signal contextuel intégré dans Couche A.  
   *C'est le pont entre Couche A et Couche B — sans lui, les deux couches restent déconnectées.*

4. **Pipeline E2E Couche A complet** (CBA + PV générés) — la promesse de démo client.  
   *Sans livrable concret (CBA généré), impossible de convaincre un premier adoptant.*

5. **Module Comité** — la conformité réglementaire qui différencie du tableur.

**Verdict final sur l'unicité** : Si les 5 conditions ci-dessus sont remplies d'ici la fin du plan de milestones V3.3.2, le DMS sera **structurellement irremplaçable** sur son créneau Afrique de l'Ouest. Aucun concurrent identifiable ne combine mémoire décisionnelle + conformité réglementaire + Market Signal à 3 sources + génération automatique CBA/PV pour DAO/RFQ/RFP dans ce contexte géographique.

---

## 7. VIOLATIONS ACTIVES DE LA CONSTITUTION

Ces violations existent dans le code mergé et doivent être adressées avant le marquage DONE de tout milestone affecté.

| ID | Fichier | Violation | Invariant/ADR | Gravité |
|----|---------|-----------|---------------|---------|
| V-01 | `src/couche_a/scoring/engine.py:~350` | UPSERT `ON CONFLICT DO UPDATE` sur `supplier_scores` | ADR-0006, INV-6 | 🔴 CRITIQUE |
| V-02 | `src/couche_a/scoring/engine.py:~340` | `_meets_criterion()` retourne `True` systématiquement — éliminations désactivées | INV-9, ADR-0008 ÉTAPE 7 | 🔴 CRITIQUE |
| V-03 | `src/couche_a/scoring/engine.py:~270` | Poids fallback hardcodés sans traçabilité (`commercial: 0.50, capacity: 0.30...`) | INV-9, ADR-0009 D2 | 🟠 ÉLEVÉ |
| V-04 | `src/couche_a/scoring/engine.py:~150` | Devise `"XOF"` hardcodée — violation universalité | Constitution §1.2 | 🟡 MOYEN |
| V-05 | `src/evaluation/profiles.py` | Localisation ambiguë hors Couche A et hors Couche B — module neutre non documenté | ADR-0002, Constitution §2.2 | 🟡 MOYEN |
| V-06 | `scoring_configs` (migration 007) | Colonnes `price_ratio_acceptable` / `price_ratio_eleve` absentes | ADR-0009 D1 | 🟠 ÉLEVÉ |

---

## 8. PISTES DE SOLUTIONS → ADR CANDIDATS

Ces pistes sont directement convertibles en ADRs formels. Chacune suit la structure ADR canonique du projet.

---

### ADR-CANDIDAT-01 — Correction scoring engine : append-only + éliminations réelles

**Problème** : V-01 (UPSERT) + V-02 (stub éliminations).  
**Décision** :
1. Remplacer UPSERT dans `_save_scores_to_db` par INSERT strict dans `score_runs` (événements) + vue `current_supplier_scores` (ADR-0005 D2 — déjà décidé, non implémenté).
2. Implémenter `_meets_criterion()` avec logique réelle basée sur `criteria.type = 'essential'` + `seuil_elimination`.
3. Ajouter trigger append-only sur `supplier_scores` (ou migrer vers `score_runs`).
4. Milestone affecté : ce correctif est prérequis au marquage DONE de M-SCORING-ENGINE / M-PRICE-CHECKING.

**Scope migration** : créer `score_runs` table (INSERT only) + vue `current_supplier_scores`.  
**Tests obligatoires** : `test_scoring_append_only.py` bloquant CI.

---

### ADR-CANDIDAT-02 — Canonisation `evaluation/profiles.py`

**Problème** : V-05 — module flottant entre Couche A et Couche B.  
**Décision** :
1. Déclarer `src/evaluation/` comme **module neutre partagé** (ni Couche A, ni Couche B) — documenté comme tel.
2. Interdire à `price_check/engine.py` de l'utiliser directement — uniquement `scoring_configs` DB (ADR-0009 D2).
3. Conserver `evaluation/profiles.py` comme seed-source pour migration 025 uniquement.
4. Ajouter test CI : `test_price_check_does_not_import_evaluation_profiles`.

**Scope** : documentation uniquement + test CI.

---

### ADR-CANDIDAT-03 — Poids et devises : neutralité universelle

**Problème** : V-03 (poids hardcodés) + V-04 (XOF hardcodé).  
**Décision** :
1. Tout fallback de poids doit être tracé dans `PriceCheckResult.notes` et dans le `calculation_details` de `ScoreResult`.
2. La devise doit être portée par le `Case` (champ `currency`) — jamais hardcodée dans le moteur.
3. Ajouter colonne `currency` à la table `cases` si absente.
4. Test CI : `test_score_currency_from_case_not_hardcoded`.

---

### ADR-CANDIDAT-04 — Auto-feed Couche B : capture décisionnelle obligatoire

**Problème** : Couche B ne capte aucune donnée des dossiers finalisés — dette de mémoire croissante.  
**Décision** :
1. Créer hook `post_case_close(case_id)` — déclenché automatiquement quand un `case_event` de type `closed` est inséré.
2. Ce hook alimente `decision_history` (source 2 Market Signal) avec prix payés, fournisseur retenu, zone, date.
3. Le hook est Couche B, déclenché depuis Couche A via événement — pas d'import direct.
4. Contrainte : le hook ne bloque JAMAIS la clôture du dossier (async ou best-effort loggué).
5. Milestone associé : M-MARKET-INGEST (source 2 spécifiquement).

**Impact stratégique** : C'est le mécanisme qui transforme le DMS en actif de connaissance. Chaque dossier clôturé devient une ligne dans la mémoire marché.

---

### ADR-CANDIDAT-05 — Priorité Couche B : séquençage accéléré

**Problème** : Couche B est en Phase 5 du plan milestones (après Pipeline E2E, Sécurité, etc.). À ce rythme, le Market Signal arrive après 15+ milestones. Le moat est retardé de plusieurs mois.  
**Décision** :
1. Avancer M-MARKET-DATA-TABLES à Phase 2 (parallèle au M-COMMITTEE-CORE).
2. Implémenter la capture `decision_history` (auto-feed source 2) dès Phase 3 — sans attendre le Market Signal complet.
3. Le Market Signal complet (3 sources) reste Phase 5 mais la donnée commence à s'accumuler dès Phase 2-3.
4. Justification : sans données historiques, le Market Signal sera vide à son lancement — inutile pour les premiers clients.

**Note** : Ce séquençage ne viole pas ADR-0001 si validé CTO explicitement dans un ADR dédié.

---

### ADR-CANDIDAT-06 — Tests boundary obligatoires avant M-PRICE-CHECKING DONE

**Problème** : `tests/boundary/` n'existe pas — ADR-0009 D5 l'exige.  
**Décision** :
1. Créer `tests/boundary/test_couche_a_b_boundary.py` (DT-006 — AST boundary check).
2. Créer `tests/boundary/test_constitution_compliance.py` (schéma PriceCheckResult sans champ décisionnel).
3. Ces deux tests sont **BLOQUANTS CI** — sans eux, M-PRICE-CHECKING ne peut pas être marqué DONE.
4. Le test constitution vérifie : absence de `rank`, `winner`, `recommendation`, `selected`, `best_offer`, `shortlist` dans tout schéma Pydantic de l'API `/price-check/*`.

---

## 9. MATRICE DE PRIORITÉ

| Priorité | Action | ADR Candidat | Impact Vision | Effort |
|----------|--------|-------------|---------------|--------|
| 🔴 P0 | Corriger UPSERT scoring + éliminations stub | ADR-C01 | Critique — sans ça, M-PRICE-CHECKING démarre sur une base cassée | Moyen |
| 🔴 P0 | Créer tests/boundary (L6a + L6b) | ADR-C06 | Bloquant DONE ADR-0009 | Faible |
| 🟠 P1 | Migration 025 scoring_configs (D1 ADR-0009) | ADR-0009 D2 déjà décidé | Bloquant PriceCheckEngine | Faible |
| 🟠 P1 | Implémenter price_check module complet | ADR-0009 | Ponts Couche A ↔ Couche B | Moyen |
| 🟠 P1 | Ajouter auto-feed decision_history | ADR-C04 | ★ Moat — commence à accumuler la mémoire | Moyen |
| 🟡 P2 | Canoniser evaluation/profiles.py | ADR-C02 | Prévention dérive future | Faible |
| 🟡 P2 | Neutralité devise (currency from case) | ADR-C03 | Universalité §1.2 | Faible |
| 🟡 P2 | Avancer M-MARKET-DATA-TABLES Phase 2 | ADR-C05 | ★ Moat — séquençage stratégique | ADR requis |
| 🟢 P3 | Pipeline E2E Couche A (CBA + PV) | Milestones existants | Démo client | Élevé |
| 🟢 P3 | Market Signal Engine complet | Milestones Phase 5 | ★★ Differenciateur ultime | Très élevé |

---

## 10. CONCLUSION

### Ce qui est remarquable

Ce projet a quelque chose de rare : **une vision claire, un cadre de gouvernance béton, et une discipline d'exécution qui honore réellement les contraintes qu'elle se fixe**. La Constitution n'est pas un document marketing — elle est encodée dans les tests CI. Les ADRs ne sont pas des formalismes — ils bloquent réellement le merge. Le protocole militaire n'est pas une métaphore — il s'applique à chaque milestone.

Pour un projet solo ou très petite équipe en contexte Afrique de l'Ouest, c'est une maturité architecturale remarquable.

### Ce qui est brutal

La Couche B est vide. Le moat n'existe pas encore. Chaque dossier traité depuis le début du projet sans capture `decision_history` est une donnée marché perdue définitivement. L'urgence n'est pas de finir tous les milestones de la Couche A avant de commencer la Couche B — c'est de **commencer à collecter dès maintenant**, même sommairement.

ADR-0009 est excellent mais non implémenté. Le scoring engine existant contient 3 violations de la Constitution. Ces violations ne bloquent pas le développement futur si elles sont adressées dans le milestone M-PRICE-CHECKING — mais elles ne peuvent pas être ignorées.

### Verdict final sur le game changer

> **Le DMS peut honorer sa vision de game changer. L'architecture le permet. La rigueur le soutient. Mais la promesse de game changer est dans la Couche B, pas dans la Couche A. La Couche A est l'ouvrier qui construit la maison. La Couche B est la mémoire qui fait que la maison vaut plus cher chaque année qu'elle existe. La Couche B est le moat. Et le moat est vide.**

Priorité absolue après M-PRICE-CHECKING : déclencher la capture de données Couche B en parallèle des milestones Couche A restants. Ne pas attendre Phase 5 pour commencer à accumuler la mémoire marché.

---

*Audit produit en lecture seule — zéro modification de fichier existant.*  
*Pistes de solutions soumises sous forme d'ADR candidats — conversion en ADRs formels requiert validation CTO explicite.*  
*Opposable selon ADR-0008 §6 : "preuve > narration".*
