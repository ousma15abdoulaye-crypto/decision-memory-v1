# V0 — interrogation vérité interne DMS (DB)

Référence : DMS-MANDAT-V0-INTERROGATION-VERITE-INTERNE-V1  
Date collecte : 2026-04-24  
Workspace cible : `f1a6edfb-ac50-4301-a1a9-7a80053c632a` (CASE-28b05d85)  
Agent : exécution depuis poste Windows (réseau SCI).

---

## Section 1 — Structure DMS

| ID | Commande / requête | Résultat |
|----|-------------------|----------|
| Q1 | `python -m alembic current` (cwd repo) | `sqlalchemy.exc.OperationalError: (psycopg.OperationalError) [Errno 11001] getaddrinfo failed` (connexion DB locale impossible) |
| Q2 | `python -m alembic history -r base:head` | sortie non vide, **140** lignes texte |
| Q2b | `Get-ChildItem alembic\versions -Filter *.py -File \| Measure-Object` | **133** fichiers `.py` sous `alembic/versions/` |
| Q3 | `SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name` | non exécuté |
| Q4 | `\d+` équivalent : `SELECT column_name, data_type FROM information_schema.columns …` pour les 10 tables listées | non exécuté |

**Erreur transport Railway (toutes les voies DB distantes)**  
`railway variables` et `railway ssh --service arq-worker -- …` et pipe `type …\dms_truth_runner.py | railway ssh …` :  
`Failed to fetch: error sending request for url (https://backboard.railway.com/graphql/v2)` — causes observées : `os error 10054` et `operation timed out` (8 tentatives ssh espacées de 8 s).

---

## Section 2 — Workspace pilote `f1a6edfb-ac50-4301-a1a9-7a80053c632a`

| ID | Requête SQL (extrait) | Résultat |
|----|----------------------|----------|
| Q5 | `SELECT id, tenant_id, code, name, status, host_framework, procedure_resolution_status, estimated_value, created_at, updated_at FROM process_workspaces WHERE id = 'f1a6edfb-ac50-4301-a1a9-7a80053c632a'` | non exécuté |
| Q6 | agrégats `supplier_bundles` par `bundle_status` pour ce workspace | non exécuté |
| Q7 | détail `supplier_bundles` ordre `bundle_index` | non exécuté |
| Q8 | détail `bundle_documents` (état `raw_text` = NULL / EMPTY / longueur) | non exécuté |
| Q9 | `source_packages` pour workspace | non exécuté |
| Q10 | `source_package_documents` pour workspace | non exécuté |

`tenant_code = sci_mali` : non observé en base (requête non exécutée).

---

## Section 3 — DAO criteria et scoring

| ID | Requête | Résultat |
|----|---------|----------|
| Q11 | totaux famille TECHNICAL / COMMERCIAL / SUSTAINABILITY | non exécuté |
| Q12 | `SUM(weight_within_family)` par `family` | non exécuté |
| Q13 | `DISTINCT criterion_mode, scoring_mode` | non exécuté |

---

## Section 4 — Criterion assessments (Bridge P5)

| ID | Requête | Résultat |
|----|---------|----------|
| Q14 | totaux + `COUNT(DISTINCT bundle_id)` + `COUNT(DISTINCT dao_criterion_id)` | non exécuté |
| Q15 | `SELECT pg_typeof(dao_criterion_id) … LIMIT 1` | non exécuté |

---

## Section 5 — Agrégats DMS globaux

| ID | Requête | Résultat |
|----|---------|----------|
| Q16 | `SELECT COUNT(*) FROM process_workspaces` | non exécuté |
| Q17 | `ocr_engine` distribution globale `bundle_documents` | non exécuté |
| Q18 | `bundle_status` distribution globale `supplier_bundles` | non exécuté |
| Q19 | `assembled_by` distribution globale `supplier_bundles` | non exécuté |
| Q20 | totaux `bundle_documents` (texte / struct / classifié) | non exécuté |

---

## STOP — remontée CTO principal (§8.3)

Connexion DB production **non obtenue** sur la fenêtre d’exécution : CLI Railway → GraphQL `backboard.railway.com` en échec répété ; `alembic current` local → `getaddrinfo failed`. Les requêtes SQL Q3–Q20 n’ont **pas** été exécutées. `tenant_code` workspace pilote non vérifié. Aucune ligne résultat Q5–Q20 à opposer.

---

## Annexe — statut des 20 interrogations §3

| Q | Statut | Sortie |
|---|--------|--------|
| Q1 | exécuté (CLI) | erreur `getaddrinfo failed` (voir Section 1) |
| Q2 | exécuté (CLI) | 140 lignes ; 133 fichiers `alembic/versions/*.py` |
| Q3 | non exécuté | pas de connexion DB |
| Q4 | non exécuté | pas de connexion DB |
| Q5 | non exécuté | pas de connexion DB |
| Q6 | non exécuté | pas de connexion DB |
| Q7 | non exécuté | pas de connexion DB |
| Q8 | non exécuté | pas de connexion DB |
| Q9 | non exécuté | pas de connexion DB |
| Q10 | non exécuté | pas de connexion DB |
| Q11 | non exécuté | pas de connexion DB |
| Q12 | non exécuté | pas de connexion DB |
| Q13 | non exécuté | pas de connexion DB |
| Q14 | non exécuté | pas de connexion DB |
| Q15 | non exécuté | pas de connexion DB |
| Q16 | non exécuté | pas de connexion DB |
| Q17 | non exécuté | pas de connexion DB |
| Q18 | non exécuté | pas de connexion DB |
| Q19 | non exécuté | pas de connexion DB |
| Q20 | non exécuté | pas de connexion DB |
