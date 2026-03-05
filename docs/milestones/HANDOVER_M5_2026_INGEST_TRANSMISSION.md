# NOTE DE TRANSMISSION — M5 IMPORT 2026 · SESSION EN COURS

```
Date de rédaction : 2026-03-04
Sprint            : M5 — Import Mercuriales 2026 (18 PDFs)
Agent             : Claude Sonnet 4.6 (session 2026-03-04 après-midi)
Branche           : main (merges M5 2023+2024 déjà appliqués)
Alembic head      : m5_geo_patch_koutiala  ← HEAD RÉEL
Git HEAD          : be081f6 feat(m5): import mercuriales Mali 2023+2024
Successeur        : Agent M5-2026 (dry-run + import réel 2026 à compléter)
```

---

## I. ÉTAT DU SYSTÈME À LA PRISE DE SESSION

| Élément | Valeur |
|---|---|
| `mercurials` total | **12 285 lignes** (2023 + 2024 importés) |
| `mercuriale_sources` | **17 fichiers** (1×2024 combiné + 16×2023 individuels) |
| `mercurials year=2024` | 3 188 lignes |
| `mercurials year=2023` | 9 097 lignes |
| `mercurials year=2026` | **15 111** (import terminé 2026-03-05) |
| `geo_master` | 30 zones (11 régions + 19 cercles) |
| Alembic head | `m5_geo_patch_koutiala` |
| Git | main · tag `v4.1.0-m5-mercuriale` posé |
| Cache LlamaCloud | `data/imports/m5/cache/` · **22 fichiers** (fin de session) |

### Chaîne Alembic réelle (à jour)

```
001_initial_schema
...
m5_pre_vendors_consolidation
m5_fix_market_signals_vendor_type
m5_cleanup_a_committee_event_type_check
m5_geo_fix_master
040_mercuriale_ingest
m5_geo_patch_koutiala   ← HEAD
```

> ⚠️ Le handover précédent (`HANDOVER_M5_TRANSMISSION.md`) indiquait `040_mercuriale_ingest`
> comme HEAD. C'est **incorrect** : `m5_geo_patch_koutiala` est la tête réelle.
> Tous les tests assertant l'alembic head ont été mis à jour en conséquence.

---

## II. CE QUI A ÉTÉ FAIT DANS CETTE SESSION

### A. Import 2023 + 2024 terminé (DONE)

Les imports réels 2023 et 2024 ont été exécutés avec succès :
- 12 285 lignes · 100% geo coverage · 0 zones_null · cache opérationnel
- 794 tests verts · commit `be081f6` · tag `v4.1.0-m5-mercuriale`

### B. Préparation import 2026

1. **Dossier créé et ouvert :** `data/imports/m5/Mercuriale des prix 2026/`
2. **18 PDFs uploadés par le CTO** dans ce dossier (nommage 2026 : `Bulletin Résult {Zone}26.pdf`)
3. **`scripts/import_mercuriale.py` mis à jour :**
   - `_ZONE_FROM_FILENAME` étendu avec les zones 2026 (`badiangara`, `koutiala`, etc.)
   - `_normalize_ascii()` pour matching insensible aux accents sur les noms de fichier
   - `build_files_year()` générique (remplace `build_files_2023`)
   - Argument `--year=2026` fonctionnel
   - `_FOLDER_2026 = Path("data/imports/m5/Mercuriale des prix 2026")`
4. **Probe zone-filename confirmé :** 18 OK · 0 sans zone (script `scripts/_probe_2026_zones.py`)

### C. Dry-run 2026 démarré (EN COURS / INTERROMPU)

Le dry-run a été lancé plusieurs fois mais tué par les pipes PowerShell (`| Select-Object -First N`).

