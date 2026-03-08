# ADR-MRD-001 — Restauration des migrations m7_4 et m7_4a dans origin/main

**Date :** 2026-03-08  
**Statut :** ACCEPTÉ  
**Auteur :** Agent MRD-1  
**Branche :** feat/mrd-1-align-origin-main  
**Cherry-pick source :** commit 7219636 (main local)

---

## Contexte

À la clôture du milestone M7.3b (`64d7e12`, PR #170), `origin/main` ne contenait pas les migrations :
- `alembic/versions/m7_4_dict_vivant.py`
- `alembic/versions/m7_4a_item_identity_doctrine.py`

Or, la base Railway de production avait déjà appliqué ces deux migrations (`alembic head = m7_4a_item_identity_doctrine`).

**Situation avant ce PR :**

| Référentiel | Alembic head |
|---|---|
| origin/main (64d7e12) | m7_3b_deprecate_legacy_families |
| main local (7219636) | m7_4a_item_identity_doctrine |
| Railway DB (prod) | m7_4a_item_identity_doctrine |

**Drift détecté :** origin/main était en retard de 2 migrations sur Railway prod.

---

## Décision

Promouvoir les deux migrations vers `origin/main` via cherry-pick du commit `7219636` sur une branche dédiée.

**Chaîne de révisions validée :**

```
m7_3b_deprecate_legacy_families
  └─ m7_4_dict_vivant          (down_revision = m7_3b_deprecate_legacy_families)
       └─ m7_4a_item_identity_doctrine  (down_revision = m7_4_dict_vivant)
```

**Vérification effectuée :**
- `alembic heads` = `m7_4a_item_identity_doctrine (head)` — 1 seule tête ✓
- `git diff origin/main HEAD --name-only` = 2 fichiers uniquement ✓
- Zéro conflit au cherry-pick ✓

---

## Conséquences

### Positives
- `origin/main` devient aligné avec Railway prod (aucune migration manquante).
- Le pipeline CI peut désormais vérifier `alembic heads` sans drift.
- Toute future branche créée depuis `origin/main` aura la chaîne Alembic complète.

### Contraintes posées

1. **RÈGLE-T04 stricte** : aucune des deux migrations ne contient de `DROP`. Confirmé par relecture des fichiers.
2. **RÈGLE-12** : SQL brut uniquement dans les deux migrations. Confirmé.
3. **RÈGLE-ID03** (m7_4a) : jamais écraser une identité existante. Confirmé.
4. Les 5 fichiers modifiés du working tree (`HANDOVER_AGENT.md`, `build_dictionary.py`, `etl_vendors_wave2.py`, `seed_taxonomy_v2.py`, `test_m7_3b_legacy_block.py`) sont **hors scope de ce PR**. Ils constituent une dette de working tree à traiter dans un mandat séparé.

### Risques résiduels

| Risque | Sévérité | Mitigation |
|---|---|---|
| `ON DELETE CASCADE` sur `procurement_dict_aliases.item_id` (identifié en audit M4→M7) | S3 | Hors scope MRD-1 — ADR séparé requis |
| `m7_rebuild_t0_purge.py` destructif toujours présent | S4 | Hors scope MRD-1 — ADR séparé requis |
| Working tree dirty (5 fichiers non commités) | S2 | À traiter en mandat suivant |

---

## Alternatives rejetées

| Alternative | Raison du rejet |
|---|---|
| `git push --force origin main` | Destructif, interdit sans CTO explicite |
| Créer un nouveau commit avec les 2 fichiers de migration | Cherry-pick préféré pour traçabilité (lien SHA→SHA) |
| Ne pas aligner et laisser le drift | Inacceptable — Railway prod déjà à m7_4a |

---

## Validation requise

- [ ] CTO review du diff (2 fichiers de migration uniquement)
- [ ] CI verte sur la branche `feat/mrd-1-align-origin-main`
- [ ] `alembic upgrade head` en env de staging avant merge
- [ ] Merge via PR (no fast-forward ou squash selon politique repo)
- [ ] Tag `v0.7.4a` post-merge si applicable
