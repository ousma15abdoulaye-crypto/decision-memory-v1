# MANDAT INGESTION PROD — TEMPS 0 + TEMPS 0bis · RAPPORT

**Date :** 2026-03-07  
**Branche :** feat/m7-4-dict-vivant

---

## TEMPS 0 — ÉTAT RÉEL PROD

### 5 SQL counts

```
vendors:      0
mercurials:   0
imc_total:    0  annee_min: None  annee_max: None  nb_annees: 0
dict_actifs:  51
alembic_version: m7_3b_deprecate_legacy_families
```

### Liste scripts (triée)

```
__pycache__
_acte6_option_a.py
_cleanup_prod_smoke_users.py
_dod_m0b_probe.py
_preuve_1_2.py
_probe_audit_log_schema.py
_probe_couche_b_complet.py
_probe_dict_complement_stop.py
_probe_dict_schema_stop.py
_probe_final_m6.py
_probe_imc_db.py
_probe_item_raw_canonical.py
_probe_m1.py
_probe_m1_post.py
_probe_m1_role.py
_probe_m1b.py
_probe_m1b_post.py
_probe_m6_post.py
_probe_m73_final.py
_probe_m73_todo.py
_probe_post_build.py
_probe_post_downgrade.py
_probe_step1_db_safe.py
_probe_step2_vendors_prod.py
_smoke_m2.py
_test_admin_login.py
apply_fk_prod.py
audit_criteria_fk_orphans.py
build_dictionary.py
classify_taxonomy_v2.py
create_db_simple.py
etl_vendors_m4.py
etl_vendors_wave2.py
extract_pr79_logs.ps1
fetch_pr_logs.md
fix_alembic_version_017_to_018.py
fix_backfill_taxonomy.py
fix_template.py
freeze
import_imc.py
import_mercuriale.py
probe_imc_format.py
probe_m7_3_nerve_center.py
probe_m7_3b.py
probe_m7_pre.py
probe_m7_taxo_reset.py
probe_m74.py
probe_users_id_type.py
regenerate_freeze_checksums.sh
regenerate_freeze_checksums_win.ps1
reset_password_simple.ps1
reset_postgres_password.ps1
runbook_m2b_local.sql
seed_classification_backfill.py
seed_taxonomy_v2.py
setup_db.py
setup_db_with_password.py
setup_postgres_local.ps1
smoke_postgres.py
validate_all.sh
validate_taxo_batch.py
```

---

## TEMPS 0bis — ÉTAPE A · 4 SCRIPTS IDENTIFIÉS

### Vendors (plusieurs candidats)
```
etl_vendors_m4.py
etl_vendors_wave2.py
_probe_step2_vendors_prod.py
```
**STOP · 2 candidats ingest : etl_vendors_m4.py, etl_vendors_wave2.py · GO Tech Lead pour confirmer.**

### Mercurials
```
import_mercuriale.py
```

### IMC
```
import_imc.py
probe_imc_format.py
_probe_imc_db.py
```
**Script ingest : import_imc.py**

### Dictionary build
```
build_dictionary.py
_probe_post_build.py
```
**Script ingest : build_dictionary.py**

---

## TEMPS 0bis — ÉTAPE B · DATABASE_URL et normalisation

Les scripts **n'utilisent pas DATABASE_URL directement** dans leur code.  
Ils passent par `src.db` (get_connection) qui :
- lit `os.environ.get("DATABASE_URL")` (src/db/core.py, src/db/connection.py)
- normalise `postgresql+psycopg://` → `postgresql://` (src/db/connection.py L30)

| Script | DATABASE_URL direct | Via get_connection | Normalisation |
|--------|---------------------|-------------------|---------------|
| etl_vendors_m4.py | NON | OUI (insert_vendor → src.db) | OUI (connection.py) |
| etl_vendors_wave2.py | NON | OUI (get_connection) | OUI |
| import_mercuriale.py | NON | OUI (importer → repository) | OUI |
| import_imc.py | NON | OUI (repository) | OUI |
| build_dictionary.py | OUI L46-48 | — | OUI L52-53 |

**build_dictionary.py** : DATABASE_URL présent + normalisation postgresql+psycopg.

---

## TEMPS 0bis — ÉTAPE C · --dry-run

| Script | --dry-run présent |
|--------|-------------------|
| etl_vendors_m4.py | OUI (argparse) |
| etl_vendors_wave2.py | OUI (argparse) |
| import_mercuriale.py | OUI (sys.argv) |
| import_imc.py | OUI (argparse) |
| build_dictionary.py | OUI (argparse) |

**0 manquant.**

---

## TEMPS 0bis — ÉTAPE D · Colonnes legacy

**STOP-I6 DÉTECTÉ**

`scripts/build_dictionary.py` L391-398 :
```python
INSERT INTO couche_b.procurement_dict_items (
    item_id, family_id, label_fr,
    ...
) VALUES (
    %s, 'equipements', %s,
    ...
)
```

**Écriture sur family_id = interdit post-M7.3b.**  
Les triggers `trg_block_legacy_family_insert` bloquent tout INSERT avec family_id non NULL.

**STOP-I6 · Ne pas lancer build_dictionary.py avant correction. GO Tech Lead.**

---

## TEMPS 0bis — ÉTAPE E · Chemins hardcodés

| Pattern | Résultat |
|---------|----------|
| C:\\Users | 0 |
| /home/ | 0 |
| /Users/ | 0 |
| data/imports | etl_vendors_m4, etl_vendors_wave2, import_mercuriale |

**data/imports** : chemins relatifs (ROOT / "data/imports/m4/...", Path("data/imports/m5/...")).  
**0 STOP-I8.**

---

## TEMPS 0bis — ÉTAPE F · INSERT/UPDATE cibles

| Script | INSERT/UPDATE |
|--------|---------------|
| etl_vendors_m4 | insert_vendor → INSERT INTO vendors |
| etl_vendors_wave2 | insert_vendor → INSERT INTO vendors |
| import_mercuriale | repository → mercurials + mercuriale_sources |
| import_imc | insert_source, insert_entries_batch → imc_sources, imc_entries |
| build_dictionary | procurement_dict_items, dict_aliases, dict_proposals |

Conformes aux tables cibles attendues.

---

## TEMPS 0bis — ÉTAPE G · Schéma vendors

```
id uuid NO
vendor_id text NO
fingerprint text NO
name_raw text NO
name_normalized text NO
zone_raw text YES
zone_normalized text YES
region_code text NO
category_raw text YES
email text YES
phone text YES
email_verified boolean NO
is_active boolean NO
source text NO
created_at timestamp with time zone NO
updated_at timestamp with time zone NO
activity_status text NO
verified_at timestamp with time zone YES
verified_by text YES
verification_source text YES
canonical_name text NO
aliases ARRAY NO
nif text YES
rccm text YES
rib text YES
verification_status text NO
vcrn text YES
zones_covered ARRAY NO
category_ids ARRAY NO
has_sanctions_cert boolean NO
has_sci_conditions boolean NO
key_personnel_verified boolean NO
suspension_reason text YES
suspended_at timestamp with time zone YES
```

---

## RÉSUMÉ STOP

| Signal | Statut |
|--------|--------|
| STOP-I6 | **ACTIF** — build_dictionary.py écrit family_id |
| ÉTAPE A | **2 candidats vendors** — GO Tech Lead pour nom exact |

---

**STOP. GO Tech Lead requis.**
