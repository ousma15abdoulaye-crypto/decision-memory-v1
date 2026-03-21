# Revue — PR Copilot « multi-tenant / org_id / cases auth »

Date : 2026-03-21  
Contexte : cette branche (`feat/arch-routing-01` et travaux associés) a déjà introduit **`tenant_id`** (JWT, `user_tenants`, `cases.tenant_id`, RLS migration `051`, critères `org_id` = tenant dossier).

## Synthèse

| Élément PR Copilot | Compatibilité avec le dépôt actuel | Recommandation |
|--------------------|-------------------------------------|----------------|
| **`org_id` dans JWT + `UserClaims.org_id`** | **Doublon sémantique** avec `tenant_id` déjà présent (`jwt_handler`, `dependencies`, login). | **Ne pas merger tel quel.** Garder un seul claim : `tenant_id`. Documenter que le paramètre API `org_id` (critères) = **tenant métier du dossier**, aligné sur `cases.tenant_id`. |
| **`tenant_guard.py` (TENANT_SCOPED / GLOBAL_CORE)** | Utile comme **catalogue** et garde-fous futurs ; à réécrire avec vocabulaire **`tenant_id`** (pas `org_id` côté JWT). | **Cherry-pick conceptuel** après adaptation des noms et de la liste des tables (voir migration `051`). |
| **`list_cases` / `get_case` auth + filtre** | Auth **déjà** sur `create_case`, `list_cases`, `get_case`. Filtre actuel : **admin = tout**, sinon **`WHERE tenant_id = :tid`**. La PR Copilot parle de filtre **`owner_id`** : **modèle différent**. | **Ne pas remplacer** le filtre tenant par owner-only sans décision produit. |
| **Cohérence liste ↔ détail** | Aujourd’hui : liste par **tenant**, `get_case` utilise **`require_case_access`** (403 si pas owner, sauf admin). Un utilisateur peut **voir** un dossier d’un collègue dans la liste mais être **refusé** sur le détail — incohérence UX / sécurité à trancher. | **Décision requise** : (A) restreindre la liste à `owner_id` **ou** (B) assouplir `require_case_access` pour les rôles / co-tenant (ex. même `tenant_id`). |
| **`test_inv_10_tenant_isolation.py` (scan SQL)** | Intention bonne ; implémentation dépend des conventions (colonnes `tenant_id`, RLS, chemins `src/`). | **Adapter** plutôt que copier : voir `tests/invariants/test_inv_10_tenant_isolation.py` (version allégée alignée `tenant_id`). |
| **`AUDIT_MULTI_TENANT_ISOLATION.md`** | Documentation utile ; fusionner avec cette note et l’état réel des mandats (RLS déjà amorcé en `051`). | **Conserver** comme annexe ou fusion. |

## Ce qui est déjà couvert ici (pas à réintroduire sous un autre nom)

- Claim JWT **`tenant_id`** (`_build_claims`, `create_access_token`, `create_refresh_token`).
- **`UserClaims.tenant_id`** + résolution fallback `user_tenants`.
- **`set_db_tenant_id` / `set_rls_is_admin`** par requête authentifiée.
- **`cases.tenant_id`** à la création ; liste filtrée par tenant (non-admin).
- Critères : **`require_case_tenant_org`** — `org_id` requête/body doit égaler **`cases.tenant_id`**.

## Merge suggéré de la PR GitHub Copilot

1. **Fermer / modifier** les changements `org_id` dans JWT → mapper en **`tenant_id`** si une seule PR doit passer.
2. **Ne pas** appliquer « liste des cases par `owner_id` seul » sans aligner **`require_case_access`** et les besoins métier multi-utilisateur par tenant.
3. Importer **tests d’invariants** et **audit doc** après relecture ; éviter les doublons avec `051` / critères.

## Branche de travail « alignement »

Les commits sur la branche dédiée peuvent contenir : ce document, les invariants `test_inv_10_*`, et toute adaptation de `tenant_guard` **nommée tenant** si le produit valide la liste des tables.
