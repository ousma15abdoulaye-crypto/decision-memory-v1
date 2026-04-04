# DMS V4.2.0 — Pilote SCI Mali : Runbook Go/No-Go

**Référence** : Plan V4.2.0 Phase 6 — 5 processus SCI Mali réels, performance gates, 12 STOP SIGNALS  
**Autorité** : CTO sign-off obligatoire avant exécution  
**Date cible** : Post-déploiement migrations 068-075

---

## 0. Prérequis avant pilote

| # | Condition | Vérification |
|---|-----------|-------------|
| P0-1 | Migrations 068-075 appliquées | `alembic current` = `075_rbac_permissions_roles` |
| P0-2 | Tenant `sci_mali` présent | `SELECT code FROM tenants WHERE code='sci_mali'` |
| P0-3 | Tables V4.2.0 créées | `\dt process_workspaces`, `workspace_events`, `rbac_permissions` |
| P0-4 | ARQ worker démarré | `arq src.workers.arq_config.WorkerSettings` lancé |
| P0-5 | Redis opérationnel | `REDIS_URL` défini, ping ok |
| P0-6 | Annotation-backend non redéployé (gel actif) | Aucune modification `services/annotation-backend/` |

---

## 1. Description des 5 processus pilote

Cinq processus d'achat SCI Mali réels à rejouer sur V4.2.0 workspace-first :

| # | Processus | Type | Nb fournisseurs | Lots |
|---|-----------|------|----------------|------|
| P1 | Achat fournitures bureau Q1-2025 | Biens | 3 | 1 |
| P2 | Prestation transport distribution vivres | Services | 5 | 2 |
| P3 | Achat médicaments ORS + SRO | Médicaments | 4 | 3 |
| P4 | Contrat gardiennage 12 mois | Services | 2 | 1 |
| P5 | Fournitures WASH (seaux, aquatabs) | Biens | 6 | 4 |

**Données** : Dossiers ZIP extraits des archives SharePoint SCI Mali.  
**Objectif** : Valider le flux complet `workspace → ZIP → bundles → évaluation → comité → sealed`.

---

## 2. Performance Gates (obligatoires avant GO)

### Gate PG-1 : Pass -1 < 30s par workspace

```sql
-- Mesurer la durée ARQ run_pass_minus_1 pour chaque workspace
SELECT
    workspace_id,
    EXTRACT(EPOCH FROM (emitted_at - LAG(emitted_at) OVER (PARTITION BY workspace_id ORDER BY id))) AS delta_s
FROM workspace_events
WHERE event_type IN ('BUNDLE_CREATED', 'PASS_1_STARTED')
ORDER BY workspace_id, id;
```

**Seuil** : P50 < 30s, P95 < 90s. Échec → STOP SIGNAL 7.

### Gate PG-2 : WebSocket latence < 3s

- Mesurer délai entre `INSERT INTO workspace_events` et réception côté client WS.
- Outil : script `scripts/probe_ws_latency.py` (à créer lors du pilote).
- **Seuil** : P95 < 3s. Échec → optimiser `POLL_INTERVAL_S` dans `workspace_events.py`.

### Gate PG-3 : Projector Couche B sans perte

```sql
-- Vérifier ratio ok/total dans arq_projection_log
SELECT
    status,
    COUNT(*) as n,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) as pct
FROM arq_projection_log
GROUP BY status;
```

**Seuil** : status='ok' ≥ 95%. Échec → STOP SIGNAL 10.

### Gate PG-4 : RLS isolation tenant

```sql
-- En tant qu'user tenant A, tenter d'accéder workspace tenant B
SET LOCAL app.tenant_id = 'tenant-a-uuid';
SET LOCAL app.is_admin = 'false';
SELECT id FROM process_workspaces;
-- Résultat attendu : 0 rows (isolation confirmée)
```

**Seuil** : 0 lignes retournées. Échec → STOP SIGNAL 12 (critique).

### Gate PG-5 : Comité sealed irréversible

```sql
-- Tenter UPDATE sur workspace sealed
UPDATE process_workspaces SET status = 'open'
WHERE status = 'sealed';
-- Résultat attendu : ERROR trigger_workspace_fsm
```

**Seuil** : Exception levée. Échec → STOP SIGNAL 8.

---

## 3. Les 12 STOP SIGNALS V4.2.0

Ces signaux déclenchent un arrêt immédiat du pilote et un escalade CTO.

