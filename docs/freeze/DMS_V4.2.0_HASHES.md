# DMS V4.2.0 — HASHES DE VÉRIFICATION

**Date** : 2026-04-04
**Commande** : `Get-FileHash docs/freeze/DMS_V4.2.0_*.md -Algorithm SHA256` + `*.sql`
**Algorithme** : SHA-256

Ces fichiers sont gelés après hash.
Tout amendement → `DMS_V4.2.1_PATCH.md`
Les fichiers hashés ne sont PLUS JAMAIS modifiés.

---

## Hashes

| Fichier | SHA-256 |
|---|---|
| `DMS_V4.2.0_ADDENDUM.md` | `04D9B0146B5B4910CAA24C7CA016B1B5C070732F90804B179D8016CE20F98278` |
| `DMS_V4.2.0_SCHEMA.sql` | `41CEBBB34E11E8425A2F63626F305B00F243256369960431ED8A7C4DB9E4A517` |
| `DMS_V4.2.0_MIGRATION_PLAN.md` | `EA2EAF401F07346D82F28E76238003336B65A6F541EB075BDD3538F99C65BD98` |
| `DMS_V4.2.0_INVARIANTS.md` | `3DA37FD04F7C44869C08B50050ED6E997E84F9B10CF5432620A4DB1D682FB9E7` |
| `DMS_V4.2.0_RBAC.md` | `A8B9FACD5942BE449FBCB5BB2413A2C1D8CE15F5A4B6CE0918B5E84AB76DEBC7` |
| `DMS_V4.2.0_STOP_SIGNALS.md` | `5476CB2A41A74A30435EAAD4F69C5427FD322D4CF3EAB76E241751327E51B13F` |

---

## Vérification

```powershell
Get-FileHash docs/freeze/DMS_V4.2.0_ADDENDUM.md -Algorithm SHA256
Get-FileHash docs/freeze/DMS_V4.2.0_SCHEMA.sql -Algorithm SHA256
Get-FileHash docs/freeze/DMS_V4.2.0_MIGRATION_PLAN.md -Algorithm SHA256
Get-FileHash docs/freeze/DMS_V4.2.0_INVARIANTS.md -Algorithm SHA256
Get-FileHash docs/freeze/DMS_V4.2.0_RBAC.md -Algorithm SHA256
Get-FileHash docs/freeze/DMS_V4.2.0_STOP_SIGNALS.md -Algorithm SHA256
```

Comparer avec le tableau ci-dessus. Si un hash diffère, le fichier a été modifié après freeze.

---

*Gelé. Ce fichier lui-même n'est plus modifié après publication.*
