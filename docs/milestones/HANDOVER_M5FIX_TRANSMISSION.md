# NOTE DE TRANSMISSION — M5-FIX · SPRINT CLOS

```
Date de clôture : 2026-03-03
Sprint          : M5-FIX — Correction type market_signals.vendor_id
Agent           : Claude Sonnet 4.6 (session 2026-03-03)
Branche         : feat/m5-fix-pre-ingest → PR ouverte · en attente merge CTO
Commit          : cb69030
Successeur      : Agent M5 (Mercuriale Ingest)
Référence V4    : docs/freeze/DMS_V4.1.0_FREEZE.md (source de vérité unique)
Durée réelle    : ~4h (3 bloquages majeurs non anticipés + problèmes shell Windows)
```

---

## I. ÉTAT SYSTÈME À LA CLÔTURE

| Élément | Valeur |
|---|---|
| Branche | `feat/m5-fix-pre-ingest` · PR ouverte · **non mergée** |
| Alembic head | `m5_fix_market_signals_vendor_type` · **1 seul head** |
| Tests | **735 passed · 36 skipped · 0 failed · 0 error** |
| `market_signals.vendor_id` | `UUID` · nullable · sans FK locale |
| `idx_signals_vendor` | Index UUID présent |
| FK prod | À appliquer via `scripts/apply_fk_prod.py` sur Railway |
| ADR | `docs/adr/ADR-M5-FIX-001.md` créé et à jour |
| TD-010 | FERMÉE |

### Chaîne Alembic à la clôture

```
...
m5_pre_vendors_consolidation
m5_fix_market_signals_vendor_type   ← HEAD (feat/m5-fix-pre-ingest)
```

**Prochain `down_revision` obligatoire pour M5 :**
```python
down_revision = "m5_fix_market_signals_vendor_type"
```

---

## II. CE QUE CE SPRINT A LIVRÉ

### Migration principale

**`alembic/versions/m5_fix_market_signals_vendor_type.py`**
- `down_revision = "m5_pre_vendors_consolidation"`
- `revision = "m5_fix_market_signals_vendor_type"`
- Corrige `market_signals.vendor_id` : `INTEGER → UUID`
- **Garde 0** : idempotence — si vendor_id déjà UUID → skip propre (RAISE NOTICE + RETURN)
- **Garde 1** : market_signals vide obligatoire avant ALTER (si encore INTEGER)
- **Garde 2** : vendor_id doit être INTEGER avant de tenter l'ALTER
- **Garde 3** : vendors.id doit être UUID (consolidation M5-PRE appliquée)
- Index `idx_signals_vendor` : drop si présent, recréé après ALTER (idempotent)
- **FK non créée** : incompatible avec protection append-only locale (voir Section V)
- Downgrade honnête : bloqué si vendor_id non NULL · DROP FK si présente

### Script prod FK

**`scripts/apply_fk_prod.py`**
- Applique `FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE RESTRICT`
- Vérifie pré-conditions (vendor_id UUID, FK absente)
- Usage : `DATABASE_URL=<prod_url> python scripts/apply_fk_prod.py`
- À exécuter après merge et deploy Railway

### ADR

**`docs/adr/ADR-M5-FIX-001.md`**
- Décision : FK non recréée en migration (FOR KEY SHARE bloqué localement)
- Contrainte logique documentée : `REFERENCES vendors(id) ON DELETE RESTRICT`
- Appliquée manuellement en prod uniquement

### Tests (6 invariants)

**`tests/db_integrity/test_m5_fix_market_signals.py`**
- `test_vendor_id_type_est_uuid` ✓
- `test_vendor_id_nullable` ✓
- `test_index_vendor_id_existe` ✓
- `test_insert_valid_vendor_id_uuid` ✓
- `test_insert_vendor_id_integer_refuse` ✓
- `test_market_signals_vide_avant_migration` ✓

*3 tests FK supprimés (SET NULL, RESTRICT, test_fk_reference) : incompatibles avec la protection append-only locale. La FK est vérifiée en prod via `apply_fk_prod.py`.*

### Tests alembic head mis à jour (5 fichiers)

