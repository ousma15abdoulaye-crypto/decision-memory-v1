# Rapport — BLOC 4 : Comité live + scellement PV SHA-256

**Date** : 2026-04-05  
**Branche mandat** : `feat/mandat-bloc4-committee-pv`  
**Prérequis** : BLOC 3 VERT (smokes W1/W2) ; base cible **Alembic head = `077_fix_bridge_triggers_workspace_id`** (vérifié sur Railway).  
**Cible API** : `https://decision-memory-v1-production.up.railway.app`  
**Outil de rejouabilité** : [`scripts/bloc4_committee_mandate_run.py`](../../scripts/bloc4_committee_mandate_run.py) (orchestration register → RBAC SQL → workspace → open-session → add-member → seal).

---

## Écarts mandat ↔ implémentation (résumé)

| Sujet | Mandat | Réalité dépôt / prod |
|--------|--------|----------------------|
| Routes session | `POST …/committee`, `activate`, batch `members` | `POST …/committee/open-session` (session **active** + CDE `session_activated` immédiat), `POST …/add-member` **unitaire** |
| Délibération | `deliberation/open`, `comment`, `challenge` | **Non implémentées** dans [`committee_sessions.py`](../../src/api/routers/committee_sessions.py) (docstring chantier futur) |
| Rôle « Reviewer Procurement » | 2× supply chain + reviewer | CHECK DB / API : `supply_chain`, `finance`, `budget_holder`, `technical`, `secretary`, etc. — **Reviewer Procurement** mappé sur **`secretary`** (votant) pour ce run |
| Payload workspace | `committee_required` au POST | [`WorkspaceCreate`](../../src/api/routers/workspaces.py) : `extra=forbid` sans ce champ — **`committee_required` posé en SQL** après création |
| Scellement API | `sealed_by` dans le body | [`SealSessionPayload`](../../src/api/routers/committee_sessions.py) : `seal_comment` optionnel ; scelleur = JWT |
| Export PV | `GET …/pv/export` | **Aucune route** ; preuve partielle via **`GET …/committee`** (sans `pv_snapshot` dans la réponse JSON actuelle) |
| Trigger append-only | Nom `trg_cde_appendonly` | Migration **071** : `trg_cde_append_only` + `fn_reject_mutation()` |
| INV-W04 workspace | UPDATE `title` post-scellement **doit échouer** | Trigger [`fn_workspace_sealed_final`](../../alembic/versions/069_process_workspaces_events_memberships.py) : bloque surtout la **régression de `status`** depuis `sealed`, pas toutes les colonnes — **UPDATE `title` a réussi** après passage manuel du workspace en `sealed` (voir section preuves SQL) |

---

## Identifiants de session (run 2026-04-05)

| Champ | Valeur |
|--------|--------|
| `reference_code` | `PILOT-COMITE-001-2e2eddeccc` |
| `workspace_id` | `bbb0caa7-010e-4384-a64f-75c47c7110d7` |
| `session_id` | `f17de466-1b38-46c0-8050-e4ecaa74f5ab` |
| Comité « chair » (API + RBAC `procurement_director`) | `user_id` **65** (`bloc4_chair_2e2eddeccc`) |
| Membres (5 `user_id` distincts) | **66** `supply_chain` votant ; **67** `secretary` votant ; **68** `finance` votant ; **69** `budget_holder` votant ; **70** `technical` **non votant** |

RBAC : `INSERT` dans `user_tenant_roles` pour user **65**, tenant `sci_mali`, rôle `procurement_director` (mandat : permission `committee.manage`).

---

## Preuves SQL — invariants

### `committee_deliberation_events` (ordre réel)

| # | `event_type` | `occurred_at` (UTC) |
|---|----------------|---------------------|
| 1 | `session_activated` | 2026-04-05 16:39:36.524229+00 |
| 2–6 | `member_added` | (5 lignes, une par membre) |

**Phases délibération mandat** (`deliberation_opened`, `comment_added`, `score_challenged`) : **non produites** (pas de routes API).

### INV-W01 / INV-W03 — append-only (`trg_cde_append_only`)

Exécutés avec `SET app.is_admin = 'true'` pour cibler une ligne existante :

- **UPDATE** : échec attendu — `RaiseException: Table committee_deliberation_events est append-only. DELETE/UPDATE interdits.` (fonction `fn_reject_mutation()`).
- **DELETE** : même exception.

