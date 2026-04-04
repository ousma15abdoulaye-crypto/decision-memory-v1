# DMS V4.2.0 — STOP SIGNALS

**Référence** : DMS-V4.2.0-ADDENDUM-WORKSPACE §VII
**Date freeze** : 2026-04-04
**Statut** : FREEZE DÉFINITIF après hash

---

## 12 signaux d'arrêt

| # | Signal | Condition de déclenchement | Commande de vérification | Action si déclenché | Invariant / Règle violé |
|---|---|---|---|---|---|
| **S1** | P0 non résolu | P0-DOC-01 ou P0-OPS-01 ouvert avant MIGRATION-A | `Get-Content docs/audit/DMS_TECHNICAL_DEBT_P0_P3.md \| Select-String P0` | **STOP total** — pas de migration sur base contradictoire | Gouvernance |
| **S2** | CI rouge > 1 jour | CI rouge pendant semaine 3 (DROP case_id) | `gh run list --limit 5` | **STOP** — restaurer case_id via git revert, replanifier | RÈGLE-03 |
| **S3** | Pool connexions > 80% | Plus de 80 connexions PG en charge | `SELECT count(*) FROM pg_stat_activity` | **STOP** — auditer, réduire pools ou upgrade plan | Infra |
| **S4** | Pass -1 > 60s | Timeout sur 15 fichiers réseau Mopti | Langfuse trace latence | **STOP** — optimiser OCR routing ou réduire parallélisme | SLA EXTRACT |
| **S5** | winner/rank détecté | Champ interdit dans n'importe quelle sortie | `rg "winner\|rank\|recommendation\|best_offer\|selected_vendor" src/` | **STOP** — contrainte CHECK absente ou bypassée | INV-W06, RÈGLE-09 |
| **S6** | Event sans workspace_id | workspace_event avec workspace_id NULL | `SELECT count(*) FROM workspace_events WHERE workspace_id IS NULL` | **STOP** — INV-W05 violé | INV-W05 |
| **S7** | Session sealed transitionnée | committee_session sealed → draft/active | `UPDATE committee_sessions SET session_status='draft' WHERE session_status='sealed'` (doit échouer) | **STOP** — trigger absent | INV-W01 |
| **S8** | WebSocket calcul côté gateway | Donnée pushée non issue de workspace_events | Review code WebSocket handler | **STOP** — INV-W07 violé | INV-W07 |
| **S9** | Appel API réel dans test | Mock absent pour service externe | `rg "httpx\.post\|httpx\.get" tests/ --glob "!*mock*"` | **STOP** — RÈGLE-21 violée | RÈGLE-21 |
| **S10** | Migration autogenerate | Alembic autogenerate utilisé | `rg "autogenerate" alembic/versions/06[89]* alembic/versions/07*` | **STOP** — RÈGLE-12 violée | RÈGLE-12 |
| **S11** | Artefact sans workspace_id | Document/score/event sans workspace_id après 074 | `SELECT 'documents' t, count(*) FROM documents WHERE workspace_id IS NULL UNION ALL SELECT 'score_history', count(*) FROM score_history WHERE workspace_id IS NULL` | **STOP** — INV-W08 violé | INV-W08 |
| **S12** | Append-only violé | UPDATE/DELETE réussi sur table append-only | `UPDATE workspace_events SET payload='{}' WHERE id=1` (doit échouer) | **STOP** — trigger absent | INV-W03 |

---

## Procédure de vérification

Pour chaque signal, exécuter la commande de vérification **avant** chaque gate de semaine.

**Résultat attendu** : tous les signaux sont négatifs (= aucun problème détecté).

**Si un signal est positif** :
1. STOP immédiat — ne pas continuer vers la gate suivante
2. Documenter le signal déclenché, la commande, le résultat
3. Poster au CTO avec preuve
4. Attendre validation humaine avant correction
5. Après correction, re-vérifier TOUS les 12 signaux

---

## Mapping signaux → semaines

| Semaine | Signaux applicables |
|---|---|
| 0 | S1 |
| 1 | S6, S12 |
| 2 | S5, S7, S12 |
| 3 | S2, S10, S11 |
| 4-5 | S4, S9 |
| 6-7 | S5, S6 |
| 8 | S8, S12 |
| 9-10 | S1→S12 (tous — gate finale) |

---

*Gelé après hash. Tout amendement → DMS_V4.2.1_PATCH.md*
