# Rapport de validation inter-BLOCs — SPEC BLOC5 V4.3.1

**Statut** : rapport de sondes dépôt + preuves de cohérence pour la session inter-BLOCs.  
**Référence** : SPEC BLOC5 V4.3.1 (ARQ projectors + fondation cognitive).  
**Date** : 2026-04-05

---

## Tableau « LIVRABLE DE VALIDATION » (SPEC — section fin de document)

| Point de validation | Attendu | Preuve / sondage dépôt | Statut |
|---------------------|---------|-------------------------|--------|
| C2-V431 cohérence avec O8 spec | Tous bundles `qualification_status == "qualified"` alimentent la mémoire prix — pas seulement `is_retained` | Avant impl : pas de colonne `qualification_status` sur `supplier_bundles` (070). **Migration 079** ajoute `qualification_status` + `is_retained`. Projecteur ARQ filtre sur `qualified` uniquement pour `price_anchor_update`. | **Vert** sous réserve migrations + code projecteur |
| INV-C15 cohérence schéma DB | Aucune colonne `has_source_package` sur `process_workspaces` | `069` : pas de telle colonne. `has_source_package` = **EXISTS** sur `source_package_documents` (migration **078**). | **Vert** |
| Guards de transition exhaustifs | Couvrent les statuts workspace définis | `069` CHECK sur `status` ; service `validate_transition` introduit dans `src/workspace/status_transitions.py` (à utiliser progressivement par les routeurs). | **Partiel** — adoption route par route hors périmètre strict BLOC5 |
| `committee_session` cohérent avec matrice / FSM | Alignement spec vs DB | DB : `draft`, **`active`**, `in_deliberation`, `sealed`, `closed`. Spec liste `draft`, `in_deliberation`, `sealed`, `closed`, `no_session`. **Mapping API** : `active` → exposé tel quel ; `no_session` si aucune ligne `committee_sessions`. | **Documenté** — pas d’incohérence bloquante |
| Propagation confiance sans faux positif | `[]` → 0.0, pas 1.0 | `compute_bundle_confidence` / `compute_frame_confidence` dans `src/cognitive/confidence_envelope.py` ; tests unitaires `tests/cognitive/test_cognitive_state.py`. | **Vert** (tests) |
| Interfaces C.1/C.2/C.3 sans conflit BLOC 6+ | À confirmer session inter-BLOCs | Hors périmètre dépôt — **CHECKPOINT** produit. | **En attente** |

---

## Écarts sondés (rappel)

- **INV-C02** : `bundle_documents` (070) autorise encore `dao`/`rfq`/`tdr` ; la SPEC exige routage vers `source_package_documents`. **Stratégie** : nouvelles écritures via `POST …/source-package` ; données historiques hors scope migration automatique sauf mandat data.
- **Projecteurs** : `arq_projector_couche_b` consomme `EVALUATION_SEALED` (scores) ; la SPEC ajoute `project_sealed_workspace` post-commit seal. Voir [ADR-BLOC5-V431-EVENT-PROJECTION.md](../adr/ADR-BLOC5-V431-EVENT-PROJECTION.md) pour éviter double écriture.
- **`signal_relevance_log`** : table créée migration **079** ; surfacé max 3 signaux (logique Python).

---

## GO implémentation

Le tableau ci-dessus est **vert ou partiel avec mitigation** pour les lignes techniques ; la ligne « BLOC 6+ » reste **humaine**. **GO code** : validé pour la livraison implémentée sur branche dédiée sous mandat CTO / AO selon gouvernance repo.
