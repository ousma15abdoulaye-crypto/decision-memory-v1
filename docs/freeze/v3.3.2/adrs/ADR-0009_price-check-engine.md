# ADR-0009 — PRICECHECK ENGINE & EVALUATION PROFILES (Couche A)
**Status     :** ACCEPTED  
**Date       :** 2026-02-22  
**Décideur   :** CTO Abdoulaye Ousmane  
**Contexte   :** DMS V3.3.2 — bloquants D1/D2/D3 identifiés à l'Étape 0 de #7 (ex-M-SCORING-ENGINE)  
**Références :** ADR-0001, ADR-0002, ADR-0008, Constitution V3.3.2 (`no_scoring_no_ranking_no_recommendations=true`), DT-006 

## 1. Problème

Trois bloquants opposables détectés à l'Étape 0 :

- **D1** — Seuils prix absents de DB : risque de hardcode silencieux (non opposable).
- **D2** — Contrainte constitutionnelle : `scoring/ranking/recommendations` interdit (`no_scoring_no_ranking_no_recommendations=true`).
- **D3** — Tables scores existantes : `submission_scores` / `supplier_scores` existent → risque de duplication + écriture prématurée.

---

## 2. Décisions

### DECISION 1 — Requalification #7 (Constitution compliance)

Le milestone **#7 implémente un PriceCheck Engine (Couche A)**, pas un scoring engine.

Le PriceCheck Engine produit un `PriceCheckResult` **descriptif** :

- métriques (`prix_ref`, `ratio`, `notes`)
- verdict **non décisionnel**

**Interdits (Constitution) — irrévocables :** tout champ ou comportement de type  
`rank`, `winner`, `recommendation`, `selected`, `best_offer`, `shortlist`.

#### Nomenclature verdict (irrévocable)

Avant gel définitif des verdicts, **preuve DB obligatoire** :

```sql
-- Adapter <colonne_verdict> au schéma réel si elle existe
SELECT DISTINCT <colonne_verdict> FROM submission_scores;
SELECT DISTINCT <colonne_verdict> FROM supplier_scores;
````

* Si nomenclature existante → **l'adopter** (pas de 3ème nomenclature).
* Si rien d'existant → nomenclature ADR-0009 :

| Verdict    | Signification                        |
| ---------- | ------------------------------------ |
| WITHIN_REF | Prix dans la référence acceptable    |
| ABOVE_REF  | Prix au-dessus du seuil acceptable   |
| NO_REF     | Aucune offre de référence disponible |

Choix justifié : plus lisible et moins décisionnel que `ACCEPTABLE/ELEVE/INACCEPTABLE`.

---

### DECISION 2 — Seuils prix opposables (source unique : `public.scoring_configs`)

**Source unique :** `public.scoring_configs`
**Interdit :** création d'une table `scoring_rules` (doublon).

#### Preuve DB avant migration

Avant tout `ALTER TABLE`, produire la preuve des colonnes existantes :

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'scoring_configs'
ORDER BY ordinal_position;
```

#### Colonnes à garantir

Si absentes, les ajouter via migration additive idempotente :

```sql
-- alembic/versions/025_alter_scoring_configs.py

ALTER TABLE scoring_configs
  ADD COLUMN IF NOT EXISTS profile_code           TEXT          NOT NULL DEFAULT 'GENERIC',
  ADD COLUMN IF NOT EXISTS price_ratio_acceptable NUMERIC(6,4)  NOT NULL DEFAULT 1.0500,
  ADD COLUMN IF NOT EXISTS price_ratio_eleve      NUMERIC(6,4)  NOT NULL DEFAULT 1.2000;

-- Contrainte unicité profil
ALTER TABLE scoring_configs
  ADD CONSTRAINT uq_scoring_configs_profile_code UNIQUE (profile_code);

-- Contrainte ordre seuils
ALTER TABLE scoring_configs
  ADD CONSTRAINT chk_ratio_order
  CHECK (price_ratio_acceptable < price_ratio_eleve);
```

