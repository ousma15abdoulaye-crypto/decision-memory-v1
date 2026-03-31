# Railway Migration Runbook — DMS v4.1

**Autorite** : CTO / AO — Abdoulaye Ousmane  
**Regle** : REGLE-ANCHOR-06 — RAILWAY PROTEGE  
**Flag requis** : `DMS_ALLOW_RAILWAY_MIGRATE=1`  
**Merge** : humain uniquement  

---

## Etat actuel (2026-03-30)

| Point | Valeur |
|-------|--------|
| Repo head | `054_m12_correction_log` |
| Railway head | `044_decision_history` (DESYNCHRONISE) |
| Delta | 11 migrations pending |

---

## Pre-requis avant tout lot

### 1. Probe local

```powershell
python scripts/probe_alembic_head.py
python scripts/probe_railway_counts.py
```

### 2. Probe Railway

```powershell
# RAILWAY_DATABASE_URL doit etre dans .env.local (jamais commite)
python scripts/probe_alembic_head.py --railway
python scripts/probe_railway_counts.py --railway
```

### 3. Verifier le state systeme

```powershell
python scripts/validate_mrd_state.py --railway
```

Tous les STOP doivent etre absents avant de continuer.

---

## Lots de migration (sequence obligatoire)

### LOT 1 — Infrastructure agents (risque faible)

Migrations : `045`, `046`, `046b`

| Migration | Description |
|-----------|-------------|
| `045_agent_native_foundation` | couche_a.agent_checkpoints, agent_runs_log, pg_notify |
| `046_imc_category_item_map` | Mapping categories IMC |
| `046b_imc_map_fix_restrict_indexes` | Correctif indexes IMC |

**Commande Railway** :
```bash
DMS_ALLOW_RAILWAY_MIGRATE=1 alembic upgrade 046b_imc_map_fix_restrict_indexes
```

**Probe post-lot** :
```powershell
python scripts/probe_alembic_head.py --railway
python scripts/probe_railway_counts.py --railway
```

**Rollback lot 1** :
```bash
alembic downgrade 044_decision_history
```

---

### LOT 2 — Couche A + securite donnees (risque moyen)

Migrations : `047`, `048`, `049`, `050`

| Migration | Description |
|-----------|-------------|
| `047_couche_a_service_columns` | Colonnes service couche_a |
| `048_vendors_sensitive_data` | Chiffrement donnees sensibles vendors |
| `049_validate_pipeline_runs_fk` | FK validation pipeline_runs |
| `050_documents_sha256_not_null` | SHA256 not null sur documents |

**Prerequis** : Lot 1 probe OK.

**Commande Railway** :
```bash
DMS_ALLOW_RAILWAY_MIGRATE=1 alembic upgrade 050_documents_sha256_not_null
```

**Attention migration 050** : `documents.sha256` devient NOT NULL. Verifier que
tous les documents existants ont un SHA256 avant d'appliquer. Si des documents
ont `sha256 IS NULL` sur Railway, backfiller avant.

**Probe post-lot** :
```powershell
python scripts/probe_alembic_head.py --railway
python scripts/probe_railway_counts.py --railway
```

**Rollback lot 2** :
```bash
alembic downgrade 046b_imc_map_fix_restrict_indexes
```

---

### LOT 3 — RLS + M12 (risque eleve)

Migrations : `051`, `052`, `053`, `054`

| Migration | Description |
|-----------|-------------|
| `051_cases_tenant_user_tenants_rls` | Row Level Security cases/tenants |
| `052_dm_app_rls_role` | Role PostgreSQL dm_app |
| `053_dm_app_enforce_security_attrs` | Attributs securite dm_app |
| `054_m12_correction_log` | Table feedback loop M12 (append-only) |

**Prerequis** : Lots 1 et 2 probes OK. Role `dm_app` inexistant sur Railway
sera cree par 052 — verifier les permissions Railway beforehand.

**Commande Railway** :
```bash
DMS_ALLOW_RAILWAY_MIGRATE=1 alembic upgrade 054_m12_correction_log
```

**Probe post-lot** :
```powershell
python scripts/probe_alembic_head.py --railway
python scripts/probe_railway_counts.py --railway
```

Verifier :
- `alembic_version` = `054_m12_correction_log`
- `m12_correction_log` table presente (count = 0, normal)
- triggers couche_b tous presents

**Rollback lot 3** :
```bash
alembic downgrade 050_documents_sha256_not_null
```

---

## Apres tous les lots — verification finale

```powershell
python scripts/validate_mrd_state.py --railway
```

Resultat attendu : `SYSTEME OK — PRET POUR MANDAT`

Mettre a jour `docs/freeze/CONTEXT_ANCHOR.md` :
- `alembic head Railway : 054_m12_correction_log (SYNCHRONISE)`
- Supprimer la ligne `migrations pending Railway`
- Commit : `docs(anchor): Railway synced 044→054 — YYYY-MM-DD`

---

## Gouvernance

- `DMS_ALLOW_RAILWAY_MIGRATE=1` : positionnee uniquement via Railway dashboard Variables, retirée apres chaque lot
- `start.sh` n'applique les migrations QUE si ce flag est present (REGLE-ANCHOR-06)
- Jamais de `alembic autogenerate` (REGLE-ANCHOR-05)
- Jamais de modification de migration existante (REGLE-ANCHOR-05)
- Chaque rollback = decision CTO documentee
