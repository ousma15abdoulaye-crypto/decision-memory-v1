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
| `DMS_V4.2.0_ADDENDUM.md` | `0484F009052B66FEC5F1CDA039320FCC51A4E0CF425E4589B415C4B9B2AA35F4` |
| `DMS_V4.2.0_SCHEMA.sql` | `DC31228F87393BECF380BFF67F6E16E06C6A4698C1DD8F75E65192FA5C690503` |
| `DMS_V4.2.0_MIGRATION_PLAN.md` | `EA2EAF401F07346D82F28E76238003336B65A6F541EB075BDD3538F99C65BD98` |
| `DMS_V4.2.0_INVARIANTS.md` | `319E52F1697BEEE227E2171ED4EAAEC28C9D967D94F12FCA1CEB4297BEB2CDD3` |
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
