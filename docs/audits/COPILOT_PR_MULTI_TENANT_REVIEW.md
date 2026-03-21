# Revue — PR Copilot « multi-tenant / org_id / cases auth »

Date : 2026-03-21  
Contexte : cette branche (`feat/arch-routing-01` et travaux associés) a déjà introduit **`tenant_id`** (JWT, `user_tenants`, `cases.tenant_id`, RLS migration `051`, critères `org_id` = tenant dossier).

## Synthèse

| Élément PR Copilot | Compatibilité avec le dépôt actuel | Recommandation |
|--------------------|-------------------------------------|----------------|
| **`org_id` dans JWT + `UserClaims.org_id`** | **Doublon sémantique** avec `tenant_id` déjà présent (`jwt_handler`, `dependencies`, login). | **Ne pas merger tel quel.** Garder un seul claim : `tenant_id`. Documenter que le paramètre API `org_id` (critères) = **tenant métier du dossier**, aligné sur `cases.tenant_id`. |
| **`tenant_guard.py` (TENANT_SCOPED / GLOBAL_CORE)** | Utile comme **catalogue** et garde-fous futurs ; à réécrire avec vocabulaire **`tenant_id`** (pas `org_id` côté JWT). | **Cherry-pick conceptuel** après adaptation des noms et de la liste des tables (voir migration `051`). |
| **`list_cases` / `get_case` auth + filtre** | Auth sur create/list/get. Non-admin : **`tenant_id` + `owner_id`** (cohérent avec `require_case_access` sur le détail). | Aligné : pas owner-only sans tenant ; pas liste tenant-only sans owner. |
| **Cohérence liste ↔ détail** | Liste et détail restreints au **même owner** dans le tenant (sauf admin). | Fermé côté implémentation actuelle. |
| **`test_inv_10` + scan SQL (reprise revue CI)** | Regex **insensible à la casse** ; helpers dans **`inv10_tenant_sql_scan.py`** ; AST inclut **f-strings** ; docstrings alignées ; pas de **`org_id` JWT** ( **`tenant_id`** déjà émis dans `auth_router`). | Voir `tests/invariants/inv10_tenant_sql_scan.py`. |
| **`AUDIT_MULTI_TENANT_ISOLATION.md`** | Documentation utile ; fusionner avec cette note et l’état réel des mandats (RLS déjà amorcé en `051`). | **Conserver** comme annexe ou fusion. |

## Ce qui est déjà couvert ici (pas à réintroduire sous un autre nom)

- Claim JWT **`tenant_id`** (`_build_claims`, `create_access_token`, `create_refresh_token`).
- **`UserClaims.tenant_id`** + résolution fallback `user_tenants`.
- **`set_db_tenant_id` / `set_rls_is_admin`** par requête authentifiée.
- **`cases.tenant_id`** à la création ; liste non-admin filtrée par **tenant + owner**.
- Critères : **`require_case_tenant_org`** — `org_id` requête/body doit égaler **`cases.tenant_id`**.

## Merge suggéré de la PR GitHub Copilot

1. **Fermer / modifier** les changements `org_id` dans JWT → mapper en **`tenant_id`** si une seule PR doit passer.
2. **Ne pas** appliquer « liste des cases par `owner_id` seul » **sans** `tenant_id` : le dépôt garde **les deux** pour le non-admin.
3. **Tests d’invariants** : scan SQL intégré (reprise commentaires revue Copilot : bug regex, PERF helper, docstrings).

## Intégration revue CI / Copilot (2026-03-21)

- **Ruff I001** : imports triés dans `test_inv_10_tenant_isolation.py`.
- **Scan SQL** : tables RLS = migration **051** ; matching **`re.IGNORECASE`** ; allowlist admin `cases` ; vendors = **warnings** seulement.
- **Docstrings** `cases.py` / module : alignées sur **tenant + owner** et sur **tenant_id JWT** (pas `org_id` token).

## Branche de travail « alignement »

Les commits sur la branche dédiée peuvent contenir : ce document, les invariants `test_inv_10_*`, et toute adaptation de `tenant_guard` **nommée tenant** si le produit valide la liste des tables.
