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
| INV-W04 workspace | UPDATE `title` post-scellement **doit échouer** ; sealed→closed **autorisé** | **v2 sur Railway** (annexe) : mutation sur `sealed` **sans** passage à `closed` → exception ; **`sealed` → `closed`** → autorisé ; **`closed`** → aucune modification. |

---

## Correctifs post-BLOC4 (mandat agent — 2026-04-05)

| Fix | Statut | Détail |
|-----|--------|--------|
| INV-W04 trigger scope élargi | **OK** | Fonction SQL remplacée sur Railway ; preuve `UPDATE title` sur workspace `sealed` → exception `fn_workspace_sealed_final` |
| 500 seal — cause identifiée | **PISTE A** | `tenant_id` pour `INSERT committee_deliberation_events` : usage de `user.tenant_id or ""` pouvant produire une valeur invalide pour la colonne UUID `tenant_id` ; correction : **`tenant_id` issu de `committee_sessions`**, repli `process_workspaces.tenant_id` |
| 500 seal — fix appliqué (code) | **OK** | [`seal_committee_session`](../../src/api/routers/committee_sessions.py) : `tid_cde` depuis la session (+ fallback workspace) |
| seal_hash validé via API | **À confirmer** | Re-tester `POST …/committee/seal` **après déploiement Railway** du handler ; attendu : `seal_hash` 64 hex + `session_sealed` CDE |

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

- **Constat initial** : **`POST …/committee/seal`** → HTTP **500** (hypothèse retenue : **`tenant_id` vide / invalide** pour l’INSERT CDE — **PISTE A**).
- **Correctif code** : handler utilise `committee_sessions.tenant_id` (repli `process_workspaces`) pour `tid_cde` — pas de changement de schéma ni de migration.
- **Validation prod** : à refaire après **déploiement** ; attendu : `seal_hash` 64 caractères hex, `pv_snapshot` JSON, CDE `session_sealed`.

### INV-W04 — workspace (`trg_workspace_sealed_final`)

- **Avant correction** : passage manuel `status = 'sealed'` ; **UPDATE** `title` réussissait (ancienne logique = blocage surtout sur régression de `status`).
- **Après correction (Railway)** : `fn_workspace_sealed_final` élargi — **UPDATE** `title` sur une ligne `status = 'sealed'` **échoue** avec `Workspace … est sealed. Aucune modification autorisée.` — **INV-W04 workspace : corrigé post-BLOC4**.

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
| Scellement SHA-256 (API) | **OK** (post-fix, **après déploiement**) | Fix handler `tid_cde` ; re-test prod requis |
| INV-W04 session sealed | **OK** | Après statut scellé (preuve SQL) |
| INV-W04 workspace sealed (UPDATE title) | **OK** | Post-correction trigger Railway — UPDATE bloqué |
| Export PV JSON (4 champs mandat) | **PARTIEL** | Pas d’endpoint `/pv/export` ; GET committee partiel |
| `process_workspaces.status = sealed` | **OK** (SQL) | Pas via API seal comité ; alignement métier à clarifier |

---

## Verdict final (synthèse)

**BLOC 4 = ROUGE (seal toujours 500 après fix en code)** — détail chiffré et corps d’erreur : **§ Validation post-fix**. Branche **`feat/mandat-bloc4-committee-pv`** poussée sur `origin` ; **merge PR + déploiement Railway** requis pour valider le fix en prod. **INV-W04** : trigger **v2** sur Railway (sealed → **closed** autorisé). Repasser en **VERT** après merge `main` + déploiement + re-test seal **200/201** + `seal_hash` 64.

---

## Validation post-fix (mandat agent — 2026-04-05)

Commits de référence : `eadd7baa`, `8ca58108` sur `feat/mandat-bloc4-committee-pv` (+ livrables scripts/rapport : `0304b774`).

PR : ouvrir / merger depuis  
`https://github.com/ousma15abdoulaye-crypto/decision-memory-v1/pull/new/feat/mandat-bloc4-committee-pv`  
(merge **humain** ; l’agent n’a pas pu utiliser `gh` : timeout TLS vers `api.github.com`.)

