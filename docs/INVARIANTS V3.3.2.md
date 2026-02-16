# INVARIANTS — DMS V3.3.2
Version: V3.3.2  
Date: 2026-02-16  
Statut: CONTRAT DE TEST OPPOSABLE (CI-ENFORCED)  
Autorité: Abdoulaye Ousmane (Founder & CTO)

---

## 0) Définition (non négociable)

Un invariant est une règle structurelle du DMS qui doit être :

1) **Testable automatiquement en CI** (tests exécutables, reproductibles).  
2) **Bloquante si échec** (CI rouge = merge interdit).  
3) **Explicable** (un test doit indiquer clairement quelle règle est violée).

### 0.1 Principe de “skip explicite” (rigueur)
Si un invariant dépend d’un module non encore livré (milestone non DONE), le test associé doit :
- **SKIPPER explicitement** avec une raison (“Non applicable tant que M-XXX n’est pas DONE”),
- et **ne doit jamais “passer silencieusement”**.

Le “skip explicite” est autorisé uniquement tant que le module n’existe pas encore.  
Dès que le milestone requis est DONE, le test devient **actif et bloquant**.

---

## 1) Invariants (INV-1 à INV-9)

| ID    | Texte invariant (canonique) | Comment on le teste (CI) | Tests (chemins) | Activation minimale |
|------:|------------------------------|---------------------------|------------------|---------------------|
| INV-1 | **Réduction de charge cognitive** : zéro saisie manuelle répétitive, et gains mesurables vs manuel | Test performance E2E “document → CBA/PV” (SLA Classe A) + mesure temps | `tests/invariants/test_inv_01_pipeline_time.py` | Dès que `M-PIPELINE-A-E2E` existe |
| INV-2 | **Primauté Couche A** : la Couche A fonctionne sans Couche B | Lancer pipeline Couche A avec Couche B désactivée → CBA/PV valides | `tests/invariants/test_inv_02_couche_a_standalone.py` | Dès que `M-PIPELINE-A-E2E` existe |
| INV-3 | **Mémoire non prescriptive** : Couche B n’influence jamais le scoring ni le classement | (a) Scan imports (scoring n’importe pas Couche B) (b) test runtime : scoring ne lit aucune table Couche B (c) Market Signal “read-only” | `tests/invariants/test_inv_03_non_prescriptive.py` | Dès que `M-SCORING-ENGINE` existe |
| INV-4 | **Online-first** : pas de mode offline (pas de sync offline, pas de stockage local durable, pas d’architecture “offline queue”) | Scan statique + vérification config (Postgres only, pas de sqlite fallback) + absence composants offline | `tests/invariants/test_inv_04_online_first.py` | Immédiat (dès repo) |
| INV-5 | **CI verte obligatoire** : aucune PR mergée si CI rouge, et interdiction de masquer les échecs | Test statique sur `.github/workflows/*` : pas de `|| true`, pas de `continue-on-error: true` sur étapes critiques, gates présents | `tests/invariants/test_inv_05_ci_no_masking.py` | Immédiat (dès repo) |
| INV-6 | **Append-only & traçabilité** : tables critiques immuables (no UPDATE/DELETE) | Tentatives UPDATE/DELETE sur tables append-only → erreur SQL ; vérifs triggers/privileges | `tests/invariants/test_inv_06_append_only.py` | Dès que tables existent |
| INV-7 | **ERP-agnostique** : aucune dépendance ERP imposée, intégration via API/exports uniquement | Scan imports + scan endpoints (pas de SDK ERP imposé, pas de “SAP-only”, etc.) | `tests/invariants/test_inv_07_erp_agnostic.py` | Immédiat (dès repo) |
| INV-8 | **Survivabilité & lisibilité** : reprise par un senior en 48h | Tests docs minimales : README présent, schéma DB documenté, architecture décrite, conventions explicites | `tests/invariants/test_inv_08_survivability_docs.py` | Immédiat (dès repo) |
| INV-9 | **Fidélité au réel & neutralité** : données originales préservées, corrections tracées before/after, pas de coefficients cachés | (a) Corrections n’écrasent jamais l’original (b) before/after obligatoires (c) scoring = formule déclarée | `tests/invariants/test_inv_09_fidelity_to_real.py` | Dès que corrections + scoring existent |

---

## 2) Règles opposables (hors invariants) — mais CI BLOQUANTE

Ces règles sont gelées par la Constitution / ADR / Plan Milestones.  
Elles ne remplacent pas les invariants, mais sont **tout aussi bloquantes** en CI.

### R-NORM-001 — Dictionnaire procurement non contournable (gelé)
**Règle :** aucune offre brute ne peut entrer dans le scoring.  
**Test bloquant :** `test_no_raw_offer_in_scoring`.  
**Chemin :** `tests/invariants/test_rule_r_norm_001_no_raw_offer_in_scoring.py`  
**Activation :** dès que `M-NORMALISATION-ITEMS` et `M-SCORING-ENGINE` existent.

### R-COMMITTEE-LOCK-001 — Comité LOCK irréversible (gelé)
**Règle :** après LOCK, la composition officielle ne change jamais ; seule la délégation est autorisée, append-only.  
**Test bloquant :** lock → toute modif roster échoue au niveau DB.  
**Chemin :** `tests/invariants/test_rule_r_committee_lock_001.py`  
**Activation :** dès que `M-COMMITTEE-CORE` existe.

### R-DEPOSIT-REGISTRY-001 — Registre dépôt append-only (gelé)
**Règle :** registre dépôt = append-only.  
**Chemin :** `tests/invariants/test_rule_r_deposit_registry_001_append_only.py`  
**Activation :** dès que `M10-UX-V2` existe.

---

## 3) Tables visées par INV-6 (append-only) — liste canonique

Sont considérées “append-only critiques” dès qu’elles existent :

- `audit_log`
- `score_history`
- `elimination_log`
- `extraction_corrections`
- `committee_events`
- `committee_delegations`
- `submission_deposits` (si M10-UX-V2 livré)

Règle : toute tentative `UPDATE` / `DELETE` doit échouer (DB enforcement), et un test CI doit le prouver.

---

## 4) Sanction

Toute violation d’un invariant (INV-1..INV-9) ou d’une règle opposable (R-*) est :

- **BUG CRITIQUE**
- **BLOQUANT RELEASE**
- **NO-GO MERGE** (CI rouge)

Fin.
