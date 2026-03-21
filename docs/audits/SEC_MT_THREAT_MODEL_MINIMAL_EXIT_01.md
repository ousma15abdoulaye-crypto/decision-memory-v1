# SEC-MT-00 — Modèle de menace minimal (EXIT-PLAN-ALIGN-01)

**Référence :** EXIT-PLAN-ALIGN-01 · Mandat SEC-MT  
**Date :** 2026-03-21  
**Révision :** 2026-03-21 — surface dual-app + outil d’audit référencé  
**Statut :** SOCLE — à itérer par mandats SEC-MT-01/02/03 ; **ne pas** mélanger avec le rail annotation (hors périmètre).

---

## 0. Préambule opposable

Ce document **ne** prétend pas que le système est « multi-tenant complet ». Il liste **surfaces réelles** et **barrières vérifiables dans le code**. Toute affirmation forte (RLS, isolation totale) exige un mandat **SEC-MT-01** avec preuves SQL + tests.

---

## 1. Surfaces d’attaque (réelles dans le repo)

| Surface | Description | Ancrage |
|---------|-------------|---------|
| **API HTTP — App_Racine** | `main:app` — surface **prod par défaut** (Railway) | [`main.py`](../../main.py), [`start.sh`](../../start.sh) |
| **API HTTP — App_API_Modulaire** | `src.api.main:app` — routes additionnelles (criteria, pipeline_a, mercuriale, etc.) si montée | [`src/api/main.py`](../../src/api/main.py) |
| **Auth JWT + RBAC** | Émission / validation token, rôles | [`src/auth_router.py`](../../src/auth_router.py), [`src/couche_a/auth/`](../../src/couche_a/auth/) |
| **IDOR dossier / document** | Accès par `case_id` / `document_id` | [`src/couche_a/auth/case_access.py`](../../src/couche_a/auth/case_access.py) ; routes dans [`src/api/cases.py`](../../src/api/cases.py), documents, analysis |
| **Tenant applicatif** | `tenant_id` sur création case et claims | [`src/api/cases.py`](../../src/api/cases.py) (ex. exigence `tenant_id`) |
| **Routers optionnels absents** | Capacité non montée sans échec démarrage | `src/api/main.py` (optionnels) |
| **PostgreSQL** | Données dossiers, schémas public / `couche_b` | [`alembic/`](../../alembic/) |
| **Rate limit / headers** | Dépend Redis + import (app modulaire) | [`src/couche_a/auth/middleware.py`](../../src/couche_a/auth/middleware.py) |

**Multi-tenant DB (RLS) :** **UNKNOWN** dans ce document — pas d’attestation sans revue migrations + politiques.

---

## 2. Acteurs

- **Utilisateur authentifié** (buyer, evaluator, committee, admin, viewer).
- **Admin** — bypass `owner` dans `require_case_access` (voir implémentation).
- **Attaquant** — JWT volé, énumération d’UUID, accès direct API, confusion entre les deux apps FastAPI si les deux sont exposées.

---

## 3. Scénarios d’abus (priorisés)

1. **IDOR :** route prenant `case_id` / `document_id` **sans** `require_case_access` (ou équivalent) → lecture / écriture cross-utilisateur.
2. **Surface double :** `App_API_Modulaire` exposée en prod **en parallèle** de `App_Racine` sans inventaire des routes → routes « oubliées » non durcies.
3. **Dépendance à un router optionnel :** garantie métier supposée alors que l’import a échoué (app modulaire).
4. **Rate limit désactivé :** middleware non chargé → abuse brute force / scraping.
5. **Cross-tenant SQL :** requêtes sans filtre organisationnel si le modèle introduit plusieurs tenants au niveau ligne (à valider par schéma).

---

## 4. Barrières déjà présentes (vérifiables)

- **Contrôle applicatif case/document :** `require_case_access`, `require_document_case_access` — [`case_access.py`](../../src/couche_a/auth/case_access.py).
- **JWT + dépendances FastAPI** sur les routes qui les déclarent.
- **Gate CI partiel :** [`scripts/audit_fastapi_auth_coverage.py`](../../scripts/audit_fastapi_auth_coverage.py) — heuristique « arbre de dépendances contient `get_current_user` » pour les routes sous un préfixe donné (voir `.github/workflows/ci-main.yml`).

---

## 5. Lacunes explicites (non promesses)

- **Inventaire fermé IDOR** : **non livré** ici — mandat suivant : tableau routes × présence `get_current_user` / `require_case_access`.
- **RLS PostgreSQL** comme barrière principale : **non attesté** — SEC-MT-01.
- **Une seule app en prod** : si les deux apps sont déployées, **documenter** ou **retirer** l’exposition — sinon risque structurel.

---

## 6. Règles anti-dérive

- Ne pas étiqueter « sécurisé multi-tenant » sans preuve DB + tests.
- Ne pas mélanger ce chantier avec Label Studio / export M12 / `annotation-backend`.
- Toute analyse de routes doit commencer par **`main:app`** (vérité Railway) puis **`src.api.main:app`** si applicable.

---

## 7. Prochaine étape recommandée (mandat SEC-MT-01)

1. Générer deux inventaires : `audit_fastapi_auth_coverage.py --app main:app` et `--app src.api.main:app` (sans `--fail-prefix` d’abord).
2. Produire tableau **fermé** : routes sensibles (`/api/cases`, `/api/documents`, `/committee`, `/price-check`, etc.) × statut auth / case_access.
3. Corriger les **trous** par PRs **ciblées** ; étendre le gate CI avec préfixes additionnels **après** stabilisation.