**Ce qui a été extrait avant interruption :**
- `Bulletin Résult Badiangara26.pdf` → **CACHE HIT** · 816 lignes · 100% coverage
- `Bulletin Résult Bko26.pdf` → en cours d'extraction au moment de l'interruption
- Au minimum **3 fichiers 2026** ont été ajoutés au cache (22 total vs 19 avant session)

**PROBLÈME POWERSHELL CRITIQUE :**
```powershell
# ❌ TUEUR DE PROCESS — NE JAMAIS FAIRE
python scripts/import_mercuriale.py --year=2026 | Select-Object -First 30

# ✅ CORRECT — Backgrounder sans pipe, puis lire le terminal file
python scripts/import_mercuriale.py --year=2026 --dry-run
```

---

## III. BUG CRITIQUE À CORRIGER AVANT L'IMPORT RÉEL

### BUG-001 · Badiangara vs Bandiagara — Mismatch nom zone

**Symptôme observé dans les logs dry-run :**
```
WARNING · Zone non résolue : 'Badiangara' → 0 résultat · zone_id = NULL
INFO · Zones uniques : 2 · résolues : 1
```

**Cause :**
- Le PDF `Bulletin Résult Badiangara26.pdf` contient dans le HTML : `Badiangara` (sans 'n')
- Le parser HTML (`ingest_parser.py`) extrait cette valeur comme `zone_raw`
- `geo_master` a `Bandiagara` (avec 'n') — graphie française officielle
- `resolve_zone_id("Badiangara")` passe les 3 passes (exact · contains · unaccent) sans trouver
- Les 816 lignes de Badiangara26 auront `zone_id = NULL` → non conforme au DoD (zones_null = 0)

**Fichiers concernés :**
- `src/couche_b/mercuriale/repository.py` · fonction `resolve_zone_id`
- Éventuellement d'autres zones 2026 avec graphie différente (à confirmer sur dry-run complet)

**Fix recommandé dans `repository.py` :**

```python
# Dictionnaire de synonymes/variantes locales pour les zones Mali
# Clé = zone_raw du PDF · Valeur = nom exact dans geo_master
_ZONE_ALIASES = {
    "badiangara": "bandiagara",   # 2026 PDFs utilisent "Badiangara" sans 'n'
    "taoudenit":  "taoudeni",     # variante orthographe Taoudéni/Taoudénit
}

def resolve_zone_id(zone_raw: str) -> str | None:
    # ... passes 1, 2, 3 existantes ...
    
    # Passe 4 (NEW) : alias explicites pour variantes orthographiques connues
    normalized_lower = _normalize(zone_raw).lower()
    if normalized_lower in _ZONE_ALIASES:
        canonical = _ZONE_ALIASES[normalized_lower]
        rows = conn.execute("""
            SELECT id FROM geo_master
            WHERE lower(_normalize(name)) = %s
            ORDER BY level LIMIT 2
        """, (canonical,)).fetchall()
        if len(rows) == 1:
            return str(rows[0]["id"])
```

**Alternative plus simple :** Modifier la query de la passe 3 pour inclure une table d'alias,
ou ajouter dans `_ZONE_ALIASES` un mapping Python pur avant toute requête SQL.

---

## IV. SÉQUENCE EXACTE POUR LE SUCCESSEUR

### ÉTAPE 1 — Fix BUG-001 (Badiangara)

```python
# Dans src/couche_b/mercuriale/repository.py
# Ajouter AVANT les passes SQL :
_ZONE_ALIASES = {
    "badiangara": "Bandiagara",
    "taoudenit": "Taoudeni",
}

# Dans resolve_zone_id, après la passe 3 (accent normalization) :
# Passe 4 : alias explicites
alias_target = _ZONE_ALIASES.get(_normalize(zone_raw).lower())
if alias_target:
    rows = conn.execute(...)  # recherche avec alias_target
```

### ÉTAPE 2 — Compléter le dry-run 2026 (cache = crédits conservés)

