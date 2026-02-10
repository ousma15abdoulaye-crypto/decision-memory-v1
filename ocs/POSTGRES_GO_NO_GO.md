# PostgreSQL GO/NO-GO — DMS Couche A (Validation Cloud)

Auteur: CTO/Tech Lead (terrain)
Objectif: éviter le mélange et sécuriser l’industrialisation sans ralentir la cadence.

## TL;DR
✅ On avance.
❌ On ne merge pas en main tant qu’un run PostgreSQL cloud n’a pas été exécuté avec preuves.

---

## Constat
L’agent a livré:
- Correction placeholder layer (:0 → :p0): ✅ fait
- ONLINE-ONLY (Postgres only): ✅ fait
- Tests existants + infra validation: ✅ fait
- Docs GO/NO-GO: ✅ fait

Mais:
- PostgreSQL cloud runtime (dialecte + transactions + contraintes + encodage): ❌ pas fait

Les tests unitaires valident la transformation, pas l’exécution sur PostgreSQL réel.

---

## Étape 1 — Push complet + PR (sans merge)
Objectif: figer le snapshot et déclencher review sans risquer main.

To-do:
1. Résoudre le “push incomplet / réseau” → pousser tous les commits.
2. Créer une Pull Request vers `main`.
3. Ajouter note/label: `BLOCKED: Postgres cloud validation not done`.

---

## Étape 2 — Validation PostgreSQL cloud AVANT merge (Gate)
Objectif: prouver que le moteur tourne réellement sur PostgreSQL (Railway/Render/Supabase).

### Gates (critères non négociables)
- `scripts/smoke_postgres.py` passe sur PostgreSQL cloud
- 3 endpoints critiques OK:
  - `POST /api/cases`
  - `GET /api/cases`
  - `POST /api/decide/{case_id}`
- Vérification persistance:
  - create → list → decide → list (status bien changé)

### Preuves obligatoires dans la PR
Créer/mettre à jour `docs/POSTGRES_CLOUD_RUN.md` contenant:
- URL du service (railway/render)
- logs complets du smoke test (stdout brut)
- outputs HTTP (status + extrait JSON) des 3 endpoints ci-dessus
- EXIT_CODE final

---

## Étape 3 — Merge uniquement si Gate OK
✅ Si Gate OK:
- Merge PR vers `main`
- Tag version (ex: `v0.x.y`)
- Release note courte (changelog minimal)

❌ Si Gate KO:
- Patch minimal uniquement (binding, types, SQL, transaction)
- Re-run cloud
- Gate doit passer avant merge

---

## Décision CTO (non négociable)
- PR: OUI
- Merge: NON tant que POSTGRES_CLOUD_RUN.md n’existe pas avec run vert
- Ensuite seulement: accélération Couche B0 / Market Survey (online-first)
