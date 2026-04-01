Pull Request
Description
<!-- Décrivez les changements apportés -->
Type de changement
 Couche A (ouvrier cognitif)

 Couche B (mémoire/market intelligence)

 Infrastructure

 Documentation

 Bug fix

✅ TEST ULTIME DE DÉRIVE (Obligatoire — Constitution §9)
Avant toute évolution, répondre aux 3 questions:

1. Est-ce que cela peut être utilisé contre un individu ?
 ❌ NON

 ⚠️ OUI → Justification requise ci-dessous

Justification si OUI:

<!-- Expliquer pourquoi malgré tout acceptable, ou pourquoi rejet -->
2. Est-ce que cela réduit la liberté de décision humaine ?
 ❌ NON

 ⚠️ OUI → Justification requise ci-dessous

Justification si OUI:

<!-- Expliquer pourquoi malgré tout acceptable, ou pourquoi rejet -->
3. Est-ce que cela centralise le pouvoir cognitif ?
 ❌ NON

 ⚠️ OUI → Justification requise ci-dessous

Justification si OUI:

<!-- Expliquer pourquoi malgré tout acceptable, ou pourquoi rejet -->
🔒 Vérification Invariants Constitution
 Invariant 1: Ne augmente PAS la charge cognitive

 Invariant 2: Ne dégrade PAS la Couche A

 Invariant 3: Mémoire reste un sous-produit (pas d'effort supplémentaire)

 Invariant 4: Système ne décide PAS à la place de l'humain

 Invariant 5: Traçabilité sans accusation

 Invariant 6: Fonctionne en contexte Sahel

 Invariant 7: Reste ERP-agnostique

 Invariant 9: Append-only (pas de suppression)

 Invariant 10: Technologie subordonnée à la vision

📝 Checklist
 Code testé localement

 Tests unitaires ajoutés/mis à jour

 Documentation mise à jour

 Constitution respectée (voir checklist invariants ci-dessus)

 Pas de dépendance externe critique ajoutée

🔧 Migration Alembic (uniquement si la PR modifie ou ajoute `alembic/versions/**`)
 Cocher si applicable — sinon laisser vide (E-82 / `docs/CONTRIBUTING.md`) :

- [ ] `docs/freeze/MRD_CURRENT_STATE.md` — section ÉTAT ALEMBIC
- [ ] `docs/freeze/CONTEXT_ANCHOR.md` — bloc GIT/ALEMBIC
- [ ] `scripts/validate_mrd_state.py` — `_KNOWN_MIGRATION_CHAIN`
- [ ] `tests/test_046b_imc_map_fix.py` — `VALID_ALEMBIC_HEADS` si nouveau head
- [ ] Runbook : `docs/ops/RAILWAY_MIGRATION_RUNBOOK.md`
- [ ] Note sync prod : `docs/adr/ADR-RAILWAY-ALEMBIC-SYNC-GOVERNANCE.md` si impact Railway

👥 Reviewers
Obligatoire:

Tech Lead

Product Owner (si changement fonctionnel)

Si OUI à une question du Test Ultime de Dérive:

Governance board review requis
