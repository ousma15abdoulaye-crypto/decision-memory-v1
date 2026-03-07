# NOTE DE TRANSMISSION — M7.3b DÉPRÉCIATION LEGACY + PR #170 FIX

```
Date de clôture : 2026-03-06
Sprint          : M7.3b + M7.3b-FIX (PR #170)
Branche         : feat/m7-3b-deprecate-legacy
Tag             : v4.2.0-m7-3b-done
ADR             : ADR-0016
Successeur      : M7 Dictionary Validation (classify_taxo.py)
```

---

## I. ÉTAT À LA CLÔTURE

| Élément | Valeur |
|---------|--------|
| Alembic head | `m7_3b_deprecate_legacy_families` |
| Tag | `v4.2.0-m7-3b-done` |
| Tests | 825 passed · 36 skipped · 0 failed |
| family_id | READ-ONLY total · triggers INSERT + UPDATE |

---

## II. LIVRABLES M7.3b

### Migration
- `m7_3b_deprecate_legacy_families` : family_id DROP NOT NULL, triggers blocage, vue legacy_procurement_families

### Corrections PR #170 (D1–D5)
| D | Correction |
|---|------------|
| D2 | downgrade() idempotent · DO block EXECUTE pour DROP NOT NULL |
| D3 | Trigger UPDATE bloque SET family_id = NULL (WHEN sans AND NEW IS NOT NULL) |
| D4 | Normalisation URL psycopg dans probe_m7_3b (RÈGLE-39) |
| D1 | test_p10/pa8 → test_alembic_head_est_m7_3b |
| D5 | Tests uuid suffix, fixture tx rollback, 8 tests, 0 pollution |

---

## III. RÈGLES GRAVÉES

- RÈGLE-DICT-01 : family_id = READ-ONLY après M7.3b
- RÈGLE-DICT-02 : domain_id/family_l2_id/subfamily_id = cibles M7.2
- RÈGLE-39 : URL postgresql:// · jamais postgresql+psycopg://

---

## IV. PROCHAIN SPRINT — M7 RÉEL

- classify_taxo.py
- seed_apply_taxo.py
- Tag : v4.2.0-m7-dict-vivant

---

*Agent : Composer · DMS V4.2.0 · M7.3b · 2026-03-06*