**Règle head unique Alembic :** guard CI actif — la migration 025 ne doit pas créer de tête multiple.

#### Résolution des seuils (ordre opposable)

1. `scoring_configs WHERE profile_code = <family_code>`
2. `scoring_configs WHERE profile_code = 'GENERIC'`
3. **Fallback code** (autorisé uniquement si `scoring_configs` est vide) :

   * acceptable = `1.05`, eleve = `1.20`
   * **Obligation :** tracer dans `PriceCheckResult.notes` :
     `"fallback hardcoded — scoring_configs empty"`

**Règle absolue :** aucun fallback silencieux.

---

### DECISION 3 — Read-only strict sur #7

#7 est **READ ONLY**. Aucune écriture dans :

* `submission_scores`
* `supplier_scores`

Persistance des scores = **#9 M-COMMITTEE-CORE**, pas avant.

---

### DECISION 4 — Router (décision unique, finale)

**Prefix :** `/price-check` (pas `/scoring`)

Endpoints :

* `POST /price-check/analyze`
* `POST /price-check/analyze-batch`

Aucune exception. Tout endpoint `/scoring` est considéré dérive sémantique.

---

### DECISION 5 — Garde-fous CI dans le scope #7 (pas "plus tard")

Deux tests bloquants dans #7 :

#### L6a — Boundary AST (DT-006)

Empêche imports directs Couche A → modules internes Couche B (ADR-0002 §2.4).

* `tests/boundary/test_couche_a_b_boundary.py`

#### L6b — Constitution compliance test

Vérifie :

1. Le schéma `PriceCheckResult` ne contient aucun champ décisionnel (`rank`, `winner`, `recommendation`, `selected`, etc.)
2. Les réponses des endpoints `/price-check/*` ne contiennent pas ces clés

* `tests/boundary/test_constitution_compliance.py`

Ces deux tests sont obligatoires pour marquer #7 DONE.

---

## 3. Conséquences sur mandat #7 (livrables renommés)

Le numéro **#7 reste gelé** (plan inviolable). Les livrables sont renommés pour refléter la Constitution :

| Livrable                                         | Statut                                                                             |
| ------------------------------------------------ | ---------------------------------------------------------------------------------- |
| `src/couche_a/price_check/schemas.py`            | À créer                                                                            |
| `src/couche_a/price_check/engine.py`             | À créer                                                                            |
| `src/api/routers/price_check.py`                 | À créer                                                                            |
| `alembic/versions/025_alter_scoring_configs.py`  | Conditionnel après preuve DB                                                       |
| `tests/price_check/test_price_check_engine.py`   | À créer                                                                            |
| `tests/boundary/test_couche_a_b_boundary.py`     | À créer (DT-006)                                                                   |
| `tests/boundary/test_constitution_compliance.py` | À créer                                                                            |
| `.milestones/M-SCORING-ENGINE.done`              | Inclut section "Constitution compliance" + inventaire `src/evaluation/profiles.py` |

---

## 4. Alternatives rejetées (opposables)

| Alternative                                             | Raison du rejet                    |
| ------------------------------------------------------- | ---------------------------------- |
| Hardcoder `1.05/1.20`                                   | Non opposable — viole INV-9        |
| Créer table `scoring_rules`                             | Doublon `scoring_configs`          |
| Écrire dans `submission_scores`/`supplier_scores` en #7 | Décisionnel prématuré — réservé #9 |
| Garder prefix `/scoring`                                | Dérive sémantique Constitution     |
| "Constitution test later"                               | Dette non datée = non contrainte   |

---

## 5. Références

| Référence           | Objet                                           |
| ------------------- | ----------------------------------------------- |
| ADR-0001            | Architecture Couche A/B                         |
| ADR-0002            | Frontières et contrats inter-couches            |
| ADR-0008            | Protocole militaire (preuve > narration)        |
| Constitution V3.3.2 | `no_scoring_no_ranking_no_recommendations=true` |
| DT-006              | Boundary AST test (Couche A/B)                  |

