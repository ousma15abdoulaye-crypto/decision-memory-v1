# SEC-MT-01 — Baseline exécution & dual-app

**Objectif :** figer la vérité d’exécution avant gates SEC-MT progressives (auth HTTP, heuristique IDOR, RLS).

## Commit d’inventaire

- **HEAD (au moment de l’archive des fichiers ci-dessous) :** noter `git rev-parse HEAD` lors de la régénération des sorties.

## Commandes d’audit (sans `--fail-prefix`)

À exécuter depuis la racine du dépôt avec `PYTHONPATH` = racine (comme en CI).

```bash
# Windows PowerShell
$env:PYTHONPATH = (Get-Location).Path

python scripts/audit_fastapi_auth_coverage.py --app main:app
python scripts/audit_fastapi_auth_coverage.py --app src.api.main:app
```

Sorties archivées (noms sans préfixe `audit_*.txt`, [exclus du dépôt par `.gitignore`](../../.gitignore)) :

- `docs/audits/artifacts/sec_mt_01_main_app.txt`
- `docs/audits/artifacts/sec_mt_01_src_api_main.txt`

## Décision dual-app

| Application | Entrée | Usage |
|-------------|--------|--------|
| **`main:app`** | [`start.sh`](../../start.sh) → `uvicorn main:app` | **Vérité production** (Railway). |
| **`src.api.main:app`** | `uvicorn src.api.main:app` (local / tests outillage) | **Montage modulaire complet** (routers optionnels, geo, vendors, mercuriale, etc.). **Non** lancée par `start.sh`. |

**Risque documenté (SEC-MT §2) :** si les deux ASGI étaient exposées publiquement sans inventaire aligné, la surface d’attaque doublerait. **Décision :** une seule exposition prod = `main:app`. Toute exposition future de `src.api.main:app` exige le même niveau de gates (`audit_fastapi_auth_coverage`, RLS `dm_app`, etc.).

## Exceptions publiques assumées (`src.api.main:app`)

- **`/geo/*`** : référentiel géographique lecture seule (pas de `case_id`). Documenté comme annuaire public ; pas de gate `--fail-prefix` sur ce préfixe sans décision produit inverse.
- **`/vendors/*`** : annuaire fournisseur global — auth Bearer requise (voir ADR-0052). Pas de `tenant_id` sur `vendors` à ce jour (option moyen terme dans l’ADR).

## CI Postgres superuser vs RLS prod

La CI migre et teste avec **`postgres` (superuser)** → **RLS contournee** (`BYPASSRLS`). **Vert CI ≠ preuve RLS en prod** tant que les tests [`tests/integration/test_rls_dm_app_cross_tenant.py`](../../tests/integration/test_rls_dm_app_cross_tenant.py) avec rôle **`dm_app`** ne sont pas verts (voir migration `052` + variable `DATABASE_URL_RLS_TEST` en CI).

## Références

- Plan durcissement : mandat interne SEC-MT enterprise (phases 0–6).
- [`RUNTIME_DOC_ALIGNMENT_MATRIX_EXIT_01.md`](RUNTIME_DOC_ALIGNMENT_MATRIX_EXIT_01.md)
- [`SEC_MT_THREAT_MODEL_MINIMAL_EXIT_01.md`](SEC_MT_THREAT_MODEL_MINIMAL_EXIT_01.md)
- [`ADR-0052`](../adr/ADR-0052_vendors_global_catalog_auth.md) · [`ADR-0053`](../adr/ADR-0053_geo_public_readonly.md)
- Runbook ops : [`OPS_SEC_MT_PRODUCTION.md`](OPS_SEC_MT_PRODUCTION.md)
