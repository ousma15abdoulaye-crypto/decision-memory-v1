# M-CTO-V53-B — Unification lecture marché (MQL, M16, PV, projection vendeur)

**ID :** `M-CTO-V53-B`  
**Dépend de :** `M-CTO-V53-A` (**ADR-V53-MARKET-READ-MODEL.md** = Accepted)  
**Bloque :** `M-CTO-V53-D` (parties PV marché), `M-CTO-V53-J`

---

## 1. Objectif

Implémenter **l’ADR-V53** : une règle de préséance pour les **signaux agrégés**, alignement des **requêtes MQL** avec la logique **`market_delta.py`**, et cohérence des **projecteurs** `vendor_market_signals` avec la vérité retenue.

---

## 2. Périmètre fichiers — ALLOWLIST

### 2.1 Créer (nouveau module partagé)

| Créer |
|-------|
| `src/services/market_signal_lookup.py` |

**Nom figé.** Tout autre nom de module = **amendement CTO** de ce mandat avant merge.

**Rôle attendu du module :** fonctions pures ou requêtes paramétrées partagées pour :

- normalisation label → slug (réutiliser / factoriser depuis `src/services/market_delta.py`),
- résolution `(zone_id, item_slug)` → `price_seasonal_adj` + métadonnées qualité (même SQL sémantique que `_lookup_market_price` dans `market_delta.py`).

### 2.2 Modifier

| Chemin | Contrainte |
|--------|------------|
| `src/services/market_delta.py` | Déléguer au module partagé ; **ne pas** changer le contrat public `persist_market_deltas_for_workspace` sans tests. |
| `src/mql/templates.py` | Ajouter au moins **un** template paramétré lisant `market_signals_v2` conformément ADR-V53 (ex. T7 ou extension T1–T6 documentée). |
| `src/mql/engine.py` | Brancher sélection template si nouvelle clé ; **INV-A02** : binds uniquement. |
| `src/mql/template_selector.py` | Si nécessaire pour router vers template `market_signals_v2`. |
| `src/services/pv_builder.py` | Aligner blocs marché sur ADR-V53 (ordre de fallback `vendor_market_signals` / `market_signals_v2`). |
| `src/api/routers/market.py` | Cohérence des réponses avec ADR-V53 si mêmes agrégats exposés. |
| `src/api/routers/workspaces.py` | Section requêtes `vendor_market_signals` : commentaire + logique alignée ADR (pas de double formule silencieuse). |
| `src/workers/arq_projector_couche_b.py` | Documenter + aligner INSERT `vendor_market_signals` sur décision ADR. |
| `src/workers/arq_sealed_workspace.py` | Idem si écriture `vendor_market_signals`. |
| `tests/unit/test_signal_engine.py` | Si seuils impactés (unlikely). |
| `tests/mql/` *(créer si absent)* ou `tests/unit/test_mql_*.py` | Tests template nouveau + non-régression binds. |
| `tests/services/test_market_delta.py` *(créer si absent)* ou fichier test existant pour `market_delta` | Régression lookup. |
| `tests/services/test_pv_builder.py` | Adapter assertions SQL / mocks selon changements PV. |

### 2.3 Documentation (optionnelle même PR ou sous-mandat docs)

| Modifier / Créer |
|------------------|
| `docs/adr/ADR-V53-MARKET-READ-MODEL.md` | Section « Implémentation » + lien PR. |

**Si la doc est hors cette PR :** retirer la ligne du mandat (amendement CTO).

### 2.4 Alembic

| Autorisé | Condition |
|----------|-----------|
| `alembic/versions/<new>_v53_market_*.py` | **Uniquement** si ADR impose colonne/index/vue **et** mandat CTO Alembic séparé **ou** clause explicite dans ce mandat. **Par défaut : pas de migration en B** si la cohérence est code-only. |

> Si migration nécessaire : ajouter une ligne à l’ALLOWLIST avant exécution (amendement CTO).

### INTERDIT

- `services/annotation-backend/**`
- `docs/freeze/DMS_V4.1.0_FREEZE.md`
- Fichiers non listés (ex. `src/couche_b/imc_signals.py` **sauf** si amendement : les écritures IMC restent hors périmètre sauf décision explicite).

---

## 3. Invariants à respecter

- **Kill list** : pas de champs `winner` / `rank` / `recommendation` dans sorties nouvelles.
- **Tenant** : mêmes patterns `org_id` / `tenant_id` que MQL existant (`templates.py`).
- **RLS** : requêtes via connexions déjà contextualisées (async pool / sync) — ne pas introduire de `raw_connection` sans tenant.

---

## 4. Tests obligatoires (commandes)

```bash
ruff check src tests
black --check src tests
pytest tests/mql/ tests/services/test_pv_builder.py -q  # + tout fichier test ajouté/modifié
```

---

## 5. Definition of Done

- [ ] ADR-V53 référencé en tête des changements code (commentaire ou doc).
- [ ] Au moins **un** test qui prouve que MQL peut lire `market_signals_v2` avec binds sûrs.
- [ ] `market_delta` utilise le lookup partagé (réduction du double SQL divergent).
- [ ] CI verte ; une PR ; branche `feat/M-CTO-V53-B`.

---

## 6. Commits (exemples)

```
feat(M-CTO-V53-B): shared market signal lookup module
feat(M-CTO-V53-B): MQL template for market_signals_v2
test(M-CTO-V53-B): pv_builder market section alignment
```

---

*Mandat exécutable — périmètre fermé.*
