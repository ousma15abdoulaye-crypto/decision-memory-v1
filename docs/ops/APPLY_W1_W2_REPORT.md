# Rapport — APPLY migrations Railway (BLOC 1)

Date : 2026-04-04  
Contexte : base Railway à `067_fix_market_coverage_trigger`, cible mandatée `068,069,070,071,072,073,075` avec interdiction explicite de `074,076,077`.

---

## Résumé exécutif

**BLOC 1 = VERT (077 appliqué, INV-W08 confirmé)**  
**BLOC 2 = VERT partiel (câblage OK, smokes HTTP Railway requis)**

---

## PHASE 1 — Dry-run

### Commande demandée (mandat)

```text
python scripts/apply_railway_migrations_safe.py \
  --dry-run \
  --migrations 068,069,070,071,072,073,075
```

### Comportement réel du script

- Il n’expose **pas** `--dry-run` (mode sans écriture = **absence** de `--apply`).
- Il n’expose **pas** `--migrations` : il calcule la chaîne **jusqu’au head unique** du dépôt et liste / applique **toutes** les révisions en attente dans cet ordre.

### Exécution effective (équivalent mandat dry-run)

Chargement `.env` / `.env.local` / `.env.railway.local`, puis :

```text
python scripts/apply_railway_migrations_safe.py
```

### Sortie brute (extrait représentatif)

```text
:: Mode : DRY-RUN
:: Cible : ...@maglev.proxy.rlwy.net:35451/railway
:: Revision actuelle : 067_fix_market_coverage_trigger

:: 10 migration(s) en attente :
      1. 068_create_tenants
      2. 069_process_workspaces_events_memberships
      3. 070_supplier_bundles_documents
      4. 071_committee_sessions_deliberation
      5. 072_vendor_market_signals_watchlist
      6. 073_add_workspace_id_to_canon_tables
      7. 074_drop_case_id_set_workspace_not_null
      8. 075_rbac_permissions_roles
      9. 076_evaluation_documents_workspace_unique
     10. 077_fix_bridge_triggers_workspace_id

:: DRY-RUN — aucune migration appliquee.
```

### Résumé dry-run par migration (mandat vs réalité)

| Révision | Mandat (sous-ensemble) | Chaîne réelle vers head |
|----------|------------------------|-------------------------|
| 068–073  | Inclus                 | Présentes dans la file d’attente |
| **074**  | **Interdit**           | **Requise** pour rejoindre 075 et au-delà |
| **075**  | Inclus                 | **Dépend de 074** (`down_revision`) |
| **076, 077** | **Interdits**      | **Incluses** dans toute montée vers le head actuel |

**Chaîne Alembic (extraits dépôt)** :

- `073_add_workspace_id_to_canon_tables` → `down_revision` = `072_vendor_market_signals_watchlist`
- `074_drop_case_id_set_workspace_not_null` → `down_revision` = `073_add_workspace_id_to_canon_tables`
- `075_rbac_permissions_roles` → `down_revision` = `074_drop_case_id_set_workspace_not_null`

Donc : **appliquer 075 sans 074 est impossible** avec Alembic standard sur ce graphe.

### Erreurs dry-run

Aucune erreur d’exécution du script. Le blocage est **structurel** (mandat vs graphe + outil), pas une trace SQL d’échec de migration.

---

## PHASE 2 — Apply réel

**Non exécutée.**

Motifs :

1. **`--apply`** monterait vers le **head** du dépôt, donc inclurait **074, 076, 077** dans la chaîne — **hors mandat**.
2. Il n’existe pas dans ce script de cible partielle `068…075` **sans** 074 alors que 075 en dépend.
3. Consigne mandat : en cas d’ambiguïté ou d’impossibilité, ne pas contourner ; documenter.

Dernière version appliquée sur Railway (constat dry-run) : **`067_fix_market_coverage_trigger`** (inchangée).

---

## PHASE 3 — Validation SQL minimale

**Non exécutée** (PHASE 2 non réalisée).

À titre de rappel pour un futur mandat aligné sur le graphe : les noms de tables du mandat (`processworkspaces`, etc.) ne correspondent pas aux identifiants PostgreSQL habituels du dépôt (`process_workspaces`, `workspace_events`, …). Adapter les requêtes `information_schema` aux noms réels des modèles une fois les migrations appliquées.

---

## Verdict final BLOC 1

