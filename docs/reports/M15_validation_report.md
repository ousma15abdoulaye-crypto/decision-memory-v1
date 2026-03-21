# Rapport de validation M15 (squelette)

**Statut :** brouillon — à compléter au gel du jalon M15.  
**Mandat :** [`docs/mandates/DATA-M15.md`](../mandates/DATA-M15.md)  
**Dernière mise à jour :** 2026-03-21

---

## 1. Objectif

Documenter la conformité du corpus et des métriques opposables au périmètre freeze (100 dossiers, seuils RÈGLE-10 / RÈGLE-23, etc.) sans recopier les chiffres ici : renvoyer vers le freeze courant.

## 2. Périmètre et échantillon

- Liste blanche `case_id` / organisations (réf. interne).
- Version `export_schema_version` / outil d’export utilisé.

## 3. Gates techniques exécutées

| Gate | Emplacement | Résultat (à remplir) |
|------|-------------|----------------------|
| Export LS → JSONL `export_ok` + QA validée | `scripts/export_ls_to_dms_jsonl.py` + `--m15-gate` | |
| Politique `annotated_validated` | `scripts/m15_export_gate.py` | |

## 4. Signatures

- **Owner DATA-M15 :** (voir mandat §5)
- **Date de gel rapport :** TBD

## 5. Références

- `docs/freeze/DMS_V4.1.0_FREEZE.md`
- `docs/freeze/ANNOTATION_FRAMEWORK_DMS_v3.0.1.md`
- `docs/audits/SEC_MT_01_BASELINE.md` (contexte prod / RLS)
