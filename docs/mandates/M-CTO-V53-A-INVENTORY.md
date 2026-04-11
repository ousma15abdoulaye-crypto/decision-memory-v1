# M-CTO-V53-A — Inventaire opposable + ADR « Market read model »

**ID :** `M-CTO-V53-A`  
**Type :** Documentation + ADR (aucun code applicatif)  
**Dépend de :** rien  
**Bloque :** `M-CTO-V53-B`

---

## 1. Objectif

1. Produire une **matrice écrivains / lecteurs / table** pour les domaines à doubles vérités (marché, historiques M16, mémoire, event index, corrections M12).  
2. Adopter un **ADR unique** qui tranche la **préséance de lecture** pour les **écarts prix** et le **rôle** de `vendor_market_signals` vs `market_signals_v2`.

---

## 2. Références obligatoires (lecture avant écriture)

| Document | Chemin |
|----------|--------|
| Addendum workspace-first | `docs/freeze/DMS_V4.2.0_ADDENDUM.md` |
| Registre ruptures V5.2 | `docs/audit/RUPTURES_V52.md` |
| Reconstruction V5.2 | `docs/audit/V52_RECONSTRUCTION_COMPLETE.md` |
| Canon V5.1 signal / O7 | `docs/freeze/DMS_CANON_V5.1.0_FREEZE.md` (sections O6–O7) |
| Atlas cognitif L2 | `docs/architecture/dms_atlas_v1/P0_L2_cognitive_engine.md` |

---

## 3. Périmètre fichiers — ALLOWLIST (seuls fichiers modifiables ou créables)

| Action | Chemin |
|--------|--------|
| **Créer** | `docs/adr/ADR-V53-MARKET-READ-MODEL.md` |
| **Créer** | `docs/audit/V53_WRITERS_READERS_MATRIX.md` |
| **Modifier** | `docs/mandates/M-CTO-V53-SOVEREIGNTY-00-INDEX.md` (ajouter lien « A DONE » / date si politique équipe) |

### INTERDIT (hors ALLOWLIST)

- Tout fichier sous `src/`, `tests/`, `services/`, `alembic/`, `.github/`, `frontend-v51/`
- Tout autre fichier `docs/**` non listé ci-dessus

---

## 4. Contenu minimal exigé

### 4.1 `docs/audit/V53_WRITERS_READERS_MATRIX.md`

Tableaux séparés (minimum) :

- **Marché** : `market_signals_v2`, `vendor_market_signals`, `market_surveys`, `survey_campaigns`, `mercurials` (si lecteurs dans le repo) — colonnes : *Writer*, *Readers*, *Fréquence*, *Invariant*.
- **M16 prix** : `price_line_comparisons`, `price_line_bundle_values` — lien avec `market_delta.py`.
- **M16 historique** : `assessment_history`, `criterion_assessment_history`, triggers V52.
- **Mémoire** : `memory_entries`, `dms_event_index`, writers triggers (réf. migrations `066`, `077`).
- **Corrections** : `m12_correction_log` — constat writer sans route (réf. `src/procurement/m12_correction_writer.py` lecture seule dans matrice).

### 4.2 `docs/adr/ADR-V53-MARKET-READ-MODEL.md`

Sections obligatoires :

- **Contexte** : R9 / E24 (`RUPTURES_V52`).
- **Décision** : (ex.) *« Lecture agrégée signal prix pour M16 / PV / MQL tabulaire = `market_signals_v2` ; `vendor_market_signals` = projection post-scellement pour mémoire fournisseur, alimentée uniquement par … »* — la décision exacte est **CTO** ; le mandat impose seulement qu’elle soit **binaire** et **testable**.
- **Conséquences** : liste des modules impactés pour phase B (noms de fichiers).
- **Statut** : Proposed → Accepted (signature CTO).

---

## 5. Definition of Done (binaire)

- [ ] Les deux fichiers **créés** et **review CTO**.
- [ ] Aucun autre fichier modifié hors ALLOWLIST.
- [ ] Branche : `feat/M-CTO-V53-A` ; PR unique ; CI docs-only (si applicable) verte.

---

## 6. Commits (exemples)

```
docs(M-CTO-V53-A): add writers-readers matrix V53
docs(M-CTO-V53-A): ADR-V53 market read model decision
```

---

*Mandat exécutable — périmètre fermé.*
