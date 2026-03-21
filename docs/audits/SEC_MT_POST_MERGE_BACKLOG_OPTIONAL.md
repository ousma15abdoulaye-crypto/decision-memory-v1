# Backlog optionnel — post merge SEC-MT / routing

**Date :** 2026-03-21  
**Contexte :** suite du plan post-merge ; **non bloquant** pour la baseline SEC-MT-01.

Ces items sont **priorisés côté produit / infra** ; ils ne font pas partie du périmètre minimal livré.

| Item | Fichiers / notes |
|------|------------------|
| **Vendors `tenant_id`** | Suite ADR-0052 ; migration ; `src/vendors/` ; inventaire routes `inv10` — isolation multi-tenant applicative + RLS si colonnes sensibles. |
| **Compose `dm_app`** | `docker-compose.yml` : second utilisateur PostgreSQL ou service `psql` d’init pour reproduire localement le rôle `dm_app` et les tests RLS (aligné `052`/`053`). |
| **Invariant legacy `test_couche_a_b_boundary`** | `tests/invariants/test_couche_a_b_boundary.py` : dé-skip ou fusion avec le périmètre réel `src/couche_a/` si le test reste pertinent après refactors. |

**Références :** [`SEC_MT_01_BASELINE.md`](SEC_MT_01_BASELINE.md), [`SEC_MT_THREAT_MODEL_MINIMAL_EXIT_01.md`](SEC_MT_THREAT_MODEL_MINIMAL_EXIT_01.md) §7.