| Fichier | Ancienne valeur | Nouvelle valeur |
|---|---|---|
| `tests/geo/test_geo_migration.py` | `m5_pre_vendors_consolidation` | `m5_fix_market_signals_vendor_type` |
| `tests/test_m0b_db_hardening.py` | `m5_pre_vendors_consolidation` | `m5_fix_market_signals_vendor_type` |
| `tests/vendors/test_vendor_migration.py` | `m5_pre_vendors_consolidation` | `m5_fix_market_signals_vendor_type` |
| `tests/vendors/test_vendor_patch.py` | `m5_pre_vendors_consolidation` | `m5_fix_market_signals_vendor_type` |
| `tests/vendors/test_vendor_patch_a.py` | `m5_pre_vendors_consolidation` | `m5_fix_market_signals_vendor_type` |

### Documentation

| Fichier | Mise à jour |
|---|---|
| `docs/dev/migration-checklist.md` | Section "Doctrine seed data" ajoutée |
| `TECHNICAL_DEBT.md` | TD-010 FERMÉE · motif FK hors migration documenté |
| `docs/adr/ADR-M5-FIX-001.md` | Décision finale ON DELETE RESTRICT hors migration |

---

## III. CHRONOLOGIE DES BLOQUAGES — BATAILLE DES 4H

Cette session a été techniquement la plus difficile du projet. Voici la chronologie exacte pour que l'agent suivant ne refasse pas les mêmes erreurs.

### STOP-5 · ON DELETE SET NULL → InsufficientPrivilege

**Symptôme :** `test_on_delete_set_null` échoue avec :
```
psycopg.errors.InsufficientPrivilege: droit refusé pour la table market_signals
CONTEXT: UPDATE "public"."market_signals" SET "vendor_id" = NULL
```

**Cause :** `market_signals` est protégée append-only via `REVOKE UPDATE`. Le SET NULL requiert UPDATE privilege.

**Verdict CTO :** Remplacer `ON DELETE SET NULL` par `ON DELETE RESTRICT`. Adapter le test pour vérifier `pg_constraint.confdeltype` au lieu du comportement.

### STOP-6 · ON DELETE RESTRICT → même InsufficientPrivilege (FOR KEY SHARE)

**Symptôme :** 4 failed · 637 passed · 101 errors après application de RESTRICT.

**Cause racine :** `ON DELETE RESTRICT` (et toute FK depuis `market_signals` vers `vendors`) déclenche :
```
SELECT 1 FROM ONLY "public"."market_signals" x
WHERE $1 OPERATOR(pg_catalog.=) "vendor_id" FOR KEY SHARE OF x
```
lors de tout `DELETE FROM vendors`, **même si market_signals est vide**. Ce verrou `FOR KEY SHARE` est bloqué par la protection append-only. **Ce n'est pas lié au type de cascade — c'est la FK elle-même qui est incompatible avec la protection append-only.**

**Verdict CTO :** Option A — Supprimer la FK de la migration. Contrainte logique dans l'ADR. Script prod `apply_fk_prod.py`. CI verte priorité absolue.

### PIÈGE-4 Répété · alembic_version régresse lors du cycle down/up

**Symptôme :** Après `alembic downgrade -1` depuis `m5_pre`, le moteur tente `m5_pre → m5_fix` en upgrade. Mais `vendor_id` est déjà UUID → Garde 2 lève EXCEPTION → transaction rollback → `alembic_version` reste à `m5_pre`.

**Cause :** Le `downgrade -1` initial avait regressé trop loin (de `m5_fix` à `m4_patch_a_fix`) car le DB était à `m5_pre` et non `m5_fix` au moment de l'exécution. Résultat : état DB et alembic_version désynchronisés.

**Fix appliqué :**
1. Ajouter **Garde 0 idempotence** à `m5_fix.upgrade()` : si vendor_id déjà UUID → skip
2. Utiliser `alembic stamp m5_fix_market_signals_vendor_type` pour resynchroniser
3. Relancer le cycle down/up proprement

**Règle à retenir :** Toujours vérifier `alembic current` ET l'état physique DB AVANT tout downgrade.

---

## IV. PIÈGES RENCONTRÉS — À NE PAS RÉPÉTER

*(Hérité de M5-PRE + nouveaux de ce sprint)*

### PIÈGE-8 · FOR KEY SHARE bloque toute FK depuis market_signals