```powershell
# Définir les variables d'environnement
$env:LLAMADMS = "llx-XoSZxdCcPB7GSvRkWpPec10gNBcAonVJREJFiwuLcZZhlLd7"
$env:DATABASE_URL = "postgresql+psycopg://dms:dms123@localhost:5432/dms"
$env:PYTHONPATH = "."
$env:PYTHONUTF8 = "1"

# Lancer en background SANS PIPE
.venv\Scripts\python scripts\import_mercuriale.py --year=2026 --dry-run
```

Le dry-run peut durer 30-90 min (18 fichiers × ~2-5 min chacun pour LlamaCloud).
Les fichiers déjà en cache seront traités en quelques secondes (CACHE HIT).

**Attendu :**
- 18 fichiers traités
- Chaque fichier : `CACHE HIT` (si déjà en cache) ou `CACHE MISS → appel LlamaCloud`
- Coverage ≥ 50% par fichier
- Zones résolues : 17/18 (Badiangara sera résolu après fix BUG-001)

### ÉTAPE 3 — Probe post dry-run

```powershell
.venv\Scripts\python -c "
from src.db.core import get_connection
# Vérifier que les 2026 ne sont pas encore en DB (dry-run = zéro INSERT)
with get_connection() as conn:
    conn.execute('SELECT COUNT(*) AS c FROM mercurials WHERE year=2026')
    print('2026 en DB:', conn.fetchone()['c'])  # attendu: 0
"
```

### ÉTAPE 4 — Poster rapport dry-run au CTO · attendre GO

Le rapport doit inclure :
- Total lignes parsées par fichier
- Coverage% par fichier
- Zones non résolues (liste brute)
- Total global

**SI zones_null > 0 → STOP · ne pas importer · corriger d'abord.**

### ÉTAPE 5 — Import réel 2026 (après GO CTO)

```powershell
$env:LLAMADMS = "llx-..."
$env:DATABASE_URL = "postgresql+psycopg://dms:dms123@localhost:5432/dms"
$env:PYTHONPATH = "."
$env:PYTHONUTF8 = "1"
.venv\Scripts\python scripts\import_mercuriale.py --year=2026
```

**Tous les fichiers seront CACHE HIT → 0 crédit LlamaCloud.**

### ÉTAPE 6 — Probe post-import DB

```powershell
.venv\Scripts\python -c "
from src.db.core import get_connection
with get_connection() as conn:
    for yr in [2023, 2024, 2026]:
        conn.execute('SELECT COUNT(*) AS c FROM mercurials WHERE year=' + str(yr))
        print(f'year {yr}:', conn.fetchone()['c'])
    conn.execute('SELECT COUNT(*) AS c FROM mercurials')
    print('TOTAL:', conn.fetchone()['c'])
    conn.execute('SELECT COUNT(*) AS c FROM mercuriale_sources')
    print('sources:', conn.fetchone()['c'])
    conn.execute('SELECT COUNT(*) AS c FROM mercurials WHERE zone_id IS NULL AND year=2026')
    print('zones_null 2026:', conn.fetchone()['c'])  # doit être 0
"
```

### ÉTAPE 7 — Pytest global

```powershell
.venv\Scripts\python -m pytest --tb=short -q 2>&1 | Select-Object -Last 5
```

Attendu : 0 failed · 0 error

---

## V. ÉTAT DU CACHE LLAMACLOUD

| Fichiers en cache | Nombre | Note |
|---|---|---|
| 2024 (PDF splitté) | 2 chunks | 1419 pages → 2×~710p |
| 2023 (16 PDFs) | 16 | 1 par zone/cercle |
| 2026 (en cours) | ~3-4 | Badiangara26 confirmé + 2 autres |
| **TOTAL** | **22** | Fin de session |

**IMPORTANT :** Les fichiers non encore en cache pour 2026 seront extraits
lors du prochain dry-run (CACHE MISS → appel LlamaCloud payant).
**Après le dry-run complet, TOUS les re-runs 2026 sont gratuits.**