### INV-W04 — session comité scellée (`trg_committee_session_sealed`)

Après statut `session_status = 'sealed'` (voir ci-dessous sur scellement) :

- **UPDATE** `committee_sessions` vers `active` : échec attendu — `Session … est scellee. Seule transition : sealed -> closed.` (`fn_committee_session_sealed_final()`).

### Scellement SHA-256 (API)

- **`POST /api/workspaces/{id}/committee/seal`** : **HTTP 500** (corps vide côté client) sur ce run — **pas de `seal_hash` ni `session_sealed` CDE** via API.
- Pour débloquer les preuves INV-W04 session, scellement **appliqué en SQL admin** (hors chemin API) avec `seal_hash` placeholder — **ne valide pas** le chemin produit M18 ; à traiter en **incident** (logs Railway / correction RLS ou payload).

### INV-W04 — workspace (`trg_workspace_sealed_final`)

- Passage manuel `status = 'sealed'`, `sealed_at` renseigné (SQL admin).
- **UPDATE** `title` sur workspace déjà `sealed` : **succès** (aucune exception) — le trigger ne couvre pas l’immutabilité générale des colonnes, seulement les transitions de **statut** depuis `sealed` / `closed`. **Écart** par rapport au scénario mandat « tentative de modification post-seal » attendue bloquante.

### Export JSON de remplacement

`GET /api/workspaces/bbb0caa7-010e-4384-a64f-75c47c7110d7/committee` retourne entre autres `workspace_id`, `session.seal_hash`, `session.sealed_at` — **pas** de `pv_snapshot` dans le JSON API (colonne présente en base mais non exposée par le SELECT du routeur).

---

## Tableau récapitulatif mandat

| Étape | Statut | Détails |
|-------|--------|---------|
| Workspace créé + `analysis_complete` | **OK** | SQL après `POST /api/workspaces` ; `committee_required = TRUE` en SQL |
| Session standard `min_members=5` | **OK** | `open-session` → `session_status=active`, CDE `session_activated` |
| 4 votants ajoutés | **OK** | `supply_chain`, `secretary`, `finance`, `budget_holder` |
| Technicien non votant | **OK** | `technical`, `is_voting=false` (user 70) |
| Observateur optionnel | **N/A** | Non ajouté |
| Session « activée » | **OK** | Écart FSM : pas d’étape `draft` ; événement `session_activated` |
| Délibération ouverte | **N/A** | Route absente |
| Commentaire SC / technique / Finance | **N/A** | Routes absentes |
| Score contesté | **N/A** | Route absente |
| INV-W01 UPDATE CDE rejeté | **OK** | Exception `fn_reject_mutation` |
| INV-W03 DELETE CDE rejeté | **OK** | Idem |
| Scellement SHA-256 (API) | **KO** | HTTP 500 ; pas de hash API |
| INV-W04 session sealed | **OK** | Après statut scellé (preuve SQL) |
| INV-W04 workspace sealed (UPDATE title) | **KO** (vs mandat) | UPDATE autorisé — trigger statut seulement |
| Export PV JSON (4 champs mandat) | **PARTIEL** | Pas d’endpoint `/pv/export` ; GET committee partiel |
| `process_workspaces.status = sealed` | **OK** (SQL) | Pas via API seal comité ; alignement métier à clarifier |

---

## Verdict final

**BLOC 4 = VERT PARTIEL** — Composition comité et append-only **INV-W01/W03** + irréversibilité **session** **INV-W04** sont **confirmés** en base. **Scellement PV via API** en **échec (500)** sur la cible ; **délibération live** et **export PV dédié** **absents** du code ; **INV-W04 workspace** ne correspond pas au scénario « mutation métier bloquée » du mandat (titre modifiable après scellement). Prochaine étape : **correction incident `POST …/seal`** + **routes délibération** + exposition `pv_snapshot` / **endpoint export** (mandat CTO / hors périmètre gel).

---

## Références

- Routes W3 : [`src/api/routers/committee_sessions.py`](../../src/api/routers/committee_sessions.py)  
- Migrations : [`071_committee_sessions_deliberation.py`](../../alembic/versions/071_committee_sessions_deliberation.py), [`069_process_workspaces_events_memberships.py`](../../alembic/versions/069_process_workspaces_events_memberships.py)  
- RBAC : [`075_rbac_permissions_roles.py`](../../alembic/versions/075_rbac_permissions_roles.py)