Toute contrainte FK depuis `market_signals.vendor_id` vers `vendors.id` — quelle que soit l'action (`RESTRICT`, `SET NULL`, `NO ACTION`, `CASCADE`) — déclenche un verrou `FOR KEY SHARE` lors de `DELETE FROM vendors`. Ce verrou est bloqué par la protection append-only de `market_signals` dans l'environnement local.

**Conséquence :** La FK ne peut pas exister localement. Elle doit être créée en prod via script dédié.

**Signal d'alarme :** `InsufficientPrivilege` sur `FOR KEY SHARE OF market_signals` dans les teardowns de tests qui font `DELETE FROM vendors`.

### PIÈGE-9 · Séquence vendor_id BKO sature à 10000 après runs répétés

Le générateur `get_next_sequence()` utilise `MAX(SPLIT_PART(vendor_id, '-', 4)::INTEGER) + 1`.
La contrainte `chk_vendor_id_format` impose `[0-9]{4}` (exactement 4 chiffres).
Après ~100 runs de test (debug intensif), le compteur BKO atteint `10000` → CheckViolation.

**Symptôme :** `chk_vendor_id_format` violation sur `DMS-VND-BKO-10000-M`.
**Fix local :** Supprimer les vendors `TEST_*` via `scripts/_reset_vendor_seq.py`.
**Fix structurel :** TD-001 (non atomique) + contrainte `[0-9]{4,5}` à discuter en M5+.

### PIÈGE-10 · alembic stamp ne survit pas au cycle pytest si alembic_version non protégée

Le conftest `db_integrity` exécute `alembic upgrade head` via subprocess. Si l'alembic_version est en désynchronisation avec l'état physique DB, l'upgrade échoue en milieu de transaction, et `alembic_version` reste dans l'état pré-migration. Les tests `db_integrity` (62 tests) échouent tous à setup avec `Migrations Alembic échouées`.

**Fix :** Garde 0 idempotence dans `m5_fix.upgrade()` — la migration skips proprement si déjà appliquée.

### PIÈGE-11 (Windows) · PowerShell heredoc `<<'EOF'` non supporté pour git commit

PowerShell lève `L'opérateur « < » est réservé à une utilisation future` quand on tente :
```powershell
git commit -m "$(cat <<'EOF'
...
EOF
)"
```

**Fix systématique :** Écrire le message dans un fichier texte et utiliser `git commit -F fichier.txt`.

### PIÈGE-12 (Windows) · `--timeout` pytest non reconnu (pytest-timeout absent)

Le plugin `pytest-timeout` n'est pas installé dans ce projet. Toute commande avec `--timeout=600` échoue avec exit code 4.

**Fix :** Ne jamais utiliser `--timeout` — le projet n'a pas ce plugin.

### PIÈGE-13 (Windows) · Shell spawn abort sur longues commandes pytest

Sur Windows PowerShell via l'agent, les commandes longues (`python -m pytest` > 300s) peuvent échouer à spawner avec `Error: Command failed to spawn: Aborted`.

**Fix :** Passer par un fichier Python intermédiaire (`scripts/run_tests_final.py`) qui exécute `subprocess.run([sys.executable, "-m", "pytest", ...])`. Ce pattern bypasse le problème de spawn shell.

### PIÈGE-14 (Windows) · `&&` invalide en PowerShell

PowerShell ne supporte pas `&&` pour chaîner des commandes. `cd dir && python script.py` lève une erreur de parsing.

**Fix :** Utiliser `;` à la place (semicolon), ou séparer en commandes distinctes.

---

## V. FAILLES ARCHITECTURE VUES — MISES À JOUR

### F2 (RÉSOLUE PARTIELLEMENT) · market_signals.vendor_id type mismatch

Faille identifiée en M5-PRE : `market_signals.vendor_id = INTEGER orphelin`.
**Résolution M5-FIX :** Type migré de `INTEGER → UUID`. FK logique documentée dans ADR.
**Résidu :** FK non enforced localement. Appliquée en prod via `apply_fk_prod.py`.

### F6 · Protection append-only market_signals incompatible avec FK référencée

