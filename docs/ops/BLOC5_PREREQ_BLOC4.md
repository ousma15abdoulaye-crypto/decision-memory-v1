# Prérequis BLOC 5 (SPEC V4.3.1) — stabilité BLOC 4

**Règle** : les tests **end-to-end** du projecteur `project_sealed_workspace` (enqueue post-commit, écriture `vendor_market_signals`) ne sont **fiables** que si le scellement comité API est **VERT** en environnement cible.

| Prérequis | Vérification |
|-----------|----------------|
| `POST /api/workspaces/{id}/committee/seal` → **200/201** | Smoke [`scripts/bloc4_seal_validation_postfix.py`](../../scripts/bloc4_seal_validation_postfix.py) ou équivalent |
| `seal_hash` 64 hex + SQL `committee_sessions` cohérents | Voir [BLOC4_COMMITTEE_REPORT.md](BLOC4_COMMITTEE_REPORT.md) |
| Déploiement Railway aligné `main` contenant le fix `tid_cde` | Dashboard + commit |

Si **500** persiste : **STOP** validation projecteur ; résoudre BLOC 4 (logs Railway) avant d’attribuer un verdict VERT au chaînon BLOC5 complet.

**Note** : ce prérequis ne bloque pas le merge des **migrations 078/079** ni les **tests unitaires** purs (`CognitiveState` sans DB) en CI locale.