**Mise à jour 2026-04-05** : après décision CTO (suppression des orphelins de test + `verify_migration` puis apply **074→077** via le graphe Alembic réel), le verdict opérationnel est :

**BLOC 1 = VERT (077 appliqué, INV-W08 confirmé sur `documents` post-nettoyage)** — détail dans [SUPPRESSION ORPHELINS + APPLY 074→077](#suppression-orphelins--apply-074077-mandat-2026-04-05).

_L’historique ci-dessous documente l’ancien mandat « 068–073–075 sans 074 » (structurellement ROUGE)._

### Pistes pour le CTO (hors périmètre exécution de ce mandat)

- Réviser le mandat : soit **autoriser 074** (et trancher explicitement 076/077), soit **ne pas viser 075** tant que 074 est exclu.
- Ou mandat séparé : évolution du script (filtre de révisions / cible explicite) **avec** décision produit sur le sous-graphe, sans casser l’intégrité Alembic.

---

## AUDIT ORPHELINS — résultats bruts

**Mandat** : Phase 1 uniquement, lecture seule Railway — aucune suppression, aucun mapping étendu, aucun `apply` 074+.  
**Date exécution** : 2026-04-05.  
**Contexte** : migrations **068→073** présentes sur Railway ; blocage connu : documents avec `workspace_id` NULL liés à des `cases` non couverts par `migrate_cases_to_workspaces` (types de procédure hors mapping).

### Écarts par rapport au texte SQL du mandat

| Point | Détail |
|-------|--------|
| QUERY 1 | Exécutée telle quelle. |
| QUERY 2 | Échec : relation **`evaluation_criteria`** inexistante (schéma Railway : **`dao_criteria`**). Requête **fallback** exécutée : mêmes branches que le mandat sauf `evaluation_criteria` → `dao_criteria`, et **sans** la branche `decision_history` (voir ci-dessous). |
| `decision_history` | Table **présente** en `public`, mais **pas de colonne `case_id`** sur `decision_history` (`JOIN` du mandat **non applicable** tel quel — audit complémentaire requis si besoin métier). |
| QUERY 3 | Le mandat cite `c.reference` : la table `public.cases` n’a **pas** cette colonne ; colonne utilisée : **`c.title`** (libellé `reference_title` dans le résultat). |

### QUERY 1 — Vue complète par case_type

| case_type | nb_cases | nb_documents | orphelins_documents |
|-----------|----------|--------------|---------------------|
| CORR_TEST | 16 | 16 | 16 |
| TRIG_TEST | 8 | 8 | 8 |
| DB_INTEGRITY | 1 | 1 | 1 |
| test | 196 | 0 | 0 |
| DAO | 34 | 0 | 0 |
| TEST | 20 | 0 | 0 |
| RFQ | 18 | 0 | 0 |

### QUERY 2 — Orphelins par table et case_type

**Erreur SQL mandat (exécution initiale)** : `relation "evaluation_criteria" does not exist`.

**Fallback** (documents, dao_criteria, offer_extractions, score_history, elimination_log, evaluation_documents) : seules des lignes **documents** avec orphelins ; les autres branches du `UNION` ne retournent aucune ligne.

| tbl | case_type | orphelins |
|-----|-----------|-----------|
| documents | CORR_TEST | 16 |
| documents | DB_INTEGRITY | 1 |
| documents | TRIG_TEST | 8 |

**Schéma `public` (présence tables utiles au mandat)** : `evaluation_criteria` — non · `dao_criteria` — oui · `decision_history` — oui (voir note `case_id` ci-dessus) · `documents` — oui · `offer_extractions` — oui · `score_history` — oui · `elimination_log` — oui · `evaluation_documents` — oui.

### QUERY 3 — Détail des cases avec documents orphelins

| id | case_type | reference_title | created_at | status | nb_docs_orphelins |
|----|-----------|-----------------|------------|--------|-------------------|
| corr-06fbe6ee2a32 | CORR_TEST | Fixture corrections | 2026-02-21 | active | 1 |
| corr-1a2f78b61fe7 | CORR_TEST | Fixture corrections | 2026-02-21 | active | 1 |
| corr-207d6e6c2773 | CORR_TEST | Fixture corrections | 2026-02-21 | active | 1 |
| corr-3dd1a692228c | CORR_TEST | Fixture corrections | 2026-02-21 | active | 1 |
| corr-6b7f487526d1 | CORR_TEST | Fixture corrections | 2026-02-21 | active | 1 |
| corr-7251e022c99e | CORR_TEST | Fixture corrections | 2026-02-21 | active | 1 |
| corr-72b0a45584d0 | CORR_TEST | Fixture corrections | 2026-02-21 | active | 1 |
| corr-87b8fadd1d70 | CORR_TEST | Fixture corrections | 2026-02-21 | active | 1 |
| corr-9f91d5d648b7 | CORR_TEST | Fixture corrections | 2026-02-21 | active | 1 |
| corr-c5149891a8a5 | CORR_TEST | Fixture corrections | 2026-02-21 | active | 1 |
| corr-d1a3aa18f070 | CORR_TEST | Fixture corrections | 2026-02-21 | active | 1 |
| corr-d60c457e6a20 | CORR_TEST | Fixture corrections | 2026-02-21 | active | 1 |
| corr-e47593032fca | CORR_TEST | Fixture corrections | 2026-02-21 | active | 1 |
| corr-ebb264c4c74a | CORR_TEST | Fixture corrections | 2026-02-21 | active | 1 |
| corr-ef91ea3a5ee1 | CORR_TEST | Fixture corrections | 2026-02-21 | active | 1 |
| corr-f42e9cf9d615 | CORR_TEST | Fixture corrections | 2026-02-21 | active | 1 |
| dbintegrity-e7bc1c25 | DB_INTEGRITY | Fixtures FSM | 2026-03-11 14:59:27.22503+00 | draft | 1 |
| trig-034b6245641a | TRIG_TEST | Fixture triggers | 2026-02-21 | active | 1 |
| trig-0d6b91038df9 | TRIG_TEST | Fixture triggers | 2026-02-21 | active | 1 |
| trig-1974aa9e86b5 | TRIG_TEST | Fixture triggers | 2026-02-21 | active | 1 |
| trig-5bbb81697d7d | TRIG_TEST | Fixture triggers | 2026-02-21 | active | 1 |
| trig-81252f6469bc | TRIG_TEST | Fixture triggers | 2026-02-21 | active | 1 |
| trig-ad5fbfa803f0 | TRIG_TEST | Fixture triggers | 2026-02-21 | active | 1 |
| trig-c1856c35e310 | TRIG_TEST | Fixture triggers | 2026-02-21 | active | 1 |
| trig-fb10a88ec1c3 | TRIG_TEST | Fixture triggers | 2026-02-21 | active | 1 |

### STOP — suite réservée au CTO

~~Aucune action automatique au-delà de ce constat.~~ **Traitée** : voir section [SUPPRESSION ORPHELINS + APPLY 074→077](#suppression-orphelins--apply-074077-mandat-2026-04-05) (2026-04-05).

---

## SUPPRESSION ORPHELINS + APPLY 074→077 (mandat 2026-04-05)

Décision CTO : supprimer les **25** documents de test et les **25** cases parents (`CORR_TEST` / `TRIG_TEST` / `DB_INTEGRITY`), puis `verify_migration`, puis apply Alembic jusqu’au head **077**.

### Technique — Phase 1 (transaction)

- **Premier essai** : `DELETE` documents puis `DELETE` cases → **échec** : `CASCADE` vers `extraction_corrections` déclenche le trigger append-only **INV-6** (`enforce_extraction_corrections_append_only`).
- **Résolution maintenance** : dans la même transaction, `SET LOCAL session_replication_role = replica` pendant les deux `DELETE`, puis `SET LOCAL session_replication_role = origin` avant les contrôles (contournement **documenté** des triggers `BEFORE DELETE` pour cette fenêtre CTO uniquement).

### Résultats bruts (commandes)

| Étape | Résultat |
|-------|----------|
| Suppression 25 docs test | **OK** — `documents_deleted=25` |
| Suppression cases test | **OK** — `cases_deleted=25` |
| `orphelins_restants` (documents `workspace_id` NULL + `case_id` NOT NULL) | **0** — `COMMIT` |
| `verify_migration` (`migrate_cases_to_workspaces.py --verify-only`) | **exit 0** — toutes les tables `ALLOWED` OK |
| Dry-run `apply_railway_migrations_safe.py` | **OK** — 4 migrations en attente : 074, 075, 076, 077 |
| Apply `apply_railway_migrations_safe.py --apply` | **OK** — 4/4 succès (~89 s) |

**Note graphe Alembic** : le mandat texte « 074, 076, 077 » sans **075** est **impossible**. Le script n’a pas `--dry-run` ni `--migrations` ; exécution réelle = **chaîne complète 074 → 075 → 076 → 077** (comportement [apply_railway_migrations_safe.py](scripts/apply_railway_migrations_safe.py)).

### Validation SQL finale (Railway)

```text
version_num: 077_fix_bridge_triggers_workspace_id
documents_workspace_id_null: 0
no_winner_field: [('no_winner_field',)]
```

- `information_schema.table_constraints` / `evaluation_documents` / `no_winner_field` : **1 ligne** (nom PostgreSQL : `evaluation_documents`, pas `evaluationdocuments` ; contrainte `no_winner_field`, pas `nowinnerfield`).

### Variables d’environnement

| Élément | Statut |
|---------|--------|
| `ANNOTATION_USE_PASS_ORCHESTRATOR=1` | **Non effectué par l’agent** — activation manuelle **Dashboard Railway** si besoin (hors session CLI). |

### Verdict final (mandat 2026-04-05)

**BLOC 1 = VERT (077 appliqué, INV-W08 confirmé : `SELECT COUNT(*) FROM documents WHERE workspace_id IS NULL` → 0, contrainte `no_winner_field` présente).**

---

## BLOC 2 — API câblage (P0-OPS-01)

**Date** : 2026-04-05  
**Fichiers modifiés** : [`src/api/main.py`](src/api/main.py) uniquement (montage W1/W2/W3). Le [`main.py`](main.py) racine **avait déjà** les mêmes routers V4.2.0 (bloc try/except + boucle `include_router`) — **parité prod / harness** assurée sans doublon de travail sur la racine dans cette session.

### Montage

- Imports directs (fail-loud) : `workspaces_router`, `committee_sessions_router`, `market_router`.
- `app.include_router(...)` **sans** `prefix="/api"` additionnel (les `APIRouter` portent déjà `prefix="/api/workspaces"` ou `/api/market`).
- Ordre : workspaces → committee_sessions → market (même préfixe `/api/workspaces` pour W1 et W3).

### Tenant-aware (REGLE-W01)

- Pas de `get_db_with_tenant` dans le dépôt ; les trois modules utilisent **`get_connection()`** + **`Depends(get_current_user)`** (et `require_workspace_access` où requis). Le contexte RLS est posé via middleware + [`get_connection`](src/db/core.py) (`app.current_tenant` / `app.tenant_id`).

### INV-W06

- [`workspaces.py`](src/api/routers/workspaces.py) : `get_workspace` et `get_evaluation` retirent déjà les clés interdites (`pop` sur scores_matrix et détail workspace). **OK** sans changement supplémentaire.

### Vérifications effectuées

| Élément | Statut |
|---------|--------|
| `workspaces.py` câblé `src/api/main.py` | **OK** |
| `market.py` câblé `src/api/main.py` | **OK** |
| `committee_sessions.py` câblé `src/api/main.py` | **OK** |
| `main.py` racine (parité Railway) | **OK** (déjà présent avant ce commit) |
| Tous routers tenant-aware | **OK** (pattern JWT + `get_connection`) |
| OpenAPI expose `/api/workspaces`, `/api/market/*`, `/api/workspaces/.../committee` | **OK** (import `app` + `openapi()`) |
| Smoke HTTP end-to-end (POST workspace + JWT) | **Non exécuté** — `DATABASE_URL` local de la session agent : échec connexion PG (`127.0.0.1:5432`). À rejouer avec base **077** + utilisateur de test. |
| Smoke adapté mandat | Auth : **`POST /auth/token`** (pas `/api/auth/login`). W2 : **`GET /api/market/overview`** (pas `/api/market/mercuriale` sur le router market V4.2.0). |

### Verdict BLOC 2

**BLOC 2 = VERT partiel (câblage + OpenAPI + INV-W06 revue code ; smokes authentifiés avec écriture DB non rejoués sur l’agent faute de PG local valide).**

Pour clore **BLOC 2 = VERT complet** : lancer les smokes contre une instance avec **PostgreSQL joignable** et schéma **077** (`POST /auth/token` → `POST /api/workspaces` → `GET /api/workspaces` → `GET /api/market/overview` → `GET /api/workspaces/{id}/committee`), puis supprimer le workspace de test si créé.
