# État produit — mandat DMS-MANDAT-HARDENING-PRODUCT-001

**Date** : 2026-04-06  
**Verdict synthétique** : **AMBRE** — runtime structuré ; preuve seal complète sur workspace pilote **non verte** au moment du check SQL.

## Ce qui existe (code vivant)

| Zone | Fichiers / routes |
|------|-------------------|
| Seal | `POST …/committee/seal` → `build_pv_snapshot` → `committee_sessions` + `process_workspaces` |
| Snapshot + hash | `src/services/pv_builder.py` — `validate_pv_snapshot`, bloc `meta`, kill list |
| Exports | `GET …/committee/pv` JSON/PDF/XLSX — `document_service.get_sealed_session` (pas de recalcul métier hors snapshot) |
| Comparatif XLSX | `build_comparative_table_model_from_snapshot` → `build_xlsx_export` |
| M14 | `m14_evaluation_repository.py` — `workspace_id` (post-074) |
| Tests | `tests/services/test_pv_builder.py`, `test_comparative_table_model.py`, `test_committee_pv_export.py`, `test_document_service.py` |

## Ce qui manquait / fermé dans ce mandat

- Bloc **`meta`** obligatoire + **`validate_pv_snapshot`** avant hash.
- **`build_evaluation_projection`** partagé PV / comparatif.
- **`build_comparative_table_model`** / **`_from_snapshot`** explicites.
- Script SQL **`scripts/hardening_product_sql_checks.py`**.

## Ce qui casse encore (preuve machine)

- Workspace pilote `3a1ebd0e-dc79-4b40-bc94-dcae1de6d33f` (Railway) : **pas sealed** — `session_status=active`, `seal_hash` / `pv_snapshot` NULL (check 2026-04-06).

## Ordre d’attaque résiduel

1. Déployer correctif seal si besoin → `POST …/committee/seal` → rerun `hardening_product_sql_checks.py` → **VERT** attendu.
2. Relecture métier PDF (institutionnel) sur un export réel scellé.
3. Optionnel : test d’intégration DB complet `build_xlsx_export` si openpyxl / DataBar homogène en CI.
