## Contexte

Après la migration **094** (RLS + `tenant_id` sur marché, mercuriale, `market_signals_v2`, offres, extractions, `analysis_summaries`), deux sujets bloquaient ou fragilisaient la prod :

1. **Backfill `analysis_summaries.tenant_id`** : le trigger append-only **`trg_analysis_summaries_append_only`** (035 / INV-AS3) interdit les `UPDATE` — la migration échouait ou restait incomplète sans désactivation **temporaire** du trigger autour du seul `UPDATE` de backfill.
2. **Scripts batch signaux marché** : `SignalEngine` et les scripts ouvraient des connexions psycopg **sans** poser les GUC RLS (`app.is_admin` / `app.current_tenant`). Avec RLS **FORCE** sur `mercurials`, `market_surveys`, `market_signals_v2`, etc., les batchs voyaient zéro ligne ou échouaient après le premier `COMMIT` de `persist_signal` (GUC **transactionnels** perdus au commit).

La migration **095** reste inchangée dans cette PR (déjà sur `main`) ; le nom de branche reflète le lot sécurité **094 + durcissement scripts**.

## Changements

| Zone | Détail |
|------|--------|
| `alembic/versions/094_security_market_mercurial_tenant_rls.py` | `DISABLE TRIGGER trg_analysis_summaries_append_only` → `UPDATE … tenant_id` → `ENABLE TRIGGER` (commentaires INV-AS3 / ADR-0015). |
| `src/db/connection.py` | Paramètre `transaction_local` sur `_apply_rls_session_settings` / `apply_rls_session_vars_to_connection` : `True` = GUC limités à la transaction (défaut, routes FastAPI inchangées) ; `False` = GUC de **session** pour connexions qui enchaînent plusieurs `COMMIT`. |
| `src/couche_a/market/signal_engine.py` | `SignalEngine._conn()` : après `connect`, appelle `apply_rls_session_vars_to_connection(conn, transaction_local=False)` (**SCRIPTS-RLS-01**). |
| `scripts/batch_signal_from_map.py` | `set_rls_is_admin(True)` + `apply_rls_session_vars_to_connection(conn, transaction_local=False)` sur la connexion partagée avant le batch. |
| `scripts/compute_market_signals.py` | Idem sur la connexion utilisée pour le scope et `persist_signal`. |
| `docs/ops/SECURITY_HARDENING.md` | Statut **SCRIPTS-RLS-01** ; section **§7 Smoke E2E** (ZIP test → `supplier_bundles` sous 60 s). |

## Pré-requis opérationnels

- Les scripts batch doivent tourner avec un contexte explicite : ici **`set_rls_is_admin(True)`** (équivalent « job infra »). Pour un scope **mono-tenant** strict, on pourrait à la place poser `set_db_tenant_id(<uuid>)` sans admin — hors périmètre de cette PR.
- **Ne pas** ré-exécuter le bloc 094 en prod si la migration est déjà appliquée sans ce correctif trigger : appliquer via processus CTO (patch SQL ciblé ou révision Alembic dédiée selon politique dépôt).

## Vérifications

- [ ] CI verte sur cette branche.
- [ ] Revue cohérence avec `docs/ops/SECURITY_HARDENING.md` et runbook migrations.
- [ ] Post-merge (ou sur staging) : smoke §7 — ZIP depuis `data/test_zip/`, upload pipeline, `COUNT(*) FROM supplier_bundles WHERE workspace_id = …` **> 0** dans la minute.

## Références

- `docs/ops/SECURITY_HARDENING.md` (bloc 2026-04-11 + §7).
- Politiques RLS 094 : `app.current_tenant` / `app.is_admin`.
