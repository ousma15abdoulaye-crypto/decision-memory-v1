# PV production — LOT 3

**Date** : 2026-04-06

## Fonction canonique

- **`build_pv_snapshot(conn, workspace_id, session_id, user_id, seal_comment)`** — produit snapshot + `seal_hash`.
- **`validate_pv_snapshot(snapshot)`** — blocs obligatoires : `process`, `committee`, `deliberation`, `evaluation`, `decision`, `meta` ; champs `meta.*` ; pas de kill list dans `scores_matrix`.
- Constantes : `SNAPSHOT_SCHEMA_VERSION`, `RENDER_TEMPLATE_VERSION` dans `pv_builder.py`.

## Pipeline documentaire

`pv_snapshot` scellé en DB → export lit **uniquement** ce JSON → Jinja2 (`templates/pv/`) → WeasyPrint PDF. Pas de logique métier dans les templates — données déjà dans le snapshot.

## PDF

- Footer : hash + session + date + **lignes schéma/template** si `meta` présent (`_seal_footer.html.j2`).

## Tests

- `tests/services/test_pv_builder.py`, `test_comparative_table_model.py` (validation), `tests/api/test_committee_pv_export.py`.

## Preuve export fichier

- Non attaché : dépend d’un workspace **sealed** en prod — statut pilote **ROUGE** au check SQL (voir `PRODUCT_PROOF_REPORT.md`).
