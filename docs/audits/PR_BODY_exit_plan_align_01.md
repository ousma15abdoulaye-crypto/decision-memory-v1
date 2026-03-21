# PR — `feat/exit-plan-align-01-enterprise-bundle`

> À coller dans la description GitHub de la PR (section principale / body).

## Résumé

Branche **exit-plan / alignement enterprise** : durcissement multi-tenant (`tenant_id`, RLS, critères, extractions), CI, documentation d’audit, et **intégration des correctifs issus de la revue CI de la PR Copilot** (sans dupliquer `org_id` dans le JWT — le claim unique reste **`tenant_id`**).

## Dernier commit (ce push)

**`test+docs: inv10 scan SQL RLS 051, docstrings tenant, reprise revue Copilot CI`**

### Contenu

- **`tests/invariants/inv10_tenant_sql_scan.py`** (nouveau)  
  - Scan statique AST des `SELECT` touchant les tables RLS de la migration **051** : `cases`, `criteria`, `supplier_scores`, `pipeline_runs`.  
  - Motifs **`re.IGNORECASE`** (corrige le bug signalé en revue : SQL en majuscules vs regex sensible à la casse).  
  - Allowlist explicite pour la liste **admin** des cases.  
  - Table **`vendors`** (hors RLS 051) : **avertissements** uniquement pour les lectures globales connues (`list_vendors` `is_active`, recherche `similarity` dans `couche_b/resolvers`).  
  - Prise en charge des **f-strings** SQL (`JoinedStr`) pour ne pas rater `list_vendors`.  
  - Heuristiques de périmètre : `tenant_id`, `case_id`, `org_id`, `owner_id`, `user_id`, `WHERE … id =`, `vendor_id`, `fingerprint`.

- **`tests/invariants/test_inv_10_tenant_isolation.py`**  
  - Imports **Ruff / isort** conformes (I001).  
  - Docstrings alignées sur le comportement réel (pas de promesses sur des checks INSERT absents).  
  - Test liste cases : vérifie **tenant + owner** pour le non-admin.

- **`src/api/cases.py`**  
  - Docstrings module + `list_cases` : **admin = tout** ; sinon **même `tenant_id` que le JWT et `owner_id` = utilisateur** (cohérent avec `require_case_access`).

- **`src/auth_router.py`**  
  - Commentaire : **`tenant_id` dans le JWT** = sémantique d’isolation (équivalent métier « org ») ; pas besoin d’un second claim `org_id`.

- **`docs/audits/COPILOT_PR_MULTI_TENANT_REVIEW.md`**  
  - Tableau et section **« Intégration revue CI / Copilot »** mis à jour (liste/owner, scan SQL, pas d’`org_id` token).

### Vérifications locales

- `ruff check` sur les fichiers inv10 : OK  
- `pytest tests/invariants/test_inv_10_tenant_isolation.py` : OK (2 `UserWarning` attendus sur vendors)

---

## Contexte plus large (branche)

- Multi-tenant : **`tenant_id`** JWT, `user_tenants`, `cases.tenant_id`, migration **051** + RLS, critères **`org_id` = tenant du dossier**, auth extractions, tests API, audit CI `--fail-prefix /api/extractions` selon les commits déjà sur la branche.

## Merge / suivi

- PR **Copilot** (`org_id` JWT, `require_org_id`, etc.) : **ne pas merger telle quelle** ; cette PR matérialise l’alignement documenté + invariants.  
- Optionnel : copier **`AUDIT_MULTI_TENANT_ISOLATION.md`** depuis la PR Copilot en annexe sous `docs/audits/` si tu veux le rapport long dans le repo.
