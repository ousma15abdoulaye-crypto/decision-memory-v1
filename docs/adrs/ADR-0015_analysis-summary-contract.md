# ADR-0015 — Contrat SummaryDocument v1 (M12 → M13)

**Statut :** ACCEPTED
**Date :** 2026-02-24
**Auteur :** CTO Senior — Abdoulaye Ousmane
**Milestone :** #12 M-ANALYSIS-SUMMARY
**Références :** ADR-0012 (CAS v1), ADR-0014 (séquencement)

---

## Contexte

M12 produit un `SummaryDocument v1`. M13 le consomme.
Ce contrat doit être gelé avant M13 pour éviter tout couplage implicite.

## Décision

### §1 — Structure canonique SummaryDocument v1

Champs obligatoires :
- `summary_id: str` (UUID)
- `case_id: str` (TEXT — FK logique)
- `pipeline_run_id: str | None`
- `summary_version: "v1"` (Literal)
- `summary_status: "ready" | "partial" | "blocked" | "failed"`
- `triggered_by: str` (1–255 chars)
- `generated_at: datetime`
- `source_pipeline_status: str | None`
- `source_cas_version: str | None`
- `sections: list[SummarySection]`
- `warnings: list[dict[str, Any]]` (structurés — pas list[str])
- `errors: list[dict[str, Any]]` (structurés — pas list[str])
- `result_hash: str` (SHA-256 — convention MG-01)

### §2 — SummarySection

- `section_type` : Literal fermé à 6 valeurs
- `content` : dict neutre — champs interdits : winner/rank/champs de jugement
- `warnings` : list[str]

### §3 — Mapping statuts

```python
_STATUS_MAP = {
    "partial_complete": "ready",
    "incomplete":       "partial",
    "blocked":          "blocked",
    "failed":           "failed",
}
# Absent → "blocked"
# CAS malformé → "failed"
```

### §4 — Neutralité (champs interdits dans modèles génériques)

winner, ranking, rank, champs de jugement, champs client-spécifiques

### §5 — Hash déterministe (MG-01)

Convention : `result_hash` partout (source_result_hash banni).
Algorithme : SHA-256(json.dumps(doc_sans_hash, sort_keys=True, default=str))
Champs exclus du calcul : result_hash, summary_id, generated_at

### §6 — Idempotence

Même CAS v1 → même result_hash → une seule ligne dans analysis_summaries.
UNIQUE(result_hash) enforced DB-level (INV-AS9b).

### §7 — Contrat M12→M13

M13 reçoit `SummaryDocument v1` comme seul contrat d'entrée.
M13 ne lit jamais `pipeline_runs.result_jsonb` directement.
M13 ne modifie jamais `analysis_summaries`.

## Conséquences

- Tout changement de `SummaryDocument v1` requiert un nouvel ADR
- M13 est découplé de la logique pipeline
- Un renderer tiers peut consommer `SummaryDocument v1` sans connaître DMS

## Hash de certification

SHA-256 : 358B327652D7217C9979D0A30448E1F4E045D7A10F257507E163D239B34AFBD5
Méthode : sha256(contenu_utf8_de_ce_fichier)
Commande :
  Get-FileHash docs\adrs\ADR-0015_analysis-summary-contract.md -Algorithm SHA256
