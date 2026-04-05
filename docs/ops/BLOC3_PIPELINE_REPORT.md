# Rapport — BLOC 3 : seed vendors + Pass‑1 + M12 + M14 + smokes Railway

**Date** : 2026-04-05  
**Prérequis** : BLOC 1 VERT (077), BLOC 2 VERT partiel (routers câblés).  
**Contraintes** : aucune modification de schéma DB ; pas de données de test permanentes non identifiées comme smoke (utilisateur `smoke_bloc3_*` + `reference_code` unique `SMOKE-BLOC3-<suffixe>`).

> **Addendum (post-merge correctif 500, ex. PR #324)** : en prod, `POST /api/workspaces` et `GET /api/market/overview` passent en smoke ; `GET …/committee` peut répondre **403** (RBAC) — attendu pour le script **A+B**. Le tableau ci-dessous documente surtout la **session d’audit initiale** (avant correctif), pour trace.

---

## Résumé exécutif

| Étape | Statut | Détails |
|-------|--------|---------|
| Vendors source trouvée | **OK** | [`scripts/etl_vendors_wave2.py`](../../scripts/etl_vendors_wave2.py) + fichier local `data/imports/m4/` (voir [`data/imports/m4/README.md`](../../data/imports/m4/README.md) ; xlsx hors Git). Synthèse terrain : doc interne *vendors sync* si présente dans l’équipe. |
| Vendors Railway count | **1** | `SELECT COUNT(*) FROM vendors` via [`scripts/run_pg_sql.py`](../../scripts/run_pg_sql.py) sur la cible Railway documentée dans l’environnement agent — **1** ligne (référentiel pilote non chargé ; cohérent avec probe historique `mercurials_proxy` seul). **Import Wave 2 non appliqué** dans cette session (pas de `INSERT` exécuté vers Railway). |
| Correction ETL dry-run | **OK** | Le script référençait encore la table **`vendor_identities`** dans les SQL de dry-run / post-import ; aligné sur **`vendors`** (post-m5). Sans cela, dry-run / validation post-import échouent sur le schéma actuel. |
| Dry-run ETL complet (fingerprints DB) | **GAP** | Avec la chaîne `.env` + `.env.local` + `.env.railway.local` telle qu’en session agent, `DATABASE_URL` peut rester orienté **localhost** (priorité `.env.local`) : `get_connection()` pour l’ETL cible alors **127.0.0.1:5432** en échec auth. **Action CTO** : lancer le dry-run avec `DATABASE_URL` pointant explicitement vers Railway (ou n’utiliser que `python scripts/with_railway_env.py` sans override local), puis relancer `python scripts/etl_vendors_wave2.py --dry-run` et `COUNT(*)` attendu après apply. |
| Smoke POST `/auth/token` | **OK** | Endpoint réel : **`POST /auth/token`** (pas `/api/auth/token`), body **`application/x-www-form-urlencoded`** (`username`, `password`). |
| Smoke POST `/api/workspaces` | **KO** | HTTP **500** sur `https://decision-memory-v1-production.up.railway.app` après création utilisateur smoke et JWT valide. |
| Smoke GET `/api/market/overview` | **KO** | HTTP **500** (même base URL / même token). |
| Smoke GET `/api/workspaces/{id}/committee` | **SKIP** | Pas de `workspace_id` retourné (échec création workspace). |
| Pass‑1 workspace-aware (code) | **OK** | [`run_pass_minus_1`](../../src/workers/arq_tasks.py) → graphe [`graph.py`](../../src/assembler/graph.py) → [`bundle_writer.py`](../../src/assembler/bundle_writer.py) sur `supplier_bundles` / `bundle_documents` avec `workspace_id` / `tenant_id`. |
| Pass‑1 test réel (ZIP → DB) | **GAP** | Non rejoué : dépend d’un workspace valide + worker ARQ + Redis + exécution [`workspaces.py` (upload-zip)](../../src/api/routers/workspaces.py) ; bloqué ici par les **500** sur les routes W1. |
| M12 workspace-aware | **OK** (code) | `classify_node` + persistance `m12_doc_kind` / `m12_confidence` dans [`bundle_writer.py`](../../src/assembler/bundle_writer.py) vers **`bundle_documents`**. |
| M14 workspace-aware (lecture API) | **OK** (code) | [`workspaces.py` (GET …/evaluation)](../../src/api/routers/workspaces.py) lit `evaluation_documents` par **`workspace_id`**, filtre INV‑W06 sur `scores_matrix`. |
| M14 persistance moteur (`save_evaluation`) | **GAP** | [`m14_evaluation_repository.py`](../../src/procurement/m14_evaluation_repository.py) insère encore avec **`case_id`** et colonnes héritées du modèle pré‑074 ; la migration [`074_drop_case_id_set_workspace_not_null.py`](../../alembic/versions/074_drop_case_id_set_workspace_not_null.py) supprime **`case_id`** sur `evaluation_documents`. Risque : écriture M14 via ce repository **incompatible** avec le schéma 077 tant que le code n’est pas aligné (hors périmètre correction BLOC 3). |
| `workspace_events` | **PARTIEL** | À la création de workspace, [`workspaces.py`](../../src/api/routers/workspaces.py) émet **`WORKSPACE_CREATED`**. Aucune preuve supplémentaire en session (création workspace API en échec 500). |

### Outil ajouté

- [`scripts/bloc3_smoke_railway.py`](../../scripts/bloc3_smoke_railway.py) — enchaîne register → token → workspaces → market → committee (utilisateur smoke jetable).

---

## Verdict

**BLOC 3 = VERT PARTIEL** : à l’issue de l’audit documenté dans le tableau (session initiale), le pilote complet restait conditionné à la levée des **500** W1/W2, à l’alignement ETL/DB/M14, etc. **Post-correctif 500** (voir addendum en tête de document et [`BLOC3_500_DIAGNOSIS.md`](BLOC3_500_DIAGNOSIS.md)), les smokes critiques W1/W2 ne sont plus bloqués par des erreurs serveur sur ces routes en prod ; un **VERT** complet reste toutefois limité par les autres lignes du tableau (vendors, Pass‑1 ZIP réel, M14 `case_id`, etc.).

**À l’état du tableau (snapshot session)** : compteur `vendors` à **1** sans import Wave 2 ; **HTTP 500** sur W1/W2 en smoke réel ; pas de preuve Pass‑1 / ZIP bout‑en‑bout ; **GAP** M14 (`case_id` vs schéma 074+).

**BLOC 3 ≠ ROUGE** : auth fonctionnel sur l’URL testée, chaîne Pass‑1/M12 côté code alignée workspace ; les blocages observés en session sont **exploitables** (correctifs applicatifs / déploiement) sans changement de schéma dans ce mandat.

---

## Prochaines actions recommandées (hors mandat)

1. **500 W1/W2** : corrigés (voir [`BLOC3_500_DIAGNOSIS.md`](BLOC3_500_DIAGNOSIS.md)). **État actuel du smoke** : [`bloc3_smoke_railway.py`](../../scripts/bloc3_smoke_railway.py) échoue si W1/W2 ne renvoient pas les succès attendus (**201/200**), *quel que soit* le code d’erreur (**4xx** ou **5xx**) — le script ne filtre pas « 500 seul ». **403** sur `/committee` = RBAC attendu (user smoke), pas une erreur plateforme.
2. Importer les vendors : `python scripts/etl_vendors_wave2.py --dry-run` puis sans `--dry-run` avec **`DATABASE_URL`** Railway explicite ; re‑vérifier `SELECT COUNT(*) FROM vendors`.
3. Aligner **`M14EvaluationRepository`** sur `workspace_id` si le produit doit persister M14 sur le schéma 077 (mandat / ADR dédié + GO CTO si toucher des fichiers gelés).
4. Pass‑1 (`upload-zip`) une fois besoin métier.
5. **Point C (architecture cognitive)** : droit créateur → lecture committee / membership explicite — à traiter comme chantier central avec l’implémentation **arch. cognitive** ; le smoke ne doit pas confondre **403** (autorisation) et **500** (serveur).

