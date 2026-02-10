# PostgreSQL Cloud Run — DMS

DMS is **ONLINE-ONLY** (Constitution V2.1). No SQLite fallback.

---

## Objectif

Prouver l'exécution réelle de DMS sur PostgreSQL cloud (Railway/Render/Supabase).

---

## Environnement

- Provider : _TBD_
- Service URL : _TBD_
- Database URL : _REDACTED_
- Date run : _TBD_
- Commit SHA testé : _TBD_

---

## Smoke Test

```bash
export DATABASE_URL="postgresql+psycopg://..."
python3 scripts/smoke_postgres.py
```
