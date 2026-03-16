# T1-B — Audit src.db / DATABASE_URL / psycopg · import_mercuriale & import_imc

**Date :** 2026-03-07

---

## CHAÎNE DATABASE_URL

### src.db.core (get_connection)
```
_get_raw_connection()
  ← _get_or_init_db_url()  → os.environ.get("DATABASE_URL")
  ← _normalize_url()       → postgres:// → postgresql://
  ← .replace("postgresql+psycopg://", "postgresql://")
  → psycopg.connect(url)
```

### src.db.connection (get_db_cursor)
```
get_db_cursor()
  ← os.environ.get("DATABASE_URL", "")
  ← .replace("postgresql+psycopg://", "postgresql://")
  → psycopg.connect(database_url, row_factory=dict_row)
```

---

## import_mercuriale.py

| Élément | Chemin | Présent |
|---------|--------|---------|
| DATABASE_URL direct | Non dans le script | — |
| Connexion DB | `import_mercuriale()` → `src.couche_b.mercuriale.importer` | OUI |
| Repository | `src.couche_b.mercuriale.repository` | OUI |
| get_connection | `from src.db.core import get_connection` (repository) | OUI |
| DATABASE_URL | Via get_connection → src.db.core → os.environ | OUI |
| Normalisation URL | src.db.core._get_raw_connection : postgres:// + postgresql+psycopg | OUI |
| psycopg | src.db utilise psycopg | OUI |
| --dry-run | `_dry = "--dry-run" in sys.argv` · `main(dry_run=_dry)` | OUI |
| family_id | Aucune occurrence | OUI |

**Conclusion :** import_mercuriale.py utilise DATABASE_URL via src.db (get_connection). Normalisation OK. --dry-run présent. Pas de family_id.

---

## import_imc.py

| Élément | Chemin | Présent |
|---------|--------|---------|
| DATABASE_URL direct | Non dans le script | — |
| Connexion DB | `insert_source`, `insert_entries_batch` → `src.couche_b.imc.repository` | OUI |
| Repository | `from src.db.core import get_connection` | OUI |
| get_connection | src.db.core | OUI |
| DATABASE_URL | Via get_connection → src.db.core → os.environ | OUI |
| Normalisation URL | src.db.core (idem) | OUI |
| psycopg | src.db | OUI |
| --dry-run | `parser.add_argument("--dry-run")` · `args.dry_run` | OUI |
| family_id | Aucune occurrence | OUI |

**Conclusion :** import_imc.py utilise DATABASE_URL via src.db (repository). Normalisation OK. --dry-run présent. Pas de family_id.

---

## RÉSUMÉ

| Script | DATABASE_URL | Normalisation | psycopg | --dry-run | family_id |
|--------|--------------|---------------|---------|-----------|-----------|
| import_mercuriale.py | Via src.db | OUI | OUI | OUI | 0 |
| import_imc.py | Via src.db | OUI | OUI | OUI | 0 |

**Les deux scripts sont conformes pour ingestion Railway.**