`market_signals` a une protection append-only (REVOKE UPDATE ou équivalent) qui bloque `FOR KEY SHARE`.
Cela signifie qu'**aucune table ne peut avoir de FK vers market_signals comme référencée** si le user de test n'a pas les droits de lock.

**Impact M5+ :** Toute migration qui tente d'ajouter une FK `market_signals → vendors` (ou toute autre table) doit soit :
- Passer par `apply_fk_prod.py` (prod uniquement)
- Ou utiliser une approche "logical FK" (ADR + app-level enforcement)

### F7 · Contrainte chk_vendor_id_format limitée à 4 chiffres

Le format `DMS-VND-{region}-{4digits}-{letter}` avec contrainte `[0-9]{4}` limite chaque région à 9999 vendors.
Après saturation du compteur (> 9999 insertions de test), les inserts échouent.

**Action recommandée M5+ :** Étendre la contrainte à `[0-9]{4,6}` ou implémenter une table `vendor_sequences` (TD-001).

---

## VI. ÉTAT DE LA DETTE TECHNIQUE

| Ref | Statut | Description | Sprint |
|---|---|---|---|
| TD-001 | ACTIVE | `get_next_sequence()` non atomique | M5+ |
| TD-002 | ACTIVE | Index GIN trigram manquant | M11 |
| TD-003 | ACTIVE | `zones_covered`, `category_ids` vides | M5/M6 |
| TD-007 | ACTIVE | Connection pooling absent | M5+ |
| TD-009 | PARTIELLE | Chaîne Alembic hors convention numérique | M5+ |
| TD-010 | **FERMÉE** | market_signals.vendor_id = INTEGER orphelin | **M5-FIX** |
| DETTE-M1-04 | ACTIVE | `users.role_id` INTEGER legacy | — |
| DETTE-M2-02 | ACTIVE | Rate limiting per-route no-op | — |

---

## VII. SCRIPTS UTILITAIRES AJOUTÉS CE SPRINT

| Script | Usage | Statut |
|---|---|---|
| `scripts/apply_fk_prod.py` | Applique FK `market_signals → vendors` RESTRICT sur Railway | **NOUVEAU · STABLE** |
| `scripts/run_tests_final.py` | Lance pytest via subprocess Python (bypass spawn Windows) | **NOUVEAU · UTILE** |
| `scripts/_reset_vendor_seq.py` | Nettoie vendors TEST_* · remet séquence BKO < 10000 | **NOUVEAU · LOCAL ONLY** |
| `scripts/_probe_state_now.py` | Probe état DB (tables · types · FK · alembic) | **NOUVEAU · DEBUG** |
| `scripts/_apply_m5fix_fk_stamp.py` | Ajout FK + alembic stamp (correctif état partiel) | **NOUVEAU · ONE-SHOT** |
| `scripts/_fix_piege4_upgrade.py` | Crée vendors legacy fantôme pour débloquer upgrade | **NOUVEAU · ONE-SHOT** |

---

## VIII. PROBE-SQL-01 POUR L'AGENT M5

Avant tout commit M5 Mercuriale, sonder l'état réel :

```sql
-- Alembic head (doit être 1 seul)
SELECT version_num FROM alembic_version;

-- market_signals.vendor_id (doit être UUID après M5-FIX)
SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_name = 'market_signals' AND column_name = 'vendor_id';

-- FK market_signals (absente localement, présente en prod si apply_fk_prod.py exécuté)
SELECT constraint_name, confdeltype
FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid
WHERE c.conname = 'market_signals_vendor_id_fkey' AND t.relname = 'market_signals';

-- vendors (34 colonnes, UUID id)
SELECT COUNT(*) AS c FROM vendors;
SELECT COUNT(*) AS cols
FROM information_schema.columns
WHERE table_name = 'vendors' AND table_schema = 'public';

-- market_signals (doit être vide avant M5)
SELECT COUNT(*) AS c FROM market_signals;
```

---

## IX. RÈGLES INVIOLABLES (RAPPEL POUR AGENT M5)