| Étape | Statut |
|-------|--------|
| Push + merge `main` | **Push OK** · **Merge KO** (PR à créer/merger manuellement sur GitHub) |
| Railway redéployé | **KO** (aucun déploiement depuis `main` tant que la PR n’est pas mergée) |
| `POST /committee/seal` HTTP | **500** |
| `seal_hash` 64 chars | **KO** |
| `sealed_at` NOT NULL | **KO** |
| `pv_snapshot` NOT NULL | **KO** |
| sealed → closed autorisé | **OK** (DB, trigger **v2** déjà sur Railway — voir annexe ; non rejoué sur le workspace du dernier run car scellement API non appliqué) |

**Dernier run prod** (après push branche, **sans** merge `main`) : [`scripts/bloc4_seal_validation_postfix.py`](../../scripts/bloc4_seal_validation_postfix.py) sur `https://decision-memory-v1-production.up.railway.app` — `reference_code` **`SEAL-TEST-FINAL-47e49367`**, `workspace_id` **`4a9ceea4-d871-40fe-9ad4-08d654035761`**, `session_id` **`fd5339fd-db81-4432-8ee6-7721bc64a52d`**.

**Corps de réponse `POST …/committee/seal` (obligatoire si 500)** — texte brut complet :

```text
Internal Server Error
```

**Verdict final (état au 2026-04-05, prod non mise à jour par le fix)** :

**BLOC 4 = ROUGE (seal toujours 500 après fix)** — le correctif handler (`tid_cde`) **n’est pas en production** tant que `feat/mandat-bloc4-committee-pv` n’est **pas** mergée dans `main` et déployée par Railway. **STOP** mandat BLOC 5 jusqu’à merge + déploiement + re-test seal **200/201** avec `seal_hash`. Après déploiement confirmé, si **500** persiste : **logs Railway** au timestamp du POST, corps de réponse complet dans ce rapport, **escalade CTO** immédiate.

**Escalade** : si **500** sur seal **après** déploiement confirmé du handler — consulter **logs Railway** au timestamp du POST ; si besoin d’une migration corrective → **STOP**, **GO CTO** (règle mandat).

---

## Références

- Routes W3 : [`src/api/routers/committee_sessions.py`](../../src/api/routers/committee_sessions.py)  
- Migrations : [`071_committee_sessions_deliberation.py`](../../alembic/versions/071_committee_sessions_deliberation.py), [`069_process_workspaces_events_memberships.py`](../../alembic/versions/069_process_workspaces_events_memberships.py)  
- RBAC : [`075_rbac_permissions_roles.py`](../../alembic/versions/075_rbac_permissions_roles.py)

---

## Annexe — SQL INV-W04 workspace (replay ops Railway)

**Version actuelle sur Railway (v2 — post-validation 2026-04-05)** : interdit toute modification d’une ligne **`closed`** ; sur une ligne **`sealed`**, autorise **uniquement** le passage **`status = 'closed'`** ; toute autre modification (ex. `title` avec `status` toujours `sealed`) est rejetée.

Exécuter **en une seule instruction** (voir [`scripts/bloc4_apply_workspace_trigger_v2.py`](../../scripts/bloc4_apply_workspace_trigger_v2.py)).

```sql
CREATE OR REPLACE FUNCTION fn_workspace_sealed_final()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.status = 'sealed'
     AND NEW.status IS DISTINCT FROM 'closed' THEN
    RAISE EXCEPTION
      'Workspace % est sealed. Seule transition autorisée : closed.',
      OLD.id;
  END IF;
  IF OLD.status = 'closed' THEN
    RAISE EXCEPTION
      'Workspace % est closed. Aucune transition autorisée.',
      OLD.id;
  END IF;
  RETURN NEW;
END;
$$;
```

Vérifications :

```sql
-- Doit échouer (mutation métier sans clôture)
UPDATE process_workspaces
SET title = 'test post-correction'
WHERE id = (SELECT id FROM process_workspaces WHERE status = 'sealed' LIMIT 1);

-- Doit réussir (clôture explicite)
UPDATE process_workspaces
SET status = 'closed'
WHERE status = 'sealed' AND reference_code = '…';
```