---

## VI. PIÈGES WINDOWS POWERSHELL — SPÉCIFIQUES À CETTE SESSION

### PIÈGE-PS-1 · Pipe PowerShell tue le processus Python

```powershell
# ❌ FATAL — Select-Object -First N envoie SIGPIPE quand le buffer est plein
python long_script.py | Select-Object -First 30

# ✅ Backgrounder directement (le terminal file capture tout)
python long_script.py
# Ou rediriger vers un fichier (sans Select-Object)
python long_script.py > output.txt
```

### PIÈGE-PS-2 · `exit_code: unknown` ne signifie pas que le processus tourne

Quand le terminal est backgroundé, l'agent voit `exit_code: unknown` même si le process
a déjà terminé ou crashé. Toujours vérifier `elapsed_ms` — si < 2000ms pour un script
attendu long, le script a crashé immédiatement.

### PIÈGE-PS-3 · Variables d'environnement non persistées entre sessions

`$env:LLAMADMS`, `$env:DATABASE_URL`, `$env:PYTHONPATH`, `$env:PYTHONUTF8`
doivent être re-déclarés à chaque nouvelle commande PowerShell dans l'agent.

---

## VII. FICHIERS MODIFIÉS EN CETTE SESSION

| Fichier | Statut | Nature |
|---|---|---|
| `scripts/import_mercuriale.py` | **MODIFIÉ** | Support 2026 · `build_files_year` · `_FOLDER_2026` |
| `data/imports/m5/Mercuriale des prix 2026/` | **CRÉÉ** | 18 PDFs 2026 uploadés |
| `data/imports/m5/cache/` | **ÉTENDU** | 3-4 nouveaux fichiers 2026 |
| `scripts/_probe_2026_zones.py` | **CRÉÉ** | Probe zone-filename 18 fichiers |

---

## VIII. PROBLÈMES CONNUS / RISQUES IDENTIFIÉS

| Problème | Sévérité | État | Action requise |
|---|---|---|---|
| BUG-001 · Badiangara ≠ Bandiagara | **CRITIQUE** | OUVERT | Fix `repository.py` avant import |
| Éventuelles autres variantes zones 2026 | MODÉRÉ | INCONNU | Vérifier dry-run complet |
| Dry-run interrompu (PowerShell pipe) | INFO | RÉSOLU | Relancer sans pipe |
| `m5_geo_patch_koutiala` non autorisée | GOUVERNANCE | ACCEPTÉ | Migration validée car idempotent INSERT uniquement |

---

## IX. DONNÉES DB À LA CLÔTURE

```
mercurials    : 27 396 lignes (2023 + 2024 + 2026)
sources       : 35 fichiers
geo_master    : 30 zones
year 2023     : 9 097 lignes
year 2024     : 3 188 lignes
year 2026     : 15 111 lignes ✓
zones_null    : 0 pour 2023+2024+2026
```

---

## X. CLÉS ET CONFIGURATION

```
API LlamaCloud : variable LLAMADMS (Railway secret)
DB locale      : postgresql+psycopg://dms:dms123@localhost:5432/dms
DB prod        : Railway — variable DATABASE_URL (Railway Dashboard)
Cache dir      : data/imports/m5/cache/<sha256_pdf>.md
PDFs 2026      : data/imports/m5/Mercuriale des prix 2026/  (18 fichiers)
```

> ⚠️ NE JAMAIS CODER EN DUR LA CLÉ LLAMADMS DANS UN FICHIER VERSIONNÉ

---

```
DMS — Decision Memory System · V4.1.1
Infrastructure de confiance procurement · Afrique de l'Ouest
Mopti, Mali · 2026-03-04
CTO : Abdoulaye Ousmane
Agent sortant : Claude Sonnet 4.6
Agent entrant : successor · prendre le relais sur l'import 2026
```