| Règle | Énoncé |
|---|---|
| RÈGLE-01 | 1 milestone = 1 branche = 1 PR = 1 merge = 1 tag Git |
| RÈGLE-03 | CI rouge = STOP TOTAL |
| RÈGLE-08 | PROBE-SQL-01 avant toute migration touchant une table existante |
| RÈGLE-12 | Migrations = SQL brut `op.execute()` — ZÉRO autogenerate |
| RÈGLE-17 | Toute migration = 1 test minimum prouvant l'invariant visé |
| RÈGLE-FK | Toute FK vers/depuis `market_signals` → vérifier privilege `FOR KEY SHARE` |
| RÈGLE-WIN | PowerShell : `&&` invalide · heredoc invalide · spawn peut avorter |
| RÈGLE-ORG-02 | Lire `docs/freeze/DMS_V4.1.0_FREEZE.md` EN ENTIER avant de commencer |
| RÈGLE-ORG-10 | **L'agent ne merge JAMAIS vers main** |

---

## X. ACTIONS REQUISES APRÈS MERGE (AGENT M5 OU CTO)

```text
1. Merger la PR feat/m5-fix-pre-ingest → main
2. Poser le tag : git tag v4.1.0-m5-fix && git push origin v4.1.0-m5-fix
3. Sur Railway prod, après deploy :
   DATABASE_URL=<prod_url> python scripts/apply_fk_prod.py
   → ajoute FK market_signals.vendor_id → vendors(id) ON DELETE RESTRICT
4. Vérifier alembic_version en prod = m5_fix_market_signals_vendor_type
5. Démarrer M5 avec down_revision = "m5_fix_market_signals_vendor_type"
```

---

## XI. MÉTRIQUES DE CLÔTURE

| Métrique | Valeur |
|---|---|
| Tests | **735 passed · 36 skipped · 0 failed · 0 error** |
| Tests M5-FIX ciblés | 6/6 passed |
| Alembic heads | 1 seul : `m5_fix_market_signals_vendor_type` |
| Dettes fermées | TD-010 |
| Migration créée | `m5_fix_market_signals_vendor_type` |
| Fichiers modifiés | 11 (alembic · adr · tests · docs · scripts) |
| Commit | `cb69030` · branche `feat/m5-fix-pre-ingest` |
| Bloquages résolus | 3 majeurs (STOP-5 · STOP-6 · alembic_version régression) |
| Pièges documentés | 7 nouveaux (PIÈGE-8 à PIÈGE-14) |
| Durée session | ~4h (3h de bloquages imprévus) |

---

## XII. DÉBRIEF HONNÊTE — POURQUOI 4H ?

Ce sprint devait durer 1h. Il en a pris 4. Voici pourquoi, sans filtre :

**Problème 1 — L'hypothèse RESTRICT était fausse.**
Le CTO a approuvé RESTRICT pensant qu'il éviterait le `InsufficientPrivilege`. Ce n'était pas le cas. PostgreSQL fait `FOR KEY SHARE` avant même de vérifier si des lignes existent. **Toute FK depuis/vers market_signals est incompatible avec la protection append-only.** Il a fallu 2 cycles complets de probe-verdict-implémentation pour l'établir.

**Problème 2 — L'état alembic_version se désynchronisait silencieusement.**
Chaque fois qu'une migration échouait en milieu de transaction, alembic_version restait dans l'état précédent. Les cycles down/up répétés ont créé des états intermédiaires (vendor_id UUID mais alembic dit m5_pre). La Garde 0 idempotence a résolu ça, mais il a fallu plusieurs cycles pour diagnostiquer.

**Problème 3 — L'environnement Windows PowerShell.**
- heredoc non supporté → git commit -F fichier
- `&&` invalide → `;` ou commandes séparées
- `--timeout` non reconnu → flag retiré
- spawn abort aléatoire sur les longs runs pytest → `subprocess.run([sys.executable, ...])` dans un fichier Python
Chaque nouvelle commande pouvait échouer pour une raison différente. L'agent a dû construire des workarounds itérativement.

**Ce qui a bien marché :** La rigueur de probe avant action, les gardes idempotentes dans la migration, et la décision finale d'exclure la FK de la migration au lieu de lutter contre la protection append-only.

---

*Agent : Claude Sonnet 4.6 · DMS V4.1.0 · Mopti, Mali · 2026-03-03*
*Réf. V4 : docs/freeze/DMS_V4.1.0_FREEZE.md · RÈGLE-ORG-02*
*Sprint précédent : HANDOVER_M5PRE_TRANSMISSION.md*