| # | Signal | Condition de déclenchement | Action |
|---|--------|---------------------------|--------|
| SS-1 | `alembic heads > 1` | `alembic heads` retourne plus d'une ligne | STOP + signaler CTO |
| SS-2 | Migration irréversible appliquée sur mauvaise branche | Migration 074 exécutée hors branche feat/v420 | STOP + rollback 073 |
| SS-3 | `users.id` UUID détecté | FK workspace_events.actor_id = UUID type | STOP + patch 004 |
| SS-4 | `case_id` présent après migration 074 | `SELECT column_name FROM information_schema.columns WHERE column_name='case_id' AND table_name IN ('documents','offer_extractions')` retourne > 0 | STOP + vérifier 074 |
| SS-5 | workspace_events non append-only | UPDATE/DELETE accepté sur workspace_events | STOP + vérifier trigger |
| SS-6 | `confidence` hors {0.6, 0.8, 1.0} dans extraction | `SELECT DISTINCT confidence FROM dms_extraction_results WHERE confidence NOT IN (0.6, 0.8, 1.0)` retourne > 0 | STOP + audit KILL LIST |
| SS-7 | Pass -1 P50 > 30s | Gate PG-1 échoue sur 3 workspaces consécutifs | STOP + profiler assembler |
| SS-8 | FSM sealed réversible | Gate PG-5 accepte UPDATE sur sealed | STOP + corriger trigger |
| SS-9 | ARQ worker absent | `project_workspace_events_to_couche_b` non enregistré dans WorkerSettings | STOP + corriger arq_config.py |
| SS-10 | Projector perte > 5% | Gate PG-3 : status='failed' > 5% | STOP + audit arq_projector_couche_b.py |
| SS-11 | WebSocket non connecté | `/ws/workspace/{id}/events` retourne 404 ou 500 | STOP + vérifier main.py wiring |
| SS-12 | RLS isolation brisée | Gate PG-4 retourne lignes d'un autre tenant | STOP CRITIQUE + escalade sécurité |

---

## 4. Script de validation pré-pilote

```bash
# Lancer avant démarrage du pilote
python scripts/validate_v420_pilote_gates.py --tenant sci_mali
```

Le script vérifie automatiquement SS-1 à SS-6 et SS-9. Les gates PG-1 à PG-5 sont vérifiées manuellement pendant le pilote.

---

## 5. Déroulement Go/No-Go

### Étape 1 — Création workspaces (J0)

```python
# POST /api/workspaces pour chaque processus P1-P5
workspaces = [
    {"title": "Fournitures bureau Q1-2025", "process_type": "GOODS_PROCUREMENT"},
    {"title": "Transport distribution vivres", "process_type": "SERVICE_PROCUREMENT"},
    {"title": "Médicaments ORS + SRO", "process_type": "GOODS_PROCUREMENT"},
    {"title": "Gardiennage 12 mois", "process_type": "SERVICE_PROCUREMENT"},
    {"title": "WASH fournitures", "process_type": "GOODS_PROCUREMENT"},
]
```

### Étape 2 — Upload ZIPs (J0)

```
POST /api/workspaces/{id}/upload-zip
Authorization: Bearer <JWT>
Content-Type: multipart/form-data
```

ARQ démarre `run_pass_minus_1` automatiquement.

### Étape 3 — Vérifier bundles (J0+2h)

```sql
SELECT
    pw.title,
    COUNT(sb.id) AS nb_bundles,
    SUM(bd.id) AS nb_documents
FROM process_workspaces pw
LEFT JOIN supplier_bundles sb ON sb.workspace_id = pw.id
LEFT JOIN bundle_documents bd ON bd.workspace_id = pw.id
WHERE pw.tenant_id = (SELECT id FROM tenants WHERE code='sci_mali')
GROUP BY pw.title;
```

**Attendu** : nb_bundles ≥ 2 pour P2 (2 lots), P3 (3 lots).

### Étape 4 — Délibération comité (J1)

- Ouvrir session via `POST /api/workspaces/{id}/committee-session/open`
- Ajouter membres comité via `POST .../add-member`
- Sceller via `POST .../seal`
- Vérifier SS-8 (irréversibilité)

### Étape 5 — Projection Couche B (J1+1h)

- Vérifier Gate PG-3 (projector ok ≥ 95%)
- Vérifier `vendor_market_signals` enrichi pour les fournisseurs P1-P5

### Étape 6 — Sign-off CTO (J2)

**GO** si toutes les conditions :
- [ ] SS-1 à SS-12 : aucun signal déclenché
- [ ] PG-1 à PG-5 : tous les seuils respectés
- [ ] 5 workspaces status = 'sealed'
- [ ] vendor_market_signals count ≥ 15 nouvelles lignes
- [ ] arq_projection_log ok ≥ 95%

**NO-GO** si un seul SS déclenché ou un gate PG échoue.

---

## 6. Rollback plan

En cas de NO-GO après migration 074 :

```bash
# 1. Alembic downgrade vers 073
alembic downgrade 073

# 2. Rétablir case_id colonnes
# (La migration 073 est additive — les case_id colonnes sont encore présentes
# jusqu'à 074. Après 074, rollback requiert restauration backup.)

# 3. Arrêter ARQ worker
# 4. Notifier CTO pour décision
```

**CRITIQUE** : La migration 074 (DROP case_id) est irréversible sans backup.  
Prendre un snapshot Railway avant d'appliquer 074.

---

*Document créé par mandat DMS-MAP-M0-M15-001 — Phase 6 pilote SCI Mali*  
*Autorité : CTO sign-off requis avant exécution*
